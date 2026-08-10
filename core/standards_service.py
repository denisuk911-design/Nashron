from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .database import Database


STANDARD_STATUSES = ("DRAFT", "NEEDS_REVIEW", "ACTIVE", "SUSPENDED", "CONFLICTING", "REJECTED", "SUPERSEDED")
STANDARD_AUTHORITIES = ("OFFICIAL", "STANDARD_BODY", "MANUFACTURER", "INTERNAL", "PROJECT", "UNVERIFIED")
MANDATORY_LEVELS = ("MANDATORY", "RECOMMENDED", "GUIDANCE")


@dataclass(frozen=True)
class StandardCard:
    standard_id: str
    code: str
    title: str
    requirement: str
    scope: str
    source_title: str
    source_uri: str
    source_hash: str
    authority: str
    mandatory_level: str
    role_ids: list[str]
    tags: list[str]
    status: str
    version: str
    review_notes: str
    updated_at: str


@dataclass(frozen=True)
class StandardEvent:
    event_id: str
    standard_id: str
    event_type: str
    actor: str
    detail: str
    created_at: str


@dataclass(frozen=True)
class StandardUsageCounts:
    supplied: int = 0
    applied: int = 0
    ignored: int = 0
    misapplied: int = 0


class StandardsService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create_card(
        self,
        *,
        code: str,
        title: str,
        requirement: str = "",
        scope: str = "",
        source_title: str = "",
        source_uri: str = "",
        source_hash: str = "",
        authority: str = "INTERNAL",
        mandatory_level: str = "GUIDANCE",
        role_ids: list[str] | None = None,
        tags: list[str] | None = None,
        status: str = "DRAFT",
        version: str = "0.1.0",
        review_notes: str = "",
        actor: str = "owner",
    ) -> str:
        code = " ".join(code.strip().split())
        title = " ".join(title.strip().split())
        if not code:
            raise ValueError("Код стандарта обязателен.")
        if not title:
            raise ValueError("Название стандарта обязательно.")
        self._require_status(status)
        self._require_authority(authority)
        self._require_mandatory_level(mandatory_level)
        return self.database.create_standard_card(
            code=code,
            title=title,
            requirement=requirement.strip(),
            scope=scope.strip(),
            source_title=source_title.strip(),
            source_uri=source_uri.strip(),
            source_hash=source_hash.strip(),
            authority=authority,
            mandatory_level=mandatory_level,
            role_ids=role_ids or [],
            tags=tags or [],
            status=status,
            version=version.strip() or "0.1.0",
            review_notes=review_notes.strip(),
            actor=actor,
        )

    def list_cards(self, status: str | None = None) -> list[StandardCard]:
        return [self._card_from_row(row) for row in self.database.list_standard_cards(status)]

    def update_status(self, standard_id: str, status: str, *, actor: str = "owner", reason: str = "") -> None:
        self._require_status(status)
        self.database.update_standard_card_status(standard_id, status, actor, reason.strip())

    def list_events(self, standard_id: str | None = None) -> list[StandardEvent]:
        return [self._event_from_row(row) for row in self.database.list_standard_card_events(standard_id)]

    def usage_counts_by_card(self) -> dict[str, StandardUsageCounts]:
        with self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT standard_id, usage_type, COUNT(*) AS count
                FROM standard_usage
                GROUP BY standard_id, usage_type
                """
            ).fetchall()
        raw: dict[str, dict[str, int]] = {}
        for row in rows:
            card_id = str(row["standard_id"])
            usage_type = str(row["usage_type"]).lower()
            if usage_type not in {"supplied", "applied", "ignored", "misapplied"}:
                continue
            raw.setdefault(card_id, {})[usage_type] = int(row["count"])
        return {
            card_id: StandardUsageCounts(
                supplied=values.get("supplied", 0),
                applied=values.get("applied", 0),
                ignored=values.get("ignored", 0),
                misapplied=values.get("misapplied", 0),
            )
            for card_id, values in raw.items()
        }

    def relevant_active_cards(self, query: str, role_id: str = "", limit: int = 5) -> list[StandardCard]:
        query_tokens = _tokens(query)
        role_id = role_id.strip()
        scored: list[tuple[int, StandardCard]] = []
        for card in self.list_cards("ACTIVE"):
            if card.role_ids and role_id not in card.role_ids:
                continue
            haystack = " ".join([card.code, card.title, card.requirement, card.scope, " ".join(card.tags)]).lower()
            token_score = sum(1 for token in query_tokens if token in haystack)
            role_score = 2 if not card.role_ids or role_id in card.role_ids else 0
            mandatory_score = 2 if card.mandatory_level == "MANDATORY" else 1 if card.mandatory_level == "RECOMMENDED" else 0
            authority_score = 1 if card.authority in {"OFFICIAL", "STANDARD_BODY", "MANUFACTURER", "INTERNAL"} else 0
            score = token_score + role_score + mandatory_score + authority_score
            if score > 0:
                scored.append((score, card))
        scored.sort(key=lambda item: (-item[0], item[1].code.lower()))
        return [card for _score, card in scored[:limit]]

    def prompt_lines(self, cards: list[StandardCard]) -> list[str]:
        if not cards:
            return ["- нет активных релевантных стандартов"]
        lines: list[str] = []
        for card in cards:
            source = card.source_title or card.source_uri or "источник не указан"
            requirement = card.requirement or card.scope or "требование не заполнено"
            lines.append(
                f"- [{card.standard_id}] {card.code} {card.title} ({card.mandatory_level}; {card.authority}; {source}): {requirement}"
            )
        return lines

    @staticmethod
    def _require_status(status: str) -> None:
        if status not in STANDARD_STATUSES:
            raise ValueError(f"Недопустимый статус стандарта: {status}")

    @staticmethod
    def _require_authority(authority: str) -> None:
        if authority not in STANDARD_AUTHORITIES:
            raise ValueError(f"Недопустимый тип источника стандарта: {authority}")

    @staticmethod
    def _require_mandatory_level(level: str) -> None:
        if level not in MANDATORY_LEVELS:
            raise ValueError(f"Недопустимая обязательность стандарта: {level}")

    def _card_from_row(self, row) -> StandardCard:
        return StandardCard(
            standard_id=str(row["id"]),
            code=str(row["code"]),
            title=str(row["title"]),
            requirement=str(row["requirement"] or ""),
            scope=str(row["scope"] or ""),
            source_title=str(row["source_title"] or ""),
            source_uri=str(row["source_uri"] or ""),
            source_hash=str(row["source_hash"] or ""),
            authority=str(row["authority"] or ""),
            mandatory_level=str(row["mandatory_level"] or ""),
            role_ids=self._json_list(row["role_ids"]),
            tags=self._json_list(row["tags"]),
            status=str(row["status"] or ""),
            version=str(row["version"] or ""),
            review_notes=str(row["review_notes"] or ""),
            updated_at=str(row["updated_at"] or ""),
        )

    @staticmethod
    def _event_from_row(row) -> StandardEvent:
        return StandardEvent(
            event_id=str(row["id"]),
            standard_id=str(row["standard_id"]),
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
