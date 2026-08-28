from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .build_info import build_info


_SECRET = re.compile(r"(?i)(AQ\.|ghp_|sk-|bearer\s+|api[_ -]?key\s*[:=])[^\s,;]+")


class BetaHealthService:
    """Persist a small operational health summary, never raw runtime data."""

    def __init__(self, profile_dir: Path) -> None:
        self.profile_dir = Path(profile_dir)
        self.path = self.profile_dir / "data" / "beta-health.json"
        self.state = self._load()

    def mark_start(self) -> None:
        if self.state.get("started") is True and self.state.get("ready") is not True:
            self.record("crash", "Предыдущий запуск завершился аварийно")
        self.state["started"] = True
        self.state["ready"] = False
        self._save()

    def mark_ready(self) -> None:
        self.state["started"] = True
        self.state["ready"] = True
        self._save()

    def record_provider_failure(self, provider: str, detail: str = "") -> None:
        self.record("provider_failure", f"{provider}: {detail}")

    def record_goal_failure(self, detail: str) -> None:
        self.record("goal_failure", detail)

    def record(self, kind: str, detail: str) -> None:
        events = self.state.setdefault("events", [])
        events.append({
            "kind": kind,
            "detail": _SECRET.sub("[скрыто]", str(detail))[:240],
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        self.state["events"] = events[-50:]
        self._save()

    def snapshot(self) -> dict[str, Any]:
        events = list(self.state.get("events", []))
        counts: dict[str, int] = {}
        for event in events:
            kind = str(event.get("kind", "unknown"))
            counts[kind] = counts.get(kind, 0) + 1
        return {
            "product": "Team2050",
            "build": build_info(),
            "status": "HEALTHY" if self.state.get("ready") else "STARTING_OR_INTERRUPTED",
            "counts": counts,
            "last_event": events[-1] if events else None,
            "events": events,
            "secrets_included": False,
        }

    def _load(self) -> dict[str, Any]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"started": False, "ready": False, "events": []}
        return value if isinstance(value, dict) else {"started": False, "ready": False, "events": []}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")
