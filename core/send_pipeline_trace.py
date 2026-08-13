from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from time import perf_counter
import uuid


@dataclass
class SendPipelineTrace:
    """Monotonic timing data for one user send without blocking the first paint."""

    trace_id: str = field(default_factory=lambda: f"SEND-{uuid.uuid4().hex[:12].upper()}")
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    _origin: float = field(default_factory=perf_counter, repr=False)
    stages_ms: dict[str, float] = field(default_factory=dict)
    agents: list[str] = field(default_factory=list)

    def mark(self, stage: str) -> float:
        elapsed = round((perf_counter() - self._origin) * 1000.0, 2)
        self.stages_ms[stage] = elapsed
        return elapsed

    def set_agents(self, agents: list[str]) -> None:
        self.agents = list(dict.fromkeys(agents))

    def payload(self) -> dict[str, object]:
        return {
            "trace_id": self.trace_id,
            "started_at": self.started_at,
            "agents": self.agents,
            "stages_ms": dict(self.stages_ms),
            "bubble_budget_ok": self.stages_ms.get(
                "user_bubble_created",
                self.stages_ms.get("bubble_created", 51.0),
            ) <= 50.0,
        }

    def to_json(self) -> str:
        return json.dumps(self.payload(), ensure_ascii=False, separators=(",", ":"))
