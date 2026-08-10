from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .database import Database


KNOWLEDGE_STATUSES = ("DRAFT", "NEEDS_SOURCE_RECHECK", "NEEDS_REVIEW", "ACTIVE", "CONFLICTING", "REJECTED", "SUPERSEDED")
SOURCE_AUTHORITIES = ("OFFICIAL", "PRIMARY", "STANDARD", "TEXTBOOK", "INTERNAL_VERIFIED", "COMMUNITY", "UNVERIFIED")


@dataclass(frozen=True)
class KnowledgeCard:
    knowledge_id: str
    title: str
    summary: str
    content: str
    source_type: str
    source_title: str
    source_uri: str
    source_authority: str
    source_hash: str
    role_ids: list[str]
    tags: list[str]
    status: str
    version: str
    review_notes: str
    updated_at: str


@dataclass(frozen=True)
class KnowledgeEvent:
    event_id: str
    knowledge_id: str
    event_type: str
    actor: str
    detail: str
    created_at: str


@dataclass(frozen=True)
class KnowledgeUsageCounts:
    supplied: int = 0
    applied: int = 0
    ignored: int = 0
    misapplied: int = 0


class KnowledgeService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create_card(
        self,
        *,
        title: str,
        summary: str = "",
        content: str = "",
        source_type: str = "internal_note",
        source_title: str = "",
        source_uri: str = "",
        source_authority: str = "UNVERIFIED",
        source_hash: str = "",
        role_ids: list[str] | None = None,
        tags: list[str] | None = None,
        status: str = "DRAFT",
        version: str = "0.1.0",
        review_notes: str = "",
        actor: str = "owner",
    ) -> str:
        title = " ".join(title.strip().split())
        if not title:
            raise ValueError("Название знания обязательно.")
        self._require_status(status)
        self._require_authority(source_authority)
        return self.database.create_knowledge_card(
            title=title,
            summary=summary.strip(),
            content=content.strip(),
            source_type=source_type.strip() or "internal_note",
            source_title=source_title.strip(),
            source_uri=source_uri.strip(),
            source_authority=source_authority,
            source_hash=source_hash.strip(),
            role_ids=role_ids or [],
            tags=tags or [],
            status=status,
            version=version.strip() or "0.1.0",
            review_notes=review_notes.strip(),
            actor=actor,
        )

    def list_cards(self, status: str | None = None) -> list[KnowledgeCard]:
        return [self._card_from_row(row) for row in self.database.list_knowledge_cards(status)]

    def update_status(self, knowledge_id: str, status: str, *, actor: str = "owner", reason: str = "") -> None:
        self._require_status(status)
        self.database.update_knowledge_card_status(knowledge_id, status, actor, reason.strip())

    def list_events(self, knowledge_id: str | None = None) -> list[KnowledgeEvent]:
        return [self._event_from_row(row) for row in self.database.list_knowledge_card_events(knowledge_id)]

    def usage_counts_by_card(self) -> dict[str, KnowledgeUsageCounts]:
        with self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT knowledge_id, usage_type, COUNT(*) AS count
                FROM knowledge_usage
                GROUP BY knowledge_id, usage_type
                """
            ).fetchall()
        raw: dict[str, dict[str, int]] = {}
        for row in rows:
            card_id = str(row["knowledge_id"])
            usage_type = str(row["usage_type"]).lower()
            if usage_type not in {"supplied", "applied", "ignored", "misapplied"}:
                continue
            raw.setdefault(card_id, {})[usage_type] = int(row["count"])
        return {
            card_id: KnowledgeUsageCounts(
                supplied=values.get("supplied", 0),
                applied=values.get("applied", 0),
                ignored=values.get("ignored", 0),
                misapplied=values.get("misapplied", 0),
            )
            for card_id, values in raw.items()
        }

    def relevant_active_cards(self, query: str, role_id: str = "", limit: int = 5) -> list[KnowledgeCard]:
        query_tokens = _tokens(query)
        role_id = role_id.strip()
        scored: list[tuple[int, KnowledgeCard]] = []
        for card in self.list_cards("ACTIVE"):
            role_score = 2 if not card.role_ids or role_id in card.role_ids else 0
            if card.role_ids and role_id not in card.role_ids:
                continue
            haystack = " ".join([card.title, card.summary, card.content, " ".join(card.tags)]).lower()
            token_score = sum(1 for token in query_tokens if token in haystack)
            authority_score = 1 if card.source_authority in {"OFFICIAL", "PRIMARY", "STANDARD", "INTERNAL_VERIFIED"} else 0
            score = role_score + token_score + authority_score
            if score > 0:
                scored.append((score, card))
        scored.sort(key=lambda item: (-item[0], item[1].title.lower()))
        return [card for _score, card in scored[:limit]]

    def prompt_lines(self, cards: list[KnowledgeCard]) -> list[str]:
        if not cards:
            return ["- нет активных релевантных карточек знаний"]
        lines: list[str] = []
        for card in cards:
            source = card.source_title or card.source_uri or "источник не указан"
            summary = card.summary or card.content[:220]
            lines.append(
                f"- [{card.knowledge_id}] {card.title} ({card.source_authority}; {source}): {summary}"
            )
        return lines

    @staticmethod
    def _require_status(status: str) -> None:
        if status not in KNOWLEDGE_STATUSES:
            raise ValueError(f"Недопустимый статус знания: {status}")

    @staticmethod
    def _require_authority(authority: str) -> None:
        if authority not in SOURCE_AUTHORITIES:
            raise ValueError(f"Недопустимая надежность источника: {authority}")

    def _card_from_row(self, row) -> KnowledgeCard:
        return KnowledgeCard(
            knowledge_id=str(row["id"]),
            title=str(row["title"]),
            summary=str(row["summary"] or ""),
            content=str(row["content"] or ""),
            source_type=str(row["source_type"] or ""),
            source_title=str(row["source_title"] or ""),
            source_uri=str(row["source_uri"] or ""),
            source_authority=str(row["source_authority"] or ""),
            source_hash=str(row["source_hash"] or ""),
            role_ids=self._json_list(row["role_ids"]),
            tags=self._json_list(row["tags"]),
            status=str(row["status"] or ""),
            version=str(row["version"] or ""),
            review_notes=str(row["review_notes"] or ""),
            updated_at=str(row["updated_at"] or ""),
        )

    @staticmethod
    def _event_from_row(row) -> KnowledgeEvent:
        return KnowledgeEvent(
            event_id=str(row["id"]),
            knowledge_id=str(row["knowledge_id"]),
            event_type=str(row["event_type"]),
            actor=str(row["actor"]),
            detail=str(row["detail"] or ""),
            created_at=str(row["created_at"] or ""),
        )

    @staticmethod
    def _json_list(value: Any) -> list[str]:
        payload = Database.loads(str(value or "[]"), [])
        if not isinstance(payload, list):
            return []
        return [str(item) for item in payload if str(item).strip()]


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9_]{3,}", text.lower().replace("ё", "е"))}
