from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from typing import Any

from .contracts import AgentRuntime, CheckpointStore, TraceService
from .models import (
    RETRYABLE_FAILURES,
    ActionRisk,
    AgentAction,
    FailureReason,
    FindingStatus,
    Handoff,
    HandoffStatus,
    ProviderRun,
    StepStatus,
    TraceEvent,
    WorkflowDefinition,
    WorkflowState,
    WorkflowStatus,
    new_id,
    utc_now,
)
from .registries import StateArtifactRegistry, StateFindingRegistry
from .workspace import WorkspacePolicy


FINAL_WORKFLOW_STATUSES = {WorkflowStatus.CANCELLED, WorkflowStatus.COMPLETED, WorkflowStatus.FAILED}
FINAL_STEP_STATUSES = {StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.CANCELLED}


class PrototypeWorkflowEngine:
    """Framework-neutral, durable execution prototype.

    Execution is deterministic by waves. Independent ready steps are part of
    the same wave and may be submitted concurrently by a future backend.
    """

    def __init__(
        self,
        store: CheckpointStore,
        runtime: AgentRuntime,
        traces: TraceService,
        *,
        disabled_employees: set[str] | None = None,
    ) -> None:
        self.store = store
        self.runtime = runtime
        self.traces = traces
        self.disabled_employees = disabled_employees or set()
        self.artifacts = StateArtifactRegistry()
        self.findings = StateFindingRegistry()

    def create_workflow(
        self,
        organization_id: str,
        goal: str,
        definition: WorkflowDefinition,
        *,
        requirements: dict[str, Any] | None = None,
    ) -> WorkflowState:
        self._validate_definition(definition)
        workflow_id = new_id("workflow")
        task_id = new_id("task")
        steps = {item.step_id: deepcopy(item) for item in definition.steps}
        state = WorkflowState(
            workflow_id=workflow_id,
            task_id=task_id,
            organization_id=organization_id,
            goal=" ".join(goal.strip().split()),
            definition_name=definition.name,
            status=WorkflowStatus.READY,
            steps=steps,
            requirements=dict(requirements or {}),
            max_handoffs=definition.max_handoffs,
            max_retries=definition.max_retries,
            max_review_cycles=definition.max_review_cycles,
            max_agent_calls=definition.max_agent_calls,
        )
        self._update_ready(state)
        self._save(state, "WORKFLOW_CREATED", {"definition": definition.name})
        return state

    def start(self, workflow_id: str) -> WorkflowState:
        state = self.get_state(workflow_id)
        if state.status not in {WorkflowStatus.READY, WorkflowStatus.PAUSED}:
            raise ValueError(f"workflow_not_startable:{state.status}")
        state.status = WorkflowStatus.RUNNING
        self._save(state, "WORKFLOW_STARTED", {})
        return state

    def pause(self, workflow_id: str) -> WorkflowState:
        state = self.get_state(workflow_id)
        if state.status != WorkflowStatus.RUNNING:
            raise ValueError("workflow_not_running")
        state.status = WorkflowStatus.PAUSED
        self._save(state, "WORKFLOW_PAUSED", {})
        return state

    def resume(self, workflow_id: str, *, current_organization_id: str | None = None) -> WorkflowState:
        state = self.get_state(workflow_id)
        if current_organization_id is not None and current_organization_id != state.organization_id:
            self._save(
                state,
                "ORGANIZATION_MISMATCH",
                {"expected": state.organization_id, "actual": current_organization_id},
            )
            raise RuntimeError("organization_changed")
        if state.status not in {WorkflowStatus.PAUSED, WorkflowStatus.WAITING_FOR_OWNER, WorkflowStatus.RUNNING}:
            raise ValueError(f"workflow_not_resumable:{state.status}")
        recovered: list[str] = []
        for step in state.steps.values():
            if step.status == StepStatus.RUNNING:
                step.status = StepStatus.READY
                step.last_error = FailureReason.PROVIDER_CRASH
                recovered.append(step.step_id)
        if state.status != WorkflowStatus.WAITING_FOR_OWNER:
            state.status = WorkflowStatus.RUNNING
        self._save(state, "WORKFLOW_RESUMED", {"recovered_steps": recovered})
        return state

    def cancel(self, workflow_id: str) -> WorkflowState:
        state = self.get_state(workflow_id)
        if state.status in FINAL_WORKFLOW_STATUSES:
            return state
        state.status = WorkflowStatus.CANCEL_REQUESTED
        self._save(state, "CANCEL_REQUESTED", {})
        state.status = WorkflowStatus.CANCELLING
        for step in state.steps.values():
            if step.status not in FINAL_STEP_STATUSES:
                step.status = StepStatus.CANCELLED
                step.last_error = FailureReason.CANCELLED
        self._save(state, "CANCELLING", {})
        state.status = WorkflowStatus.CANCELLED
        self._save(state, "WORKFLOW_CANCELLED", {})
        return state

    def checkpoint(self, workflow_id: str) -> WorkflowState:
        state = self.get_state(workflow_id)
        self._save(state, "CHECKPOINT_CREATED", {})
        return state

    def get_state(self, workflow_id: str) -> WorkflowState:
        return self.store.load(workflow_id)

    def submit_human_decision(self, workflow_id: str, step_id: str, approved: bool) -> WorkflowState:
        state = self.get_state(workflow_id)
        step = state.steps[step_id]
        if step.status != StepStatus.WAITING_APPROVAL:
            raise ValueError("approval_not_expected")
        state.owner_decisions[step_id] = approved
        if approved:
            step.status = StepStatus.READY
            state.status = WorkflowStatus.RUNNING
            event = "OWNER_APPROVED"
        else:
            step.status = StepStatus.CANCELLED
            state.status = WorkflowStatus.CANCELLED
            event = "OWNER_REJECTED"
        self._save(state, event, {"step_id": step_id})
        return state

    def run_until_blocked(self, workflow_id: str, *, max_waves: int | None = None) -> WorkflowState:
        state = self.get_state(workflow_id)
        if state.status == WorkflowStatus.READY:
            state = self.start(workflow_id)
        waves = 0
        while state.status == WorkflowStatus.RUNNING:
            self._update_ready(state)
            ready = [step for step in state.steps.values() if step.status == StepStatus.READY]
            if not ready:
                self._finish_or_block(state)
                self._save(state, "WORKFLOW_SETTLED", {"status": state.status})
                break
            if max_waves is not None and waves >= max_waves:
                self._save(state, "WAVE_LIMIT_REACHED", {"waves": waves})
                break
            state.wave += 1
            waves += 1
            for step in ready:
                step.wave = state.wave
            self._execute_wave(state, ready)
            self._save(state, "WAVE_COMPLETED", {"wave": state.wave, "steps": [item.step_id for item in ready]})
        return state

    def interrupt_requirements(
        self,
        workflow_id: str,
        updates: dict[str, Any],
        *,
        affected_steps: set[str],
    ) -> WorkflowState:
        state = self.get_state(workflow_id)
        state.requirements.update(updates)
        invalidated = set(affected_steps)
        changed = True
        while changed:
            changed = False
            for step in state.steps.values():
                if step.step_id not in invalidated and invalidated.intersection(step.dependencies):
                    invalidated.add(step.step_id)
                    changed = True
        for step_id in invalidated:
            step = state.steps[step_id]
            step.status = StepStatus.INVALIDATED
            step.output_artifacts.clear()
            step.last_error = "requirements_changed"
        state.status = WorkflowStatus.PAUSED
        self._save(state, "REQUIREMENTS_CHANGED", {"updates": updates, "invalidated": sorted(invalidated)})
        for step_id in invalidated:
            state.steps[step_id].status = StepStatus.PENDING
        self._update_ready(state)
        return self.resume_after_interrupt(state)

    def resume_after_interrupt(self, state: WorkflowState) -> WorkflowState:
        state.status = WorkflowStatus.RUNNING
        self._save(state, "WORKFLOW_RESUMED_AFTER_CHANGE", {})
        return state

    def add_handoff(
        self,
        workflow_id: str,
        source_step_id: str,
        target_step_id: str,
        instructions: str,
    ) -> Handoff:
        state = self.get_state(workflow_id)
        if len(state.handoffs) >= state.max_handoffs:
            raise RuntimeError("handoff_budget_exhausted")
        source = state.steps[source_step_id]
        target = state.steps[target_step_id]
        handoff = Handoff(
            handoff_id=new_id("handoff"),
            task_id=state.task_id,
            source_employee=source.employee_id,
            target_employee=target.employee_id,
            input_artifacts=list(source.output_artifacts),
            instructions=instructions,
            expected_output=target.expected_output,
            status=HandoffStatus.ACCEPTED,
        )
        state.handoffs[handoff.handoff_id] = handoff
        self._save(state, "HANDOFF_CREATED", {"handoff_id": handoff.handoff_id})
        return handoff

    def request_rework(
        self,
        workflow_id: str,
        *,
        artifact_id: str,
        responsible_step_id: str,
        reviewer_step_id: str,
        description: str,
        severity: str = "MEDIUM",
        evidence: dict[str, Any] | None = None,
    ) -> WorkflowState:
        state = self.get_state(workflow_id)
        if state.review_cycles >= state.max_review_cycles:
            state.status = WorkflowStatus.FAILED
            self._save(state, "REVIEW_BUDGET_EXHAUSTED", {})
            return state
        if artifact_id not in state.artifacts:
            raise ValueError("rework_artifact_missing")
        responsible = state.steps[responsible_step_id]
        finding_id = self.findings.add(
            state,
            {
                "artifact_id": artifact_id,
                "revision": state.artifacts[artifact_id].current_revision,
                "severity": severity,
                "description": description,
                "evidence": dict(evidence or {}),
                "owner_employee_id": responsible.employee_id,
            },
        )
        self.findings.transition(state, finding_id, "ASSIGNED")
        invalidated = {responsible_step_id}
        changed = True
        while changed:
            changed = False
            for step in state.steps.values():
                if step.step_id not in invalidated and invalidated.intersection(step.dependencies):
                    invalidated.add(step.step_id)
                    changed = True
        invalidated.add(reviewer_step_id)
        for step_id in invalidated:
            step = state.steps[step_id]
            step.status = StepStatus.PENDING
            step.output_artifacts.clear()
            step.last_error = "rework_required"
        state.review_cycles += 1
        state.status = WorkflowStatus.RUNNING
        self._update_ready(state)
        self._save(
            state,
            "REWORK_REQUESTED",
            {"finding_id": finding_id, "responsible_step": responsible_step_id, "invalidated": sorted(invalidated)},
        )
        return state

    def _execute_wave(self, state: WorkflowState, steps: list) -> None:
        prepared = []
        for step in steps:
            item = self._prepare_step(state, step)
            if item is not None:
                prepared.append(item)
            if state.status != WorkflowStatus.RUNNING:
                break
        if not prepared:
            return
        if len(prepared) == 1:
            step, action, provider_id = prepared[0]
            self._apply_result(state, step, self.runtime.execute(action, provider_id))
            return
        with ThreadPoolExecutor(max_workers=len(prepared), thread_name_prefix="runtime-v2") as pool:
            futures = [
                (step, pool.submit(self.runtime.execute, action, provider_id))
                for step, action, provider_id in prepared
            ]
            for step, future in futures:
                try:
                    result = future.result()
                except Exception:
                    from .models import AgentResult

                    result = AgentResult(False, step.last_provider, failure_reason=FailureReason.PROVIDER_CRASH)
                self._apply_result(state, step, result)

    def _prepare_step(self, state: WorkflowState, step):
        if state.total_agent_calls >= state.max_agent_calls:
            step.status = StepStatus.FAILED
            step.last_error = "agent_call_budget_exhausted"
            state.status = WorkflowStatus.FAILED
            return None
        if step.employee_id in self.disabled_employees:
            step.status = StepStatus.FAILED
            step.last_error = FailureReason.EMPLOYEE_DISABLED
            state.status = WorkflowStatus.FAILED
            return None
        if (step.requires_owner_approval or WorkspacePolicy.requires_owner_approval(step.risk)) and not state.owner_decisions.get(step.step_id):
            step.status = StepStatus.WAITING_APPROVAL
            state.status = WorkflowStatus.WAITING_FOR_OWNER
            return None
        input_artifacts = []
        for dependency in step.dependencies:
            for artifact_id in state.steps[dependency].output_artifacts:
                artifact = state.artifacts.get(artifact_id)
                if artifact:
                    input_artifacts.append(artifact)
            try:
                self._ensure_handoff(state, dependency, step.step_id)
            except RuntimeError:
                step.status = StepStatus.FAILED
                step.last_error = "handoff_budget_exhausted"
                state.status = WorkflowStatus.FAILED
                return None
        action = AgentAction(
            workflow_id=state.workflow_id,
            task_id=state.task_id,
            organization_id=state.organization_id,
            employee_id=step.employee_id,
            step_id=step.step_id,
            operation=step.operation,
            expected_output=step.expected_output,
            requirements=dict(state.requirements),
            input_artifacts=input_artifacts,
            risk=step.risk,
        )
        providers = [step.preferred_provider, *step.fallback_providers]
        provider_index = min(step.attempts, max(0, len(providers) - 1))
        provider_id = providers[provider_index]
        step.status = StepStatus.RUNNING
        step.started_at = utc_now()
        step.last_provider = provider_id
        step.attempts += 1
        state.total_agent_calls += 1
        self._save(state, "STEP_STARTED", {"step_id": step.step_id, "provider": provider_id})
        return step, action, provider_id

    def _apply_result(self, state: WorkflowState, step, result) -> None:
        step.last_provider = result.provider_id
        state.provider_runs.append(
            ProviderRun(
                run_id=new_id("run"),
                employee_id=step.employee_id,
                step_id=step.step_id,
                provider_id=result.provider_id,
                model=result.model,
                ok=result.ok,
                failure_reason=str(result.failure_reason or ""),
                duration_ms=result.duration_ms,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )
        )
        if not result.ok:
            self._handle_failure(state, step, result.failure_reason or FailureReason.INVALID_OUTPUT)
            return
        if not result.artifacts and step.expected_output:
            self._handle_failure(state, step, FailureReason.MISSING_ARTIFACT)
            return
        for artifact_data in result.artifacts:
            artifact_id = self.artifacts.add_revision(
                state,
                artifact_data,
                employee_id=step.employee_id,
                provider_id=result.provider_id,
            )
            if artifact_id not in step.output_artifacts:
                step.output_artifacts.append(artifact_id)
        for finding_data in result.findings:
            self.findings.add(state, finding_data)
        step.status = StepStatus.COMPLETED
        step.completed_at = utc_now()
        step.last_error = ""
        for finding in state.findings.values():
            if finding.status == FindingStatus.ASSIGNED and finding.owner_employee_id == step.employee_id:
                self.findings.transition(state, finding.finding_id, "RESOLVED")
            elif finding.status == FindingStatus.RESOLVED and step.operation == "REVIEW":
                self.findings.transition(state, finding.finding_id, "CLOSED")
        for handoff in state.handoffs.values():
            if handoff.target_employee == step.employee_id and handoff.status == HandoffStatus.ACCEPTED:
                handoff.status = HandoffStatus.COMPLETED
                handoff.completed_at = utc_now()
        self._save(state, "STEP_COMPLETED", {"step_id": step.step_id, "artifacts": step.output_artifacts})

    def _ensure_handoff(self, state: WorkflowState, source_step_id: str, target_step_id: str) -> None:
        source = state.steps[source_step_id]
        target = state.steps[target_step_id]
        existing = next((
            handoff
            for handoff in state.handoffs.values()
            if
            handoff.source_employee == source.employee_id
            and handoff.target_employee == target.employee_id
            and handoff.expected_output == target.expected_output
        ), None)
        if existing is not None:
            existing.input_artifacts = list(source.output_artifacts)
            existing.instructions = target.operation
            existing.status = HandoffStatus.ACCEPTED
            existing.completed_at = ""
            return
        if len(state.handoffs) >= state.max_handoffs:
            raise RuntimeError("handoff_budget_exhausted")
        handoff = Handoff(
            handoff_id=new_id("handoff"),
            task_id=state.task_id,
            source_employee=source.employee_id,
            target_employee=target.employee_id,
            input_artifacts=list(source.output_artifacts),
            instructions=target.operation,
            expected_output=target.expected_output,
            status=HandoffStatus.ACCEPTED,
        )
        state.handoffs[handoff.handoff_id] = handoff

    def _handle_failure(self, state: WorkflowState, step, reason: FailureReason) -> None:
        step.last_error = reason
        if reason in RETRYABLE_FAILURES and step.attempts <= step.max_retries and state.total_retries < state.max_retries:
            step.status = StepStatus.READY
            state.total_retries += 1
            self._save(state, "STEP_RETRY_SCHEDULED", {"step_id": step.step_id, "reason": reason})
            return
        if reason == FailureReason.APPROVAL_REQUIRED:
            step.status = StepStatus.WAITING_APPROVAL
            state.status = WorkflowStatus.WAITING_FOR_OWNER
        else:
            step.status = StepStatus.FAILED
            state.status = WorkflowStatus.FAILED
        self._save(state, "STEP_FAILED", {"step_id": step.step_id, "reason": reason})

    def _update_ready(self, state: WorkflowState) -> None:
        for step in state.steps.values():
            if step.status not in {StepStatus.PENDING, StepStatus.INVALIDATED}:
                continue
            if all(state.steps[dependency].status == StepStatus.COMPLETED for dependency in step.dependencies):
                step.status = StepStatus.READY

    @staticmethod
    def _finish_or_block(state: WorkflowState) -> None:
        statuses = {step.status for step in state.steps.values()}
        if statuses == {StepStatus.COMPLETED}:
            state.status = WorkflowStatus.COMPLETED
        elif StepStatus.WAITING_APPROVAL in statuses:
            state.status = WorkflowStatus.WAITING_FOR_OWNER
        elif StepStatus.FAILED in statuses:
            state.status = WorkflowStatus.FAILED
        elif not statuses.intersection({StepStatus.READY, StepStatus.RUNNING}):
            state.status = WorkflowStatus.FAILED

    def _save(self, state: WorkflowState, event_type: str, detail: dict[str, Any]) -> None:
        state.revision += 1
        state.updated_at = utc_now()
        self.store.save(state)
        self.traces.emit(TraceEvent(new_id("trace"), state.workflow_id, event_type, detail))

    @staticmethod
    def _validate_definition(definition: WorkflowDefinition) -> None:
        ids = {step.step_id for step in definition.steps}
        if not definition.steps or len(ids) != len(definition.steps):
            raise ValueError("invalid_workflow_steps")
        for step in definition.steps:
            if not set(step.dependencies).issubset(ids) or step.step_id in step.dependencies:
                raise ValueError(f"invalid_dependencies:{step.step_id}")
        visited: set[str] = set()
        active: set[str] = set()

        def visit(step_id: str) -> None:
            if step_id in active:
                raise ValueError("workflow_dependency_cycle")
            if step_id in visited:
                return
            active.add(step_id)
            for dependency in next(item for item in definition.steps if item.step_id == step_id).dependencies:
                visit(dependency)
            active.remove(step_id)
            visited.add(step_id)

        for step_id in ids:
            visit(step_id)
