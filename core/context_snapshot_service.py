from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

from .agent_directory import ChatAgent, get_chat_agent
from .database import Database
from .models import Message


STOP_WORDS = {
    "что",
    "как",
    "или",
    "для",
    "это",
    "там",
    "тут",
    "еще",
    "ещё",
    "раз",
    "мне",
    "тебе",
    "нас",
    "вам",
    "они",
    "она",
    "оно",
    "the",
    "and",
    "for",
}

ROLE_CONTEXT_TERMS = {
    "QA_ENGINEER": ("провер", "ревью", "ошиб", "риск", "отк", "контроль", "аудит"),
    "VERIFICATION_ENGINEER": ("тест", "валид", "воспро", "провер", "результат"),
    "DOCUMENT_CONTROL_OFFICER": ("документ", "гост", "отчет", "регламент", "инструкц", "архив", "верси"),
    "DESIGN_ENGINEER": ("pcb", "kicad", "схем", "плата", "трасс", "bom", "компонент"),
    "PROJECT_MANAGER": ("план", "срок", "задач", "приоритет", "статус", "блокер"),
    "LEARNING_COORDINATOR": ("обуч", "навык", "skill", "знани", "источник", "программ"),
    "RESEARCH_ASSISTANT": ("даташит", "datasheet", "источник", "поиск", "manufacturer", "стандарт"),
}


@dataclass(frozen=True)
class ContextSnapshot:
    immediate_lines: list[str]
    relevant_lines: list[str]
    accepted_facts: list[str]
    unresolved_questions: list[str]

    def prompt_lines(self) -> list[str]:
        lines = ["IMMEDIATE CONTEXT:"]
        lines.extend(self.immediate_lines or ["- нет"])
        lines.append("TASK-RELEVANT CONTEXT:")
        lines.extend(self.relevant_lines or ["- нет"])
        lines.append("ACCEPTED FACTS:")
        lines.extend(self.accepted_facts or ["- нет"])
        lines.append("UNRESOLVED QUESTIONS:")
        lines.extend(self.unresolved_questions or ["- нет"])
        return lines


class ContextSnapshotService:
    """Selects relevant context instead of dumping raw chat history."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def build(
        self,
        *,
        conversation_id: int,
        user_message: str,
        agent_key: str,
        thread_owner_keys: list[str] | None = None,
        immediate_limit: int = 8,
        relevant_limit: int = 12,
    ) -> ContextSnapshot:
        messages = self.database.list_messages(conversation_id, limit=100)
        agent = get_chat_agent(self.database, agent_key)
        thread_owner_keys = thread_owner_keys or []
        recent_window = messages[-30:]
        immediate = self._rank_relevant(
            recent_window,
            user_message=user_message,
            agent=agent,
            agent_key=agent_key,
            thread_owner_keys=thread_owner_keys,
            excluded_ids=set(),
            limit=immediate_limit,
        )
        if not immediate:
            immediate = messages[-immediate_limit:]
        immediate_ids = {message.id for message in immediate}
        relevant = self._rank_relevant(
            messages,
            user_message=user_message,
            agent=agent,
            agent_key=agent_key,
            thread_owner_keys=thread_owner_keys,
            excluded_ids=immediate_ids,
            limit=relevant_limit,
        )
        return ContextSnapshot(
            immediate_lines=[self._format(message) for message in immediate],
            relevant_lines=[self._format(message) for message in relevant],
            accepted_facts=self._facts(messages),
            unresolved_questions=self._questions(messages),
        )

    def _rank_relevant(
        self,
        messages: list[Message],
        *,
        user_message: str,
        agent: ChatAgent | None,
        agent_key: str,
        thread_owner_keys: list[str],
        excluded_ids: set[int],
        limit: int,
    ) -> list[Message]:
        query_tokens = self._tokens(user_message)
        role_terms = self._role_terms(agent)
        scored: list[tuple[int, int, Message]] = []
        for index, message in enumerate(messages):
            if message.id in excluded_ids:
                continue
            message_tokens = self._tokens(message.content)
            score = 0
            score += 4 * len(query_tokens & message_tokens)
            if message.role == agent_key:
                score += 5
            if message.role in thread_owner_keys:
                score += 4
            lowered = message.content.lower().replace("ё", "е")
            score += sum(2 for term in role_terms if term in lowered)
            if "?" in message.content:
                score += 1
            if score:
                scored.append((score, index, message))
        scored.sort(key=lambda item: (-item[0], item[1]))
        selected = sorted((message for _score, _index, message in scored[:limit]), key=lambda item: item.id)
        return selected

    def _role_terms(self, agent: ChatAgent | None) -> tuple[str, ...]:
        if agent is None:
            return ()
        terms: list[str] = []
        for role in agent.roles:
            terms.extend(ROLE_CONTEXT_TERMS.get(role, ()))
        return tuple(terms)

    def _facts(self, messages: list[Message]) -> list[str]:
        facts: list[str] = []
        for message in messages[-40:]:
            lowered = message.content.lower().replace("ё", "е")
            if any(marker in lowered for marker in ("принято", "фиксирую", "решили", "договор")):
                facts.append(f"- {self._trim(message.content)}")
        return facts[-6:]

    def _questions(self, messages: list[Message]) -> list[str]:
        conversation_id = messages[-1].conversation_id if messages else None
        if conversation_id is not None:
            try:
                rows = self.database.list_thread_questions(conversation_id=conversation_id, status="OPEN", limit=6)
            except sqlite3.Error:
                rows = []
            if rows:
                result = []
                for row in reversed(rows):
                    assigned = row["assigned_agent_keys"] or "[]"
                    result.append(f"- {self._trim(str(row['question_text']))} [assigned: {assigned}]")
                return result
        questions = [f"- {self._trim(message.content)}" for message in messages[-30:] if "?" in message.content]
        return questions[-6:]

    def _format(self, message: Message) -> str:
        return f"- {self._role_label(message.role)}: {self._trim(message.content)}"

    def _role_label(self, role: str) -> str:
        labels = {"user": "Пользователь", "roman": "Роман", "petr": "Петр", "system": "Система"}
        if role in labels:
            return labels[role]
        agent = get_chat_agent(self.database, role)
        return agent.display_name if agent is not None else role

    @staticmethod
    def _tokens(text: str) -> set[str]:
        words = re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", text.lower().replace("ё", "е"))
        return {word for word in words if len(word) >= 3 and word not in STOP_WORDS}

    @staticmethod
    def _trim(text: str, limit: int = 360) -> str:
        clean = " ".join(text.strip().split())
        if len(clean) <= limit:
            return clean
        return f"{clean[: limit - 1].rstrip()}…"
