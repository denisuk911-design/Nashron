import pytest

from runtime_v2.benchmark import expense_app_definition
from runtime_v2.models import AgentResult, FailureReason, StepStatus, WorkflowDefinition, WorkflowStatus, WorkflowStep


@pytest.mark.parametrize(
    "reason",
    [
        FailureReason.PROVIDER_CRASH,
        FailureReason.TIMEOUT,
        FailureReason.INVALID_OUTPUT,
        FailureReason.MISSING_ARTIFACT,
    ],
)
def test_retryable_failures_retry_by_reason(engine_factory, reason):
    outcomes = {"technical": [reason]}
    engine, providers, _ = engine_factory(outcomes=outcomes)
    state = engine.create_workflow("org", "Expense app", expense_app_definition())
    state = engine.run_until_blocked(state.workflow_id)
    assert state.status == WorkflowStatus.WAITING_FOR_OWNER
    assert state.steps["technical"].attempts == 2
    assert state.total_retries == 1
    assert state.steps["technical"].last_provider == "provider-b"
    assert len(providers["provider-a"].calls) + len(providers["provider-b"].calls) == 7


@pytest.mark.parametrize("reason", [FailureReason.PERMISSION_DENIED, FailureReason.EMPLOYEE_DISABLED])
def test_non_retryable_failures_stop_without_loop(engine_factory, reason):
    definition = WorkflowDefinition("one", [WorkflowStep("step", "employee", "WRITE", "FILE")])
    engine, _, _ = engine_factory(outcomes={"step": [reason]})
    state = engine.create_workflow("org", "Do work", definition)
    state = engine.run_until_blocked(state.workflow_id)
    assert state.status == WorkflowStatus.FAILED
    assert state.steps["step"].attempts == 1
    assert state.total_retries == 0


def test_missing_artifact_is_detected_even_when_provider_claims_success(engine_factory):
    result = AgentResult(True, "provider-a", summary="File created", artifacts=[])
    definition = WorkflowDefinition("one", [WorkflowStep("step", "employee", "WRITE", "FILE", max_retries=0)])
    engine, _, _ = engine_factory(outcomes={"step": [result]})
    state = engine.create_workflow("org", "Do work", definition)
    state = engine.run_until_blocked(state.workflow_id)
    assert state.status == WorkflowStatus.FAILED
    assert state.steps["step"].last_error == FailureReason.MISSING_ARTIFACT


def test_disabled_employee_is_blocked_before_provider_call(engine_factory):
    definition = WorkflowDefinition("one", [WorkflowStep("step", "disabled", "WRITE", "FILE")])
    engine, providers, _ = engine_factory(disabled_employees={"disabled"})
    state = engine.create_workflow("org", "Do work", definition)
    state = engine.run_until_blocked(state.workflow_id)
    assert state.status == WorkflowStatus.FAILED
    assert state.steps["step"].status == StepStatus.FAILED
    assert providers["provider-a"].calls == []


def test_organization_identity_survives_provider_hot_swap(engine_factory):
    engine, _, _ = engine_factory(outcomes={"technical": [FailureReason.PROVIDER_UNAVAILABLE]})
    state = engine.create_workflow("stable-org", "Expense app", expense_app_definition())
    state = engine.run_until_blocked(state.workflow_id)
    runs = [run for run in state.provider_runs if run.step_id == "technical"]
    assert [run.provider_id for run in runs] == ["provider-a", "provider-b"]
    assert state.organization_id == "stable-org"
    assert state.steps["technical"].employee_id == "technical-specialist"
