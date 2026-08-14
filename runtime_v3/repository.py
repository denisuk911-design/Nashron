from __future__ import annotations

import shutil
from pathlib import Path

from .models import RuntimeState, dumps_state, load_state, new_id


class JsonCheckpointRepository:
    """Durable Team2050-owned state store for the V3 prototype."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.current_path = self.root / "state.json"

    def save(self, state: RuntimeState, reason: str) -> str:
        checkpoint_id = new_id("checkpoint")
        checkpoint_path = self.root / f"{checkpoint_id}.json"
        state.checkpoints.append(checkpoint_id)
        payload = dumps_state(state)
        checkpoint_path.write_text(payload, encoding="utf-8")
        self.current_path.write_text(payload, encoding="utf-8")
        (self.root / f"{checkpoint_id}.reason.txt").write_text(reason, encoding="utf-8")
        return checkpoint_id

    def load(self) -> RuntimeState:
        return load_state(self.current_path)

    def exists(self) -> bool:
        return self.current_path.exists()

    def reset(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
