from __future__ import annotations

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
    def __init__(self, organization_id: str, employees: list[EmployeeBinding], workspace_root: Path, agent_runtime=None) -> None:
        self.state = RuntimeState(organization_id)
        self.supervisor = GoalSupervisor(employees)
        self.agent_runtime = agent_runtime or DeterministicAgentRuntime()
        self.tool_runtime = ToolRuntime(Path(workspace_root) / "workspace")
        self.repository = JsonCheckpointRepository(Path(workspace_root) / "checkpoints")

    def create_goal(self, objective: str) -> Goal:
        goal = Goal(new_id("goal"), objective)
        self.state.goals[goal.goal_id] = goal
        self.checkpoint("goal_created")
        return goal

    def create_plan(self, goal_id: str):
        goal = self.state.goals[goal_id]
        plan, work_items = self.supervisor.create_plan(goal)
        self.state.plans[plan.plan_id] = plan
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
        for item in self.state.work_items.values():
            if item.status == WorkItemStatus.BLOCKED and item.result.get("failure_kind") == "PROVIDER_FAILURE":
                item.status = WorkItemStatus.READY
        for goal in list(self.state.goals.values()):
            if goal.status not in {GoalStatus.COMPLETED, GoalStatus.CANCELLED, GoalStatus.FAILED}:
                self._run_until_blocked(goal)
        return self.state

    def pause(self) -> None:
        self.checkpoint("paused")

    def cancel(self, goal_id: str) -> None:
        goal = self.state.goals[goal_id]
        goal.status = GoalStatus.CANCELLED
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
        return self.repository.save(self.state, reason)

    def get_state(self) -> RuntimeState:
        return self.state

    def _run_until_blocked(self, goal: Goal) -> None:
        progress = True
        while progress:
            progress = False
            for item in list(self.state.work_items.values()):
                if item.goal_id != goal.goal_id:
                    continue
                if item.status == WorkItemStatus.PENDING and self._dependencies_complete(item):
                    item.input_artifact_ids = self._dependency_artifacts(item)
                    item.status = WorkItemStatus.READY
                    self._create_handoff(item)
                    progress = True
                if item.status in {WorkItemStatus.READY, WorkItemStatus.REWORK} and self._dependencies_complete(item):
                    self._execute_item(item)
                    progress = True
            self._update_goal(goal)

    def _execute_item(self, item: WorkItem) -> None:
        item.status = WorkItemStatus.RUNNING
        item.attempt += 1
        self.checkpoint(f"work_item_running:{item.work_item_id}")
        decision = self.agent_runtime.decide(item.assigned_employee_id, item, item.attempt - 1)
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
            self._execute_action(item, action)
        if item.status != WorkItemStatus.REWORK:
            item.status = WorkItemStatus.COMPLETED
            item.result = {"artifact_ids": self._artifacts_for_item(item.work_item_id)}
        self.checkpoint(f"work_item_finished:{item.work_item_id}")

    def _execute_action(self, item: WorkItem, action: Action) -> None:
        self.state.actions[action.action_id] = action
        if action.action_type == ActionType.REVIEW_ARTIFACT:
            observation = self._review(item, action)
        else:
            observation = self.tool_runtime.execute(action)
        self.state.observations[observation.observation_id] = observation
        if observation.status != ObservationStatus.OK:
            item.status = WorkItemStatus.FAILED
            item.result = {"failed_observation_id": observation.observation_id}
            return
        if action.action_type == ActionType.FILESYSTEM_WRITE:
            self._create_artifact_from_write(item, action, observation)
        elif action.action_type == ActionType.REVIEW_ARTIFACT:
            item.result = {"review_observation_id": observation.observation_id}

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
        for artifact_id in action.payload.get("artifact_ids", []):
            artifact = self.state.artifacts[artifact_id]
            content = Path(artifact.path).read_text(encoding="utf-8")
            if artifact.artifact_type == "TECHNICAL_SPECIFICATION" and "controller" not in content.lower():
                finding = Finding(new_id("finding"), item.goal_id, item.work_item_id, item.assigned_employee_id, artifact_id, "MAJOR", "Specification does not mention controller")
                self.state.findings[finding.finding_id] = finding
                findings.append({"finding_id": finding.finding_id, "artifact_id": artifact_id})
                owner = self.state.work_items[artifact.work_item_id]
                owner.status = WorkItemStatus.REWORK
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
