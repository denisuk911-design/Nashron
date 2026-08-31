"""Construct real isolated SDK adapters for the Product runtime boundary."""

from __future__ import annotations

import sys
import hashlib
import json
from pathlib import Path

from .external_runtime_adapters import (
    AutoGenRuntimeAdapter,
    GoogleAdkRuntimeAdapter,
    LangGraphRuntimeAdapter,
    OpenAIAgentsRuntimeAdapter,
    SubprocessRuntimeBridge,
)


def build_external_runtime_adapters(project_root: Path, timeout_seconds: float = 90.0, credential: str = "") -> dict[str, object]:
    root = Path(project_root).resolve()
    worker = root / "scripts" / "runtime_external_goal_worker.py"
    envs = {
        "openai-agents": root / ".runtime_envs" / "openai-agents" / "Scripts" / "python.exe",
        "langgraph": root / ".runtime_envs" / "langgraph" / "Scripts" / "python.exe",
        "autogen": root / ".runtime_envs" / "autogen" / "Scripts" / "python.exe",
        "google-adk": root / ".runtime_envs" / "google-adk" / "Scripts" / "python.exe",
    }
    manifest_path = root / "runtime_manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            expected = str(manifest.get("runtimes", {}).get("openai-agents", {}).get("sha256", ""))
            executable = envs["openai-agents"]
            if expected and executable.is_file():
                digest = hashlib.sha256(executable.read_bytes()).hexdigest()
                if digest != expected:
                    envs["openai-agents"] = Path("__integrity_failure__")
        except (OSError, ValueError, TypeError):
            envs["openai-agents"] = Path("__manifest_failure__")

    def bridge(runtime_id: str) -> SubprocessRuntimeBridge:
        executable = envs[runtime_id]
        return SubprocessRuntimeBridge((str(executable), str(worker)), timeout_seconds=timeout_seconds, runtime_id=runtime_id, credential=credential)

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
