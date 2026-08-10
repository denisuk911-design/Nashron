from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ClaimValidationResult(StrEnum):
    CLAIM_SUPPORTED = "CLAIM_SUPPORTED"
    CLAIM_PARTIALLY_SUPPORTED = "CLAIM_PARTIALLY_SUPPORTED"
    CLAIM_UNSUPPORTED = "CLAIM_UNSUPPORTED"
    CLAIM_CONTRADICTED = "CLAIM_CONTRADICTED"


COMPLETION_PHRASES = (
    "проверил",
    "проверила",
    "проверено",
    "подтвердил",
    "подтвердила",
    "подтверждено",
    "доступ есть",
    "права есть",
    "файл исправлен",
    "исправил файл",
    "исправила файл",
    "задача выполнена",
    "ошибок нет",
    "источник найден",
    "изучил книгу",
    "изучила книгу",
    "навык освоен",
    "обучение завершено",
)

SOURCE_PHRASES = (
    "стандарт требует",
    "по стандарту",
    "согласно стандарту",
    "даташит требует",
)

FILE_READ_PHRASES = ("прочитал файл", "прочитала файл", "читал файл", "открыл файл", "открыла файл")
FILE_CHANGED_PHRASES = ("создал файл", "создала файл", "изменил файл", "изменила файл", "записал файл", "записала файл")
SKILL_MASTERED_PHRASES = ("навык освоен", "освоил навык", "освоила навык", "обучение завершено")


@dataclass(frozen=True)
class ClaimValidation:
    result: ClaimValidationResult
    unsupported_phrases: list[str] = field(default_factory=list)
    supported_evidence_count: int = 0

    @property
    def blocks_skill_update(self) -> bool:
        return self.result in {ClaimValidationResult.CLAIM_UNSUPPORTED, ClaimValidationResult.CLAIM_CONTRADICTED}

    @property
    def warning(self) -> str:
        if not self.unsupported_phrases:
            return ""
        phrases = ", ".join(self.unsupported_phrases[:5])
        return f"Заявление сотрудника не подтверждено данными: {phrases}."


class ClaimEvidenceValidator:
    EVIDENCE_FIELDS = ("evidence", "checks")

    def validate(self, human_text: str, envelope: dict[str, Any] | None) -> ClaimValidation:
        lowered = human_text.lower().replace("ё", "е")
        evidence_count = self._evidence_count(envelope)
        unsupported: list[str] = []

        for phrase in COMPLETION_PHRASES:
            if phrase.replace("ё", "е") in lowered and evidence_count == 0:
                unsupported.append(phrase)
        if any(phrase in lowered for phrase in SOURCE_PHRASES) and not self._has_source_evidence(envelope):
            unsupported.append("утверждение о стандарте без источника")
        if any(phrase in lowered for phrase in FILE_READ_PHRASES) and not self._has_real_evidence(envelope, "files_read"):
            unsupported.append("чтение файла без evidence")
        if any(phrase in lowered for phrase in FILE_CHANGED_PHRASES) and not self._has_real_evidence(envelope, "files_created", "files_modified"):
            unsupported.append("изменение файла без evidence")
        if any(phrase in lowered for phrase in SKILL_MASTERED_PHRASES):
            unsupported.append("освоение навыка не подтверждается сообщением")

        if unsupported:
            return ClaimValidation(ClaimValidationResult.CLAIM_UNSUPPORTED, sorted(set(unsupported)), evidence_count)
        if evidence_count:
            return ClaimValidation(ClaimValidationResult.CLAIM_SUPPORTED, [], evidence_count)
        return ClaimValidation(ClaimValidationResult.CLAIM_PARTIALLY_SUPPORTED, [], 0)

    def _evidence_count(self, envelope: dict[str, Any] | None) -> int:
        if not isinstance(envelope, dict):
            return 0
        total = 0
        evidence = envelope.get("evidence")
        if isinstance(evidence, list):
            total += len([item for item in evidence if isinstance(item, dict) and item])
        checks = envelope.get("checks")
        if isinstance(checks, list):
            total += len([item for item in checks if self._check_has_evidence(item)])
        return total

    def _has_source_evidence(self, envelope: dict[str, Any] | None) -> bool:
        if not isinstance(envelope, dict):
            return False
        return self._has_real_evidence(envelope, "source")

    @classmethod
    def _has_real_evidence(cls, envelope: dict[str, Any] | None, *fields: str) -> bool:
        if not isinstance(envelope, dict):
            return False
        evidence = envelope.get("evidence")
        if isinstance(evidence, list) and any(isinstance(item, dict) and item for item in evidence):
            return True
        checks = envelope.get("checks")
        if not isinstance(checks, list):
            return False
        for check in checks:
            if isinstance(check, dict) and cls._check_has_evidence(check):
                return True
            text = str(check).lower()
            if any(token in text for token in ("evidence", "source", "источник", "доказатель", "путь")):
                return True
        return False

    @staticmethod
    def _check_has_evidence(check: object) -> bool:
        if not isinstance(check, dict):
            text = str(check).lower()
            return any(token in text for token in ("evidence", "source", "источник", "доказатель", "путь"))
        return any(check.get(key) for key in ("evidence_path", "evidence_ids", "result", "observed", "output"))
