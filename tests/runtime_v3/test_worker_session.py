import sys

from runtime_v3.models import ActionType
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
