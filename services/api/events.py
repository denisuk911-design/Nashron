from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel


EventType = Literal[
    "organization.updated", "team.updated", "employee.started", "employee.updated",
    "goal.created", "goal.started", "goal.progressed", "goal.blocked", "goal.completed",
    "work.started", "work.progressed", "work.completed", "artifact.created", "artifact.updated",
    "review.started", "review.rework_requested", "review.passed", "iris.state_changed",
    "iris.message", "provider.updated", "skill.updated", "knowledge.updated", "competence.updated",
]


class EventEnvelope(BaseModel):
    type: EventType
    data: dict[str, Any]
    occurred_at: str

    @classmethod
    def create(cls, event_type: EventType, data: dict[str, Any]) -> "EventEnvelope":
        return cls(type=event_type, data=data, occurred_at=datetime.now(timezone.utc).isoformat())
