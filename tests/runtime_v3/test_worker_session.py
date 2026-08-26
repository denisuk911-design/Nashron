import sys

from runtime_v3.models import ActionType
from runtime_v3.external_tools import ExternalToolDescriptor, ExternalToolRegistry, ExternalToolResult
from runtime_v3.tools import ToolRuntime
from runtime_v3.worker_session import WorkPackage, WorkerSession


def test_worker_session_executes_real_multi_step_workspace_and_terminal_work(tmp_path):
    tools = ToolRuntime(tmp_path, {"worker": {"READ_WORKSPACE", "WRITE_WORKSPACE", "RUN_COMMANDS"}})
    session = WorkerSession(WorkPackage("work", "worker", "make a runnable project"), tools)
    steps = [
        (ActionType.FILESYSTEM_MKDIR, {"path": "game"}),
        (ActionType.FILESYSTEM_WRITE, {"path": "game/main.py", "content": "print('game ready')\n"}),
        (ActionType.FILESYSTEM_SEARCH, {"query": "game ready"}),
        (ActionType.TERMINAL_RUN, {"command": f'"{sys.executable}" game/main.py'}),
    ]

    def planner(_observations):
        if not steps:
            return None
        action_type, payload = steps.pop(0)
        return session.action(action_type, payload)

    result = session.run(planner)

    assert result.completed
    assert len(result.observations) == 4
    assert all(item.status.value == "OK" for item in result.observations)
    assert (tmp_path / "game" / "main.py").exists()
    assert "game ready" in result.observations[-1].data["stdout"]


def test_worker_session_can_use_discovered_external_tool_with_trace_context(tmp_path):
    class Adapter:
        def discover(self):
            return [ExternalToolDescriptor("browser.dom", {"type": "object"}, frozenset({"dom.read"}))]

        def invoke(self, tool_name, arguments, correlation_id=""):
            return ExternalToolResult(tool_name == "browser.dom", "DOM read", {"selector": arguments["selector"], "correlation_id": correlation_id})

        def cancel(self, task_handle):
            return None

    registry = ExternalToolRegistry({"automation": Adapter()})
    tools = ToolRuntime(
        tmp_path,
        {"worker": {"USE_BROWSER"}},
        {"worker": {"browser.call"}},
        external_tools=registry,
    )
    session = WorkerSession(WorkPackage("work", "worker", "inspect page", correlation_id="corr-1"), tools)
    result = session.run(lambda _observations: None if _observations else session.action(
        ActionType.BROWSER_CALL,
        {"adapter_id": "automation", "tool_name": "browser.dom", "arguments": {"selector": "main"}, "correlation_id": "corr-1"},
    ))

    assert result.completed
    assert result.observations[0].data["correlation_id"] == "corr-1"
