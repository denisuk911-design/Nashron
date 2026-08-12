from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class SkillService:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, list[dict[str, Any]]]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        cleaned = {str(agent_key): self._clean_list(value) for agent_key, value in data.items()}
        return cleaned

    def list_for_prompt(self, agent_key: str, limit: int = 8) -> list[str]:
        skills = self.load().get(agent_key, [])
        skills.sort(key=lambda item: (int(item.get("uses", 0)), str(item.get("updated_at", ""))), reverse=True)
        return [
            f"{item.get('title', 'Навык')}: {item.get('note', '')}".strip()
            for item in skills[:limit]
            if item.get("title") or item.get("note")
        ]

    def learn_from_exchange(self, agent_key: str, user_message: str, response: str) -> None:
        title = self._title_from_user_message(user_message)
        note = self._note_from_response(response)
        if not title or not note:
            return
        self._upsert_skill(agent_key, title, note)

    def improve_from_context(self, agent_key: str, goal: str, response: str) -> None:
        title = self._skill_title(goal, response)
        note = self._skill_note(response)
        if not title or not note:
            return
        self._upsert_skill(agent_key, title, note)

    def _upsert_skill(self, agent_key: str, title: str, note: str) -> None:
        data = self.load()
        skills = data.setdefault(agent_key, [])
        existing = next((item for item in skills if item.get("title") == title), None)
        now = datetime.now().isoformat(timespec="seconds")
        if existing is None:
            skills.append({"title": title, "note": note, "uses": 1, "created_at": now, "updated_at": now})
        else:
            existing["note"] = note
            existing["uses"] = int(existing.get("uses", 0)) + 1
            existing["updated_at"] = now
        data[agent_key] = skills[-60:]
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _clean_list(value) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    @staticmethod
    def _title_from_user_message(message: str) -> str:
        clean = " ".join(message.strip().split())
        if not clean:
            return ""
        return clean[:64]

    @staticmethod
    def _note_from_response(response: str) -> str:
        clean = " ".join(response.strip().split())
        if not clean:
            return ""
        return clean[:220]

    @staticmethod
    def _skill_title(goal: str, response: str) -> str:
        source = goal or response
        clean = " ".join(source.strip().split())
        if not clean:
            return ""
        lowered = clean.lower()
        for marker in ("скилл", "skill", "навык"):
            index = lowered.find(marker)
            if index >= 0:
                return clean[max(0, index - 24) : index + 40].strip(" :-—")[:64]
        return f"Рабочий подход: {clean[:46]}"

    @staticmethod
    def _skill_note(response: str) -> str:
        clean = " ".join(response.strip().split())
        if not clean:
            return ""
        return clean[:260]
