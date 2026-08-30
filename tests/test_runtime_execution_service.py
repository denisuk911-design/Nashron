from core.agent_directory import ChatAgent
from core.runtime_contracts import ExecutionPolicy
from core.external_runtime_adapters import ExternalExecutionPayload, LangGraphRuntimeAdapter
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


def test_external_runtime_completes_direct_action_without_native_scheduler():
    native_calls = []

    class NativeService:
        def run_goal(self, *args):
            native_calls.append(args)
            raise AssertionError("external direct action must not enter Native scheduler")

    employee = ChatAgent(
        key="worker", agent_id="employee-1", display_name="Worker", provider_id="CODEX_CLI",
        roles=["DESIGN_ENGINEER"], persona_id=None, description="", avatar_path=None,
    )
    external = LangGraphRuntimeAdapter(
        lambda request: ExternalExecutionPayload(
            True, "external action complete", artifact_refs=("artifact-1",), observations=("tool observed",)
        )
    )
    service = RuntimeExecutionService(NativeService(), {"langgraph": external})
    result = service.execute("org-a", "create one artifact", [employee], ExecutionPolicy.DIRECT_ACTION)
    assert result.runtime_id == "langgraph"
    assert result.artifact_refs == ("artifact-1",)
    assert native_calls == []
