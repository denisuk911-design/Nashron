from core.provider_execution import ProviderExecutionResult

from runtime_v3.agent_runtime import AgentDecision, ProviderAgentRuntime
from runtime_v3.engine import HybridWorkflowEngine
from runtime_v3.models import Action, ActionType, EmployeeBinding, Goal, Plan, WorkItem, WorkItemStatus, new_id


class WritingProvider:
    def __init__(self, provider_id: str) -> None:
        self.provider_id = provider_id
        self.calls = 0

    def execute(self, request) -> ProviderExecutionResult:
        self.calls += 1
        return ProviderExecutionResult(
            request.run_id, request.employee_id, self.provider_id, request.work_item_id,
            "SUCCEEDED", request.started_at, "2026-08-28T00:00:01+00:00",
            '{"action":"filesystem.write","path":"v3_provider_output/result.md","content":"verified"}',
        )


def _employee() -> EmployeeBinding:
    return EmployeeBinding("engineer", "Engineer", "engineering", ["engineering", "specification"])


def test_uses_cheapest_sufficient_provider_and_persists_consumed_budget(tmp_path):
    cheap = WritingProvider("GEMINI_CLI")
    expensive = WritingProvider("CODEX_CLI")
    runtime = ProviderAgentRuntime(
        {"CODEX_CLI": expensive, "GEMINI_CLI": cheap},
        {"engineer": "CODEX_CLI"},
        {"engineer": ["GEMINI_CLI"]},
    )
    engine = HybridWorkflowEngine("org", [_employee()], tmp_path, agent_runtime=runtime)
    goal = engine.create_goal("Create one file as a simple note")
    goal.intelligence_budget.max_cost_units = 1
    goal.intelligence_budget.provider_cost_units = {"CODEX_CLI": 4, "GEMINI_CLI": 1}
    engine.create_plan(goal.goal_id)

    state = engine.start(goal.goal_id)

    assert state.goals[goal.goal_id].intelligence_budget.spent_cost_units == 1
    assert state.goals[goal.goal_id].intelligence_budget.provider_spend_units == {"GEMINI_CLI": 1}
    assert cheap.calls == 1
    assert expensive.calls == 0
    assert next(iter(state.provider_runs.values())).cost_units == 1


def test_exhausted_budget_prevents_provider_calls_and_survives_restart(tmp_path):
    provider = WritingProvider("GEMINI_CLI")
    runtime = ProviderAgentRuntime({"GEMINI_CLI": provider}, {"engineer": "GEMINI_CLI"})
    engine = HybridWorkflowEngine("org", [_employee()], tmp_path, agent_runtime=runtime)
    goal = engine.create_goal("Create one file as a simple note")
    goal.intelligence_budget.max_cost_units = 0
    engine.create_plan(goal.goal_id)

    engine.start(goal.goal_id)
    restored = HybridWorkflowEngine(
        "org", [_employee()], tmp_path,
        agent_runtime=ProviderAgentRuntime({"GEMINI_CLI": provider}, {"engineer": "GEMINI_CLI"}),
    )
    state = restored.resume()

    assert provider.calls == 0
    assert state.goals[goal.goal_id].intelligence_budget.max_cost_units == 0
    assert state.goals[goal.goal_id].intelligence_budget.spent_cost_units == 0
    assert any(run.status == "BUDGET_BLOCKED" for run in state.provider_runs.values())


def test_risky_action_waits_for_owner_approval_across_restart(tmp_path):
    class RiskRuntime:
        def decide(self, employee_id, work_item, attempt):
            return AgentDecision(actions=[Action(
                new_id("action"), work_item.work_item_id, employee_id, ActionType.TERMINAL_RUN,
                {"command": "echo publish release"},
            )])

    engine = HybridWorkflowEngine("org", [_employee()], tmp_path, agent_runtime=RiskRuntime())
    goal = Goal("goal-risk", "publish a release")
    item = WorkItem("work-risk", goal.goal_id, goal.objective, "engineer", status=WorkItemStatus.READY)
    engine.state.goals[goal.goal_id] = goal
    engine.state.plans["plan-risk"] = Plan("plan-risk", goal.goal_id, "engineer", [item.work_item_id])
    engine.state.work_items[item.work_item_id] = item

    engine.start(goal.goal_id)
    interrupt = engine.pending_interrupts(goal.goal_id)[0]
    assert engine.state.actions == {}

    restored = HybridWorkflowEngine("org", [_employee()], tmp_path, agent_runtime=RiskRuntime())
    restored.resume()
    pending = restored.pending_interrupts(goal.goal_id)[0]
    restored.answer_interrupt(pending.interrupt_id, "approve")

    assert restored.state.interrupts[pending.interrupt_id].owner_decision == "approve"
    assert len(restored.state.actions) == len(restored.state.observations) == 1


def test_internal_workspace_action_remains_autonomous(tmp_path):
    engine = HybridWorkflowEngine("org", [_employee()], tmp_path)
    goal = engine.create_goal("Create one file as a simple note")
    engine.create_plan(goal.goal_id)

    state = engine.start(goal.goal_id)

    assert state.goals[goal.goal_id].status.value == "COMPLETED"
    assert engine.pending_interrupts(goal.goal_id) == []
