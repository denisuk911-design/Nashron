from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .database import Database


QUESTION_STARTS = (
    "кто",
    "что",
    "как",
    "почему",
    "зачем",
    "где",
    "когда",
    "какой",
    "какая",
    "какие",
    "можно ли",
    "есть ли",
    "а ",
)


@dataclass(frozen=True)
class ThreadQuestion:
    id: str
    conversation_id: int
    thread_id: str
    question_message_id: int
    question_text: str
    assigned_agent_keys: list[str]
    status: str
    answer_message_id: int | None
    answered_by_agent_key: str | None


class ThreadQuestionService:
    """Tracks owner questions as first-class open/answered thread items."""

    def __init__(self, database: Database, conversation_id: int) -> None:
        self.database = database
        self.conversation_id = conversation_id
        self.thread_id = f"conversation-{conversation_id}"

    def record_owner_question(self, *, message_id: int | None, text: str, assigned_agent_keys: list[str]) -> str | None:
        if message_id is None or not self._looks_like_question(text):
            return None
        question_id = self.database.create_thread_question(
            conversation_id=self.conversation_id,
            thread_id=self.thread_id,
            question_message_id=message_id,
            question_text=self._trim(text),
            assigned_agent_keys=self._dedupe(assigned_agent_keys),
        )
        self.database.log_event("thread_question_opened", question_id)
        return question_id

    def mark_answered_by_agent(self, *, agent_key: str, answer_message_id: int) -> list[str]:
        open_questions = self.open_questions()
        selected = [
            question.id
            for question in open_questions
            if not question.assigned_agent_keys or agent_key in question.assigned_agent_keys
        ]
        if not selected:
            return []
        self.database.mark_thread_questions_answered(
            question_ids=selected,
            answer_message_id=answer_message_id,
            answered_by_agent_key=agent_key,
        )
        for question_id in selected:
            self.database.log_event("thread_question_answered", f"{question_id}; {agent_key}; message={answer_message_id}")
        return selected

    def accept_answer(self, question_id: str) -> bool:
        updated = self.database.update_thread_question_status(question_id, "ACCEPTED")
        if updated:
            self.database.log_event("thread_question_answer_accepted", question_id)
        return updated

    def reopen(self, question_id: str) -> bool:
        updated = self.database.update_thread_question_status(question_id, "OPEN")
        if updated:
            self.database.log_event("thread_question_reopened", question_id)
        return updated

    def open_questions(self, limit: int | None = None) -> list[ThreadQuestion]:
        return [
            self._from_row(row)
            for row in self.database.list_thread_questions(conversation_id=self.conversation_id, status="OPEN", limit=limit)
        ]

    @classmethod
    def _looks_like_question(cls, text: str) -> bool:
        lowered = " ".join(text.lower().replace("ё", "е").split())
        if "?" in text:
            return True
        return any(lowered.startswith(prefix) for prefix in QUESTION_STARTS) and len(lowered) <= 180

    @staticmethod
    def _trim(text: str, limit: int = 500) -> str:
        clean = " ".join(text.strip().split())
        if len(clean) <= limit:
            return clean
        return f"{clean[: limit - 1].rstrip()}..."

    @staticmethod
    def _dedupe(items: list[str]) -> list[str]:
        result: list[str] = []
        for item in items:
            if item and item not in result:
                result.append(item)
        return result

    @classmethod
    def _from_row(cls, row) -> ThreadQuestion:
        try:
            assigned = json.loads(str(row["assigned_agent_keys"] or "[]"))
        except json.JSONDecodeError:
            assigned = []
        if not isinstance(assigned, list):
            assigned = []
        return ThreadQuestion(
            id=str(row["id"]),
            conversation_id=int(row["conversation_id"]),
            thread_id=str(row["thread_id"]),
            question_message_id=int(row["question_message_id"]),
            question_text=str(row["question_text"]),
            assigned_agent_keys=[str(item) for item in assigned],
            status=str(row["status"]),
            answer_message_id=int(row["answer_message_id"]) if row["answer_message_id"] is not None else None,
            answered_by_agent_key=str(row["answered_by_agent_key"]) if row["answered_by_agent_key"] else None,
        )
