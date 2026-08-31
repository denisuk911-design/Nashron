"""Construct real isolated SDK adapters for the Product runtime boundary."""

from __future__ import annotations

import sys
from pathlib import Path

from .external_runtime_adapters import (
    AutoGenRuntimeAdapter,
    GoogleAdkRuntimeAdapter,
    LangGraphRuntimeAdapter,
    OpenAIAgentsRuntimeAdapter,
    SubprocessRuntimeBridge,
)


def build_external_runtime_adapters(project_root: Path, timeout_seconds: float = 90.0) -> dict[str, object]:
    root = Path(project_root).resolve()
    worker = root / "scripts" / "runtime_external_goal_worker.py"
    envs = {
        "openai-agents": root / ".runtime_envs" / "openai-agents" / "Scripts" / "python.exe",
        "langgraph": root / ".runtime_envs" / "langgraph" / "Scripts" / "python.exe",
        "autogen": root / ".runtime_envs" / "autogen" / "Scripts" / "python.exe",
        "google-adk": root / ".runtime_envs" / "google-adk" / "Scripts" / "python.exe",
    }

    def bridge(runtime_id: str) -> SubprocessRuntimeBridge:
        executable = envs[runtime_id]
        return SubprocessRuntimeBridge((str(executable), str(worker)), timeout_seconds=timeout_seconds, runtime_id=runtime_id)

    adapters = {
        "openai-agents": (OpenAIAgentsRuntimeAdapter, "openai-agents"),
        "langgraph": (LangGraphRuntimeAdapter, "langgraph"),
        "autogen": (AutoGenRuntimeAdapter, "autogen"),
        "google-adk": (GoogleAdkRuntimeAdapter, "google-adk"),
    }
    return {
        runtime_id: adapter_type(bridge(runtime_id))
        for runtime_id, (adapter_type, _) in adapters.items()
        if envs[runtime_id].is_file() and worker.is_file()
    }
