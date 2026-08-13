from __future__ import annotations

import json
from pathlib import Path

from .models import TraceEvent


class LocalTraceService:
    """Neutral trace backend; Langfuse can later implement the same contract."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else None
        self._events: list[TraceEvent] = []
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: TraceEvent) -> None:
        self._events.append(event)
        if self.path:
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event.__dict__, ensure_ascii=False) + "\n")

    def list_events(self, workflow_id: str) -> list[TraceEvent]:
        return [event for event in self._events if event.workflow_id == workflow_id]
