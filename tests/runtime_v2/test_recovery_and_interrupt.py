from runtime_v2.benchmark import expense_app_definition
from runtime_v2.engine import PrototypeWorkflowEngine
from runtime_v2.models import StepStatus, WorkflowStatus
from runtime_v2.provider import LocalAgentRuntime
from runtime_v2.trace import LocalTraceService


def test_restart_preserves_completed_work_and_recovers_running_step(engine_factory):
    engine, providers, _ = engine_factory()
    state = engine.create_workflow("org", "Expense app", expense_app_definition())
    state = engine.run_until_blocked(state.workflow_id, max_waves=1)
    assert state.steps["director-plan"].status == StepStatus.COMPLETED
    state.steps["technical"].status = StepStatus.RUNNING
    engine.store.save(state)  # Simulate process termination between transitions.

    restarted = PrototypeWorkflowEngine(engine.store, LocalAgentRuntime(providers), LocalTraceService())
    recovered = restarted.resume(state.workflow_id)
    assert recovered.steps["director-plan"].status == StepStatus.COMPLETED
    assert recovered.steps["technical"].status == StepStatus.READY
    assert recovered.steps["technical"].last_error == "PROVIDER_CRASH"
    resumed = restarted.run_until_blocked(state.workflow_id)
    assert resumed.status == WorkflowStatus.WAITING_FOR_OWNER
    assert resumed.steps["director-plan"].attempts == 1


def test_requirement_change_invalidates_only_affected_branch_and_downstream(engine_factory):
    engine, _, _ = engine_factory()
    state = engine.create_workflow("org", "Expense app", expense_app_definition(), requirements={"offline": False})
    state = engine.run_until_blocked(state.workflow_id, max_waves=2)
    assert state.steps["product"].status == StepStatus.COMPLETED
    assert state.steps["technical"].status == StepStatus.COMPLETED

    state = engine.interrupt_requirements(state.workflow_id, {"offline": True}, affected_steps={"technical"})
    assert state.steps["product"].status == StepStatus.COMPLETED
    assert state.steps["product"].attempts == 1
    assert state.steps["technical"].status == StepStatus.READY
    assert state.steps["synthesis"].status == StepStatus.PENDING
    state = engine.run_until_blocked(state.workflow_id)
    assert state.steps["product"].attempts == 1
    assert state.steps["technical"].attempts == 2
    assert state.requirements["offline"] is True


def test_cancel_records_runtime_state_transitions(engine_factory):
    engine, _, traces = engine_factory()
    state = engine.create_workflow("org", "Expense app", expense_app_definition())
    state = engine.cancel(state.workflow_id)
    assert state.status == WorkflowStatus.CANCELLED
    assert all(step.status == StepStatus.CANCELLED for step in state.steps.values())
    events = [event.event_type for event in traces.list_events(state.workflow_id)]
    assert events[-3:] == ["CANCEL_REQUESTED", "CANCELLING", "WORKFLOW_CANCELLED"]


def test_organization_switch_blocks_resume(engine_factory):
    import pytest

    engine, _, _ = engine_factory()
    state = engine.create_workflow("org-a", "Expense app", expense_app_definition())
    engine.start(state.workflow_id)
    with pytest.raises(RuntimeError, match="organization_changed"):
        engine.resume(state.workflow_id, current_organization_id="org-b")
