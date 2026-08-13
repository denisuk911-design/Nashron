from runtime_v2.benchmark import expense_app_definition
from runtime_v2.models import StepStatus, WorkflowStatus


def test_golden_workflow_parallel_dependencies_and_owner_approval(engine_factory):
    engine, _, traces = engine_factory()
    state = engine.create_workflow("org-1", "Expense app", expense_app_definition())
    state = engine.run_until_blocked(state.workflow_id)

    assert state.status == WorkflowStatus.WAITING_FOR_OWNER
    assert state.steps["product"].wave == state.steps["technical"].wave
    assert state.steps["synthesis"].wave > state.steps["technical"].wave
    assert state.steps["owner-approval"].status == StepStatus.WAITING_APPROVAL
    assert state.total_agent_calls == 6

    engine.submit_human_decision(state.workflow_id, "owner-approval", True)
    state = engine.run_until_blocked(state.workflow_id)
    assert state.status == WorkflowStatus.COMPLETED
    assert len(state.artifacts) == 7
    assert state.total_agent_calls == 7
    assert any(event.event_type == "OWNER_APPROVED" for event in traces.list_events(state.workflow_id))


def test_team_request_routes_through_director_first(engine_factory):
    engine, providers, _ = engine_factory()
    state = engine.create_workflow("org-1", "Team, start project", expense_app_definition())
    engine.run_until_blocked(state.workflow_id, max_waves=1)
    calls = providers["provider-a"].calls
    assert [call.employee_id for call in calls] == ["director"]


def test_direct_action_can_target_one_employee(engine_factory):
    from runtime_v2.models import WorkflowDefinition, WorkflowStep

    engine, providers, _ = engine_factory()
    definition = WorkflowDefinition("direct-review", [WorkflowStep("review", "elena", "REVIEW_DOCUMENT", "REVIEW")])
    state = engine.create_workflow("org-1", "Elena, inspect this document", definition)
    state = engine.run_until_blocked(state.workflow_id)
    assert state.status == WorkflowStatus.COMPLETED
    assert [call.employee_id for call in providers["provider-a"].calls] == ["elena"]


def test_independent_steps_are_actually_dispatched_concurrently(engine_factory):
    import threading
    import time

    from runtime_v2.models import AgentResult, WorkflowDefinition, WorkflowStep

    lock = threading.Lock()
    active = 0
    maximum_active = 0

    def result_factory(action, provider_id):
        nonlocal active, maximum_active
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
        time.sleep(0.04)
        with lock:
            active -= 1
        return AgentResult(
            True,
            provider_id,
            artifacts=[{"artifact_id": f"artifact-{action.step_id}", "content": action.step_id}],
        )

    definition = WorkflowDefinition(
        "parallel",
        [WorkflowStep("a", "employee-a", "A", "DOC"), WorkflowStep("b", "employee-b", "B", "DOC")],
    )
    engine, _, _ = engine_factory(result_factory=result_factory)
    state = engine.create_workflow("org", "Parallel work", definition)
    state = engine.run_until_blocked(state.workflow_id)
    assert state.status == WorkflowStatus.COMPLETED
    assert maximum_active == 2


def test_communication_budgets_stop_workflow_without_ping_pong(engine_factory):
    from runtime_v2.models import WorkflowDefinition, WorkflowStep

    definition = WorkflowDefinition(
        "budgeted",
        [
            WorkflowStep("a", "employee-a", "A", "DOC"),
            WorkflowStep("b", "employee-b", "B", "DOC", ["a"]),
        ],
        max_handoffs=0,
        max_agent_calls=2,
    )
    engine, _, _ = engine_factory()
    state = engine.create_workflow("org", "Budgeted work", definition)
    state = engine.run_until_blocked(state.workflow_id)
    assert state.status == WorkflowStatus.FAILED
    assert state.steps["a"].attempts == 1
    assert state.steps["b"].last_error == "handoff_budget_exhausted"
