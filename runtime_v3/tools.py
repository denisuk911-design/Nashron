from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from .models import Action, ActionType, Observation, ObservationStatus, new_id


class ToolRuntime:
    """Minimal generic tool runtime returning typed observations."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def execute(self, action: Action) -> Observation:
        try:
            if action.action_type == ActionType.FILESYSTEM_WRITE:
                return self._write(action)
            if action.action_type == ActionType.FILESYSTEM_READ:
                return self._read(action)
            if action.action_type == ActionType.FILESYSTEM_LIST:
                return self._list(action)
        except Exception as exc:
            return Observation(new_id("obs"), action.action_id, ObservationStatus.FAILED, f"{type(exc).__name__}: {exc}")
        return Observation(new_id("obs"), action.action_id, ObservationStatus.UNSUPPORTED, f"Unsupported tool: {action.action_type}")

    def execute_terminal(self, action: Action) -> Observation:
        command = str(action.payload.get("command", "")).strip()
        if not command:
            return Observation(new_id("obs"), action.action_id, ObservationStatus.FAILED, "empty command")
        completed = subprocess.run(command, cwd=self.workspace_root, text=True, capture_output=True, shell=True, timeout=30)
        return Observation(
            new_id("obs"),
            action.action_id,
            ObservationStatus.OK if completed.returncode == 0 else ObservationStatus.FAILED,
            f"exit={completed.returncode}",
            {"stdout": completed.stdout, "stderr": completed.stderr, "returncode": completed.returncode},
        )

    def _resolve(self, raw_path: str) -> Path:
        path = (self.workspace_root / raw_path).resolve()
        if self.workspace_root not in path.parents and path != self.workspace_root:
            raise ValueError("path escapes workspace")
        return path

    def _write(self, action: Action) -> Observation:
        path = self._resolve(str(action.payload["path"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        content = str(action.payload.get("content", ""))
        path.write_text(content, encoding="utf-8")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return Observation(
            new_id("obs"),
            action.action_id,
            ObservationStatus.OK,
            f"wrote {path.name}",
            {"path": str(path), "sha256": digest, "bytes": len(content.encode("utf-8"))},
        )

    def _read(self, action: Action) -> Observation:
        path = self._resolve(str(action.payload["path"]))
        content = path.read_text(encoding="utf-8")
        return Observation(
            new_id("obs"),
            action.action_id,
            ObservationStatus.OK,
            f"read {path.name}",
            {"path": str(path), "content": content, "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()},
        )

    def _list(self, action: Action) -> Observation:
        path = self._resolve(str(action.payload.get("path", ".")))
        entries = sorted(item.name for item in path.iterdir())
        return Observation(new_id("obs"), action.action_id, ObservationStatus.OK, f"listed {path.name}", {"path": str(path), "entries": entries})
