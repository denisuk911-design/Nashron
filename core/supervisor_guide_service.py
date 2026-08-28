from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable


class SupervisorGuideService:
    """Application service for contextual, non-blocking Supervisor guidance."""

    def __init__(self, state_path: Path, *, action_handler: Callable[[str], Any] | None = None) -> None:
        self.state_path = Path(state_path)
        self.action_handler = action_handler
        self._state = self._load()

    def explain(self, screen: str, *, goal: str = "") -> dict[str, Any]:
        key = str(screen or "main").strip().casefold() or "main"
        familiarity = int(self._state.get("screens", {}).get(key, 0))
        step = self._step_for(key, goal)
        return {
            "mode": "GUIDE",
            "screen": key,
            "title": step["title"],
            "message": step["message"],
            "target": step["target"],
            "actions": ["show", "do"],
            "familiarity": familiarity,
            "suggestion": "do" if familiarity >= 2 else "show",
        }

    def mark_seen(self, screen: str) -> dict[str, Any]:
        key = str(screen or "main").strip().casefold() or "main"
        screens = self._state.setdefault("screens", {})
        screens[key] = int(screens.get(key, 0)) + 1
        self._save()
        return self.explain(key)

    def show(self, screen: str, *, goal: str = "") -> dict[str, Any]:
        result = self.explain(screen, goal=goal)
        result["action"] = "show"
        return result

    def do(self, screen: str, *, goal: str = "") -> dict[str, Any]:
        result = self.explain(screen, goal=goal)
        if self.action_handler is None:
            result.update({"action": "do", "ok": False, "error": "action_handler_unavailable"})
            return result
        try:
            result.update({"action": "do", "ok": True, "result": self.action_handler(result["target"])})
        except Exception as exc:  # surface an owner-safe failure, keep Guide alive
            result.update({"action": "do", "ok": False, "error": f"{type(exc).__name__}: {exc}"})
        return result

    def _load(self) -> dict[str, Any]:
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {"screens": {}}
        except (OSError, ValueError, TypeError):
            return {"screens": {}}

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self._state, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _step_for(screen: str, goal: str) -> dict[str, str]:
        steps = {
            "main": {
                "title": "\u0420\u0430\u0431\u043e\u0447\u0438\u0439 \u0447\u0430\u0442",
                "message": "\u0417\u0434\u0435\u0441\u044c \u043c\u043e\u0436\u043d\u043e \u043f\u043e\u0441\u0442\u0430\u0432\u0438\u0442\u044c \u0437\u0430\u0434\u0430\u0447\u0443 \u043a\u043e\u043c\u0430\u043d\u0434\u0435 \u0438 \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u0442\u044c \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u044b.",
                "target": "chat_input",
            },
            "director": {
                "title": "\u0426\u0435\u043d\u0442\u0440 \u043a\u043e\u043c\u0430\u043d\u0434\u044b",
                "message": "\u0417\u0434\u0435\u0441\u044c \u043d\u0430\u0441\u0442\u0440\u0430\u0438\u0432\u0430\u044e\u0442\u0441\u044f \u0441\u043e\u0442\u0440\u0443\u0434\u043d\u0438\u043a\u0438, \u0440\u043e\u043b\u0438 \u0438 \u043f\u0440\u043e\u0432\u0430\u0439\u0434\u0435\u0440\u044b.",
                "target": "director_button",
            },
            "settings": {
                "title": "\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438",
                "message": "\u0422\u0435\u043c\u0430, \u044f\u0437\u044b\u043a \u0438 \u0437\u0432\u0443\u043a \u043c\u0435\u043d\u044f\u044e\u0442\u0441\u044f \u0437\u0434\u0435\u0441\u044c \u0438 \u0441\u043e\u0445\u0440\u0430\u043d\u044f\u044e\u0442\u0441\u044f \u043f\u043e\u0441\u043b\u0435 \u043f\u0435\u0440\u0435\u0437\u0430\u043f\u0443\u0441\u043a\u0430.",
                "target": "top_settings_button",
            },
        }
        result = dict(steps.get(screen, steps["main"]))
        if goal.strip():
            result["message"] += " \u0422\u0435\u043a\u0443\u0449\u0430\u044f \u0446\u0435\u043b\u044c: " + goal.strip()
        return result
