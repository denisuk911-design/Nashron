from core.agent_directory import ChatAgent
from core.runtime_contracts import ExecutionPolicy
from core.external_runtime_adapters import ExternalExecutionPayload, LangGraphRuntimeAdapter
from core.runtime_execution_service import RuntimeExecutionService
from core.runtime_journal import RuntimeExecutionJournal
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier


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


def test_external_result_is_durable_and_recoverable_without_native_checkpoint(tmp_path):
    journal = RuntimeExecutionJournal(tmp_path / "journal")
    external = LangGraphRuntimeAdapter(
        lambda request: ExternalExecutionPayload(
            True,
            "artifact produced",
            artifact_refs=("artifact-org-a",),
            observations=("artifact verified",),
            tool_calls=("write_artifact",),
        )
    )
    service = RuntimeExecutionService(lambda: None, {"langgraph": external}, journal=journal)
    result = service.execute(
        "org-a", "produce artifact", [], ExecutionPolicy.DIRECT_ACTION,
        correlation_id="external-run-1", preferred_runtime="langgraph",
    )
    recovered = RuntimeExecutionJournal(tmp_path / "journal").recover("org-a", "external-run-1")
    assert result.runtime_id == "langgraph"
    assert recovered is not None
    assert recovered.status == "COMPLETED"
    assert recovered.artifact_refs == ("artifact-org-a",)
    assert RuntimeExecutionJournal(tmp_path / "journal").recover("org-b", "external-run-1") is None


def test_native_employee_scope_is_isolated_for_parallel_executions():
    barrier = Barrier(2)
    seen = {}

    class NativeResult:
        ok = True
        summary = "done"
        workspace_root = "."

        class State:
            goals = {"goal-1": object()}
            artifacts = {}
            evidence = {}
            trace_events = {}

        state = State()

    class NativeService:
        def run_goal(self, organization_id, objective, agents):
            barrier.wait(timeout=2)
            seen[organization_id] = [agent.agent_id for agent in agents]
            return NativeResult()

    def employee(agent_id):
        return ChatAgent(
            key=agent_id, agent_id=agent_id, display_name=agent_id, provider_id="CODEX_CLI",
            roles=["ENGINEER"], persona_id=None, description="", avatar_path=None,
        )

    service = RuntimeExecutionService(NativeService())
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(service.execute, "org-a", "task-a", [employee("employee-a")], ExecutionPolicy.DETERMINISTIC_WORKFLOW),
            pool.submit(service.execute, "org-b", "task-b", [employee("employee-b")], ExecutionPolicy.DETERMINISTIC_WORKFLOW),
        ]
        [future.result() for future in futures]
    assert seen == {"org-a": ["employee-a"], "org-b": ["employee-b"]}
