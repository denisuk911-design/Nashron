from core.agent_directory import ChatAgent
from core.runtime_contracts import ExecutionPolicy
from core.runtime_execution_service import RuntimeExecutionService


def test_product_execution_service_keeps_employee_identity_outside_native_adapter():
    seen = {}

    class NativeResult:
        ok = True
        summary = "native done"
        workspace_root = "."

        class State:
            goals = {"goal-1": object()}
            artifacts = {}
            evidence = {}
            trace_events = {}

        state = State()

    class NativeService:
        def run_goal(self, organization_id, objective, agents):
            seen["ids"] = [agent.agent_id for agent in agents]
            return NativeResult()

    employee = ChatAgent(
        key="worker", agent_id="employee-1", display_name="Worker", provider_id="CODEX_CLI",
        roles=["DESIGN_ENGINEER"], persona_id=None, description="", avatar_path=None,
    )
    result = RuntimeExecutionService(NativeService()).execute(
        "org-a", "task", [employee], ExecutionPolicy.DETERMINISTIC_WORKFLOW,
    )
    assert seen["ids"] == ["employee-1"]
    assert result.runtime_id == "native"
    assert result.organization_id == "org-a"
