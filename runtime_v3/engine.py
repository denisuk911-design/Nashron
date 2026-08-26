from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .agent_runtime import AgentDecision, DeterministicAgentRuntime
from .models import (
    Action,
    ActionType,
    Artifact,
    EmployeeBinding,
    Evidence,
    Finding,
    Goal,
    GoalStatus,
    Handoff,
    HitlInterrupt,
    InterruptStatus,
    ReplanRecord,
    SupervisorDecisionRecord,
    RuntimeTraceEvent,
    Observation,
    ObservationStatus,
    RuntimeState,
    WorkItem,
    WorkItemStatus,
    new_id,
    utc_now,
)
from .repository import JsonCheckpointRepository
from .supervisor import GoalSupervisor
from .tools import ToolRuntime


class HybridWorkflowEngine:
    def __init__(self, organization_id: str, employees: list[EmployeeBinding], workspace_root: Path, agent_runtime=None, max_rework_attempts: int = 2, supervisor_policy=None) -> None:
        self.state = RuntimeState(organization_id)
        self.state.employee_snapshots = {
            employee.employee_id: {
                "role": employee.role,
                "capabilities": list(employee.competencies),
                "permissions": sorted(employee.permissions),
                "provider_capabilities": sorted(employee.provider_capabilities),
                "provider_binding_id": employee.provider_binding_id,
            }
            for employee in employees
        }
        self.supervisor = GoalSupervisor(employees, policy=supervisor_policy)
        self.agent_runtime = agent_runtime or DeterministicAgentRuntime()
        self.tool_runtime = ToolRuntime(
            Path(workspace_root) / "workspace",
            {employee.employee_id: set(employee.permissions) for employee in employees},
            {employee.employee_id: set(employee.provider_capabilities) for employee in employees},
        )
        self.repository = JsonCheckpointRepository(Path(workspace_root) / "checkpoints")
        self.max_rework_attempts = max(1, max_rework_attempts)

    def create_goal(self, objective: str) -> Goal:
        goal = Goal(new_id("goal"), objective)
        self.state.goals[goal.goal_id] = goal
        self.checkpoint("goal_created")
        return goal

    def create_plan(self, goal_id: str):
        goal = self.state.goals[goal_id]
        plan, work_items = self.supervisor.create_plan(goal)
        self.state.plans[plan.plan_id] = plan
        self._record_supervisor_decision(goal, "planning")
        for item in work_items:
            self.state.work_items[item.work_item_id] = item
        goal.plan_id = plan.plan_id
        goal.status = GoalStatus.PLANNED if work_items else GoalStatus.COMPLETED
        goal.updated_at = utc_now()
        self.checkpoint("plan_created")
        return plan

    def start(self, goal_id: str):
        goal = self.state.goals[goal_id]
        if goal.status == GoalStatus.COMPLETED and not self.state.work_items:
            return self.state
        goal.status = GoalStatus.RUNNING
        self.checkpoint("goal_started")
        self._run_until_blocked(goal)
        return self.state

    def resume(self):
        self.state = self.repository.load()
        # Resume with the immutable authorization context from the checkpoint.
        self.tool_runtime.employee_permissions = {
            employee_id: set(snapshot.get("permissions", []))
            for employee_id, snapshot in self.state.employee_snapshots.items()
        }
        self.tool_runtime.employee_provider_capabilities = {
            employee_id: set(snapshot.get("provider_capabilities", []))
            for employee_id, snapshot in self.state.employee_snapshots.items()
        }
        if hasattr(self.agent_runtime, "restore_completed_work_items"):
            confirmed_provider_items = {
                run.work_item_id
                for run in self.state.provider_runs.values()
                if run.status == "SUCCEEDED" and run.action_count > 0
            }
            self.agent_runtime.restore_completed_work_items(confirmed_provider_items)
        for item in self.state.work_items.values():
            if item.status == WorkItemStatus.RUNNING:
                item.status = WorkItemStatus.READY
            if item.status == WorkItemStatus.BLOCKED and item.result.get("failure_kind") == "PROVIDER_FAILURE":
                item.status = WorkItemStatus.READY
        for goal in list(self.state.goals.values()):
            if goal.status not in {GoalStatus.COMPLETED, GoalStatus.CANCELLED, GoalStatus.FAILED}:
                self._run_until_blocked(goal)
        return self.state

    def pending_interrupts(self, goal_id: str | None = None) -> list[HitlInterrupt]:
        return [
            interrupt for interrupt in self.state.interrupts.values()
            if interrupt.status == InterruptStatus.PENDING and (goal_id is None or interrupt.goal_id == goal_id)
        ]

    def answer_interrupt(self, interrupt_id: str, owner_decision: str) -> RuntimeState:
        interrupt = self.state.interrupts[interrupt_id]
        if interrupt.status != InterruptStatus.PENDING:
            return self.state
        if owner_decision not in interrupt.options:
            raise ValueError("owner decision is not one of the offered options")
        interrupt.status = InterruptStatus.RESOLVED
        interrupt.owner_decision = owner_decision
        interrupt.resolved_at = utc_now()
        item = self.state.work_items[interrupt.work_item_id]
        item.status = WorkItemStatus.READY
        item.result = {"owner_decision": owner_decision, "hitl_interrupt_id": interrupt_id}
        self.checkpoint(f"hitl_resolved:{interrupt_id}")
        self._run_until_blocked(self.state.goals[interrupt.goal_id])
        return self.state

    def pause(self) -> None:
        self.checkpoint("paused")

    def cancel(self, goal_id: str) -> None:
        goal = self.state.goals[goal_id]
        goal.status = GoalStatus.CANCELLED
        cancel_runs = getattr(self.agent_runtime, "cancel_active_runs", None)
        if callable(cancel_runs):
            cancel_runs()
        self.checkpoint("cancelled")

    def complete_work_item(self, work_item_id: str, result: dict) -> None:
        item = self.state.work_items[work_item_id]
        item.status = WorkItemStatus.COMPLETED
        item.result = result
        self.checkpoint("work_item_completed")

    def fail_work_item(self, work_item_id: str, reason: str) -> None:
        item = self.state.work_items[work_item_id]
        item.status = WorkItemStatus.FAILED
        item.result = {"reason": reason}
        self.checkpoint("work_item_failed")

    def request_review(self, work_item_id: str) -> None:
        self.state.work_items[work_item_id].status = WorkItemStatus.REVIEW
        self.checkpoint("review_requested")

    def submit_review(self, work_item_id: str, accepted: bool) -> None:
        self.state.work_items[work_item_id].status = WorkItemStatus.COMPLETED if accepted else WorkItemStatus.REWORK
        self.checkpoint("review_submitted")

    def checkpoint(self, reason: str) -> str:
        self._trace(reason)
        return self.repository.save(self.state, reason)

    def _trace(self, stage: str, item: WorkItem | None = None, action: Action | None = None, observation: Observation | None = None, artifact: Artifact | None = None) -> None:
        goal_id = item.goal_id if item is not None else (next(iter(self.state.goals.values())).goal_id if len(self.state.goals) == 1 else "")
        event = RuntimeTraceEvent(
            new_id("trace"), goal_id, stage,
            item.work_item_id if item else "", action.action_id if action else "",
            observation.observation_id if observation else "", artifact.artifact_id if artifact else "",
        )
        self.state.trace_events[event.event_id] = event

    def get_state(self) -> RuntimeState:
        return self.state

    def _run_until_blocked(self, goal: Goal) -> None:
        progress = True
        while progress:
            progress = False
            runnable: list[WorkItem] = []
            for item in list(self.state.work_items.values()):
                if item.goal_id != goal.goal_id:
                    continue
                if item.status in {WorkItemStatus.BLOCKED, WorkItemStatus.FAILED, WorkItemStatus.REWORK} and self._replan_item(goal, item):
                    progress = True
                if item.status == WorkItemStatus.PENDING and self._dependencies_complete(item):
                    item.input_artifact_ids = self._dependency_artifacts(item)
                    item.status = WorkItemStatus.READY
                    self._create_handoff(item)
                    progress = True
                if item.status in {WorkItemStatus.READY, WorkItemStatus.REWORK} and self._dependencies_complete(item):
                    if item.status == WorkItemStatus.REWORK and "artifact.review" in item.required_tools:
                        item.input_artifact_ids = self._dependency_artifacts(item)
                    runnable.append(item)
            if len(runnable) > 1:
                self._execute_items_concurrently(runnable)
                progress = True
            elif runnable:
                self._execute_item(runnable[0])
                progress = True
            self._update_goal(goal)

    def _replan_item(self, goal: Goal, item: WorkItem) -> bool:
        previous_status = item.status
        previous_dependencies = list(item.dependencies)
        decision = self.supervisor.replan(
            item,
            [candidate for candidate in self.state.work_items.values() if candidate.goal_id == goal.goal_id],
        )
        if decision is None:
            return False
        completed_dependency_artifacts = self._dependency_artifacts(item)
        item.input_artifact_ids = list(dict.fromkeys([*item.input_artifact_ids, *completed_dependency_artifacts]))
        item.assigned_employee_id = decision["employee_id"]
        item.dependencies = decision["dependencies"]
        item.status = WorkItemStatus.READY
        previous_result = dict(item.result)
        item.result = {
            "replanned_from": previous_result.get("failure_kind") or previous_status.value,
            "replan_count": int(previous_result.get("replan_count", 0)) + 1,
            "previous_employee_id": decision["previous_employee_id"],
            "employee_id": decision["employee_id"],
            "strategy": decision["strategy"],
        }
        plan = self.state.plans.get(goal.plan_id or "")
        if plan is not None:
            plan.strategy = decision["strategy"]
        replan = ReplanRecord(
            new_id("replan"), goal.goal_id, item.work_item_id,
            previous_result.get("failure_kind") or previous_status.value,
            decision["previous_employee_id"], decision["employee_id"], previous_dependencies,
            list(decision["dependencies"]), decision["strategy"],
        )
        self.state.replans[replan.replan_id] = replan
        self._record_supervisor_decision(goal, "replanning", item)
        evidence = Evidence(
            new_id("evidence"), goal.goal_id, item.work_item_id, "SUPERVISOR_REPLAN", "", "",
            f"replanned after {previous_result.get('failure_kind') or previous_status.value}", True,
        )
        self.state.evidence[evidence.evidence_id] = evidence
        self.checkpoint(f"supervisor_replanned:{item.work_item_id}")
        return True

    def _record_supervisor_decision(self, goal: Goal, step: str, item: WorkItem | None = None) -> None:
        decision = self.supervisor.last_policy_decision
        if decision is None:
            return
        complexity = decision.shape
        record = SupervisorDecisionRecord(
            new_id("supervisor-decision"), goal.goal_id, step, decision.level, complexity,
            "HIGH" if step == "replanning" else "LOW", "HIGH" if step == "replanning" else "LOW",
            list(item.required_capabilities if item else []), decision.reason,
            item.work_item_id if item else "",
        )
        self.state.supervisor_decisions[record.decision_id] = record

    def _execute_item(self, item: WorkItem) -> None:
        item.status = WorkItemStatus.RUNNING
        item.attempt += 1
        self.checkpoint(f"work_item_running:{item.work_item_id}")
        decision = self.agent_runtime.decide(item.assigned_employee_id, item, item.attempt - 1)
        self._apply_decision(item, decision)

    def _execute_items_concurrently(self, items: list[WorkItem]) -> None:
        """Run independent agent decisions in parallel, then commit their effects deterministically."""
        for item in items:
            item.status = WorkItemStatus.RUNNING
            item.attempt += 1
            self.checkpoint(f"work_item_running:{item.work_item_id}")
        with ThreadPoolExecutor(max_workers=len(items), thread_name_prefix="team2050-work") as executor:
            submit = getattr(self.agent_runtime, "submit", None)
            futures = {
                item.work_item_id: executor.submit(
                    (lambda candidate=item: submit(candidate.assigned_employee_id, candidate, candidate.attempt - 1).result())
                    if callable(submit)
                    else self.agent_runtime.decide,
                    *(() if callable(submit) else (item.assigned_employee_id, item, item.attempt - 1)),
                )
                for item in items
            }
            decisions = {item.work_item_id: futures[item.work_item_id].result() for item in items}
        for item in items:
            self._apply_decision(item, decisions[item.work_item_id])

    def _apply_decision(self, item: WorkItem, decision: AgentDecision) -> None:
        if decision.hitl_request:
            self._create_interrupt(item, decision.hitl_request)
            return
        provider_runs = decision.provider_runs or ([decision.provider_run] if decision.provider_run is not None else [])
        for provider_run in provider_runs:
            self.state.provider_runs[provider_run.run_id] = provider_run
        if provider_runs:
            self.checkpoint(f"provider_run_finished:{provider_runs[-1].run_id}")
        if not decision.actions:
            if decision.failure_kind:
                self._provider_failure(item, decision)
            else:
                self._unsupported_claim(item, decision)
            return
        for action in decision.actions:
            if not self._execute_action(item, action):
                self.checkpoint(f"work_item_failed:{item.work_item_id}")
                return
        if item.status != WorkItemStatus.REWORK:
            item.status = WorkItemStatus.COMPLETED
            item.result = {"artifact_ids": self._artifacts_for_item(item.work_item_id)}
        self.checkpoint(f"work_item_finished:{item.work_item_id}")

    def _create_interrupt(self, item: WorkItem, request: dict[str, object]) -> None:
        question = str(request.get("question") or "Нужно решение владельца для продолжения работы.")
        options = [str(option) for option in request.get("options", []) if str(option)]
        if not options:
            raise ValueError("HITL interrupt requires at least one option")
        interrupt = HitlInterrupt(
            new_id("hitl"), item.goal_id, item.work_item_id, question, options,
            str(request.get("context") or "Требуется подтверждение решения."),
        )
        self.state.interrupts[interrupt.interrupt_id] = interrupt
        item.status = WorkItemStatus.BLOCKED
        item.result = {"hitl_interrupt_id": interrupt.interrupt_id, "requires_owner": True}
        self.checkpoint(f"hitl_created:{interrupt.interrupt_id}")

    def _execute_action(self, item: WorkItem, action: Action) -> bool:
        self.state.actions[action.action_id] = action
        if action.action_type == ActionType.REVIEW_ARTIFACT:
            observation = self._review(item, action)
        else:
            observation = self.tool_runtime.execute(action)
        self.state.observations[observation.observation_id] = observation
        self._trace("tool_observed", item, action, observation)
        if observation.status != ObservationStatus.OK:
            item.status = WorkItemStatus.FAILED
            item.result = {"failed_observation_id": observation.observation_id}
            return False
        if action.action_type == ActionType.FILESYSTEM_WRITE:
            self._create_artifact_from_write(item, action, observation)
        elif action.action_type == ActionType.REVIEW_ARTIFACT:
            item.result = {"review_observation_id": observation.observation_id}
        return True

    def _create_artifact_from_write(self, item: WorkItem, action: Action, observation: Observation) -> None:
        path = observation.data["path"]
        artifact_type = item.expected_artifact_types[0] if item.expected_artifact_types else "WORK_PRODUCT"
        revision = 1 + sum(1 for artifact in self.state.artifacts.values() if artifact.work_item_id == item.work_item_id)
        artifact = Artifact(
            new_id("artifact"),
            item.goal_id,
            item.work_item_id,
            artifact_type,
            f"artifact://{item.goal_id}/{item.work_item_id}/{revision}",
            path,
            revision,
            observation.data["sha256"],
            item.assigned_employee_id,
            action.action_id,
            observation.observation_id,
        )
        self.state.artifacts[artifact.artifact_id] = artifact
        self._trace("artifact_created", item, action, observation, artifact)
        evidence = Evidence(
            new_id("evidence"),
            item.goal_id,
            item.work_item_id,
            "TOOL_OBSERVATION",
            action.action_id,
            observation.observation_id,
            "filesystem.write succeeded",
            True,
        )
        self.state.evidence[evidence.evidence_id] = evidence
        if artifact.artifact_type == "SOURCE_RESEARCH":
            source_evidence = Evidence(
                new_id("evidence"),
                item.goal_id,
                item.work_item_id,
                "SOURCE_RECORD",
                action.action_id,
                observation.observation_id,
                "research artifact contains source evidence section",
                "source evidence" in Path(path).read_text(encoding="utf-8").lower(),
            )
            self.state.evidence[source_evidence.evidence_id] = source_evidence

    def _review(self, item: WorkItem, action: Action) -> Observation:
        findings: list[dict] = []
        latest_revisions = {
            artifact.work_item_id: max(
                candidate.revision
                for candidate in self.state.artifacts.values()
                if candidate.work_item_id == artifact.work_item_id
            )
            for artifact in self.state.artifacts.values()
        }
        for artifact_id in action.payload.get("artifact_ids", []):
            artifact = self.state.artifacts[artifact_id]
            if artifact.revision != latest_revisions[artifact.work_item_id]:
                continue
            content = Path(artifact.path).read_text(encoding="utf-8")
            owner = self.state.work_items[artifact.work_item_id]
            requires_golden_rework = "force rework" in owner.objective.lower() and artifact.revision == 1
            missing_controller = artifact.artifact_type == "TECHNICAL_SPECIFICATION" and "controller" not in content.lower()
            missing_source_evidence = artifact.artifact_type == "SOURCE_RESEARCH" and "source evidence" not in content.lower()
            if requires_golden_rework or missing_controller or missing_source_evidence:
                if missing_source_evidence:
                    description = "Research artifact does not contain source evidence"
                elif requires_golden_rework:
                    description = "Initial specification revision requires controlled rework"
                else:
                    description = "Specification does not mention controller"
                finding = Finding(
                    new_id("finding"),
                    item.goal_id,
                    item.work_item_id,
                    item.assigned_employee_id,
                    artifact_id,
                    "MAJOR",
                    description,
                )
                self.state.findings[finding.finding_id] = finding
                findings.append({"finding_id": finding.finding_id, "artifact_id": artifact_id})
                artifact_revisions = sum(
                    1 for candidate in self.state.artifacts.values() if candidate.work_item_id == owner.work_item_id
                )
                if artifact_revisions >= self.max_rework_attempts:
                    owner.status = WorkItemStatus.FAILED
                    owner.result = {
                        "escalation": "MAX_REWORK_ATTEMPTS_EXCEEDED",
                        "finding_ids": [finding.finding_id],
                        "acceptance_criteria": owner.acceptance_criteria,
                    }
                    escalation = Evidence(
                        new_id("evidence"), item.goal_id, owner.work_item_id, "REWORK_ESCALATION", action.action_id,
                        "", "maximum rework attempts exceeded", False,
                    )
                    self.state.evidence[escalation.evidence_id] = escalation
                else:
                    owner.status = WorkItemStatus.REWORK
                    owner.result = {"finding_ids": [finding.finding_id], "acceptance_criteria": owner.acceptance_criteria}
        if findings:
            # The reviewer is retried after the reworked artifact is produced.
            item.status = WorkItemStatus.REWORK
        if not findings:
            for finding in self.state.findings.values():
                if finding.goal_id == item.goal_id:
                    finding.status = "RESOLVED"
        return Observation(
            new_id("obs"),
            action.action_id,
            ObservationStatus.OK,
            "review complete",
            {"findings": findings, "accepted": not findings},
        )

    def _unsupported_claim(self, item: WorkItem, decision: AgentDecision) -> None:
        item.status = WorkItemStatus.BLOCKED
        item.result = {"unsupported_claim": decision.message}
        evidence = Evidence(
            new_id("evidence"),
            item.goal_id,
            item.work_item_id,
            "UNSUPPORTED_CLAIM",
            "",
            "",
            decision.message,
            False,
        )
        self.state.evidence[evidence.evidence_id] = evidence
        self.checkpoint("unsupported_claim_recorded")

    def _provider_failure(self, item: WorkItem, decision: AgentDecision) -> None:
        item.status = WorkItemStatus.BLOCKED
        item.result = {"provider_failure": decision.message, "failure_kind": decision.failure_kind}
        evidence = Evidence(
            new_id("evidence"),
            item.goal_id,
            item.work_item_id,
            decision.failure_kind,
            "",
            "",
            decision.message,
            False,
        )
        self.state.evidence[evidence.evidence_id] = evidence
        self.checkpoint("provider_failure_recorded")

    def _create_handoff(self, item: WorkItem) -> None:
        if not item.dependencies:
            return
        for dependency_id in item.dependencies:
            dependency = self.state.work_items[dependency_id]
            handoff = Handoff(
                new_id("handoff"),
                dependency.assigned_employee_id,
                item.assigned_employee_id,
                item.work_item_id,
                self._artifacts_for_item(dependency_id),
                [dependency_id],
                item.objective,
                item.acceptance_criteria,
                item.evidence_requirements,
            )
            self.state.handoffs[handoff.handoff_id] = handoff

    def _dependencies_complete(self, item: WorkItem) -> bool:
        return all(self.state.work_items[dependency].status == WorkItemStatus.COMPLETED for dependency in item.dependencies)

    def _dependency_artifacts(self, item: WorkItem) -> list[str]:
        artifact_ids: list[str] = []
        for dependency in item.dependencies:
            artifact_ids.extend(self._artifacts_for_item(dependency))
        return artifact_ids

    def _artifacts_for_item(self, work_item_id: str) -> list[str]:
        return [artifact.artifact_id for artifact in self.state.artifacts.values() if artifact.work_item_id == work_item_id]

    def _update_goal(self, goal: Goal) -> None:
        items = [item for item in self.state.work_items.values() if item.goal_id == goal.goal_id]
        if not items:
            goal.status = GoalStatus.COMPLETED
        elif any(item.status == WorkItemStatus.FAILED for item in items):
            goal.status = GoalStatus.FAILED
        elif any(item.status == WorkItemStatus.REWORK for item in items):
            goal.status = GoalStatus.REWORK
        elif all(item.status == WorkItemStatus.COMPLETED for item in items):
            goal.status = GoalStatus.COMPLETED
        else:
            goal.status = GoalStatus.RUNNING
        goal.updated_at = utc_now()
        self.checkpoint(f"goal_status:{goal.status}")
