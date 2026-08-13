from __future__ import annotations

import json
import os
from pathlib import Path

from .models import WorkflowState


class JsonCheckpointStore:
    """Portable local checkpoint repository with atomic replacement."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, workflow_id: str) -> Path:
        if not workflow_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in workflow_id):
            raise ValueError("invalid_workflow_id")
        return self.root / f"{workflow_id}.json"

    def save(self, state: WorkflowState) -> None:
        path = self._path(state.workflow_id)
        temporary = path.with_suffix(".json.tmp")
        payload = json.dumps(state.to_dict(), ensure_ascii=False, indent=2)
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)

    def load(self, workflow_id: str) -> WorkflowState:
        data = json.loads(self._path(workflow_id).read_text(encoding="utf-8"))
        return WorkflowState.from_dict(data)

    def exists(self, workflow_id: str) -> bool:
        return self._path(workflow_id).exists()


class InMemoryCheckpointStore:
    def __init__(self) -> None:
        self._items: dict[str, dict] = {}

    def save(self, state: WorkflowState) -> None:
        self._items[state.workflow_id] = json.loads(json.dumps(state.to_dict()))

    def load(self, workflow_id: str) -> WorkflowState:
        if workflow_id not in self._items:
            raise KeyError(workflow_id)
        return WorkflowState.from_dict(self._items[workflow_id])

    def exists(self, workflow_id: str) -> bool:
        return workflow_id in self._items
