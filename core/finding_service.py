from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .database import Database


FINDING_SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
FINDING_CONFIDENCE = ("LOW", "MEDIUM", "HIGH")
FINDING_STATUSES = ("OPEN", "IN_REWORK", "READY_FOR_RECHECK", "RESOLVED", "ACCEPTED_RISK", "REJECTED", "DEFERRED")


@dataclass(frozen=True)
class Finding:
    finding_id: str
    task_id: str
    reviewer_run_id: str
    severity: str
    confidence: str
    affected_artifact: str
    location: str
    evidence: str
    description: str
    impact: str
    required_action: str
    status: str
    resolution: str
    standard_id: str
    finding_type: str
    repeat_key: str
    independent_recheck_status: str
    updated_at: str


@dataclass(frozen=True)
class FindingEvent:
    event_id: str
    finding_id: str
    event_type: str
    actor: str
    detail: str
    created_at: str


class FindingService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create_finding(
        self,
        *,
        task_id: str,
        description: str,
        severity: str = "MEDIUM",
        confidence: str = "MEDIUM",
        reviewer_run_id: str | None = None,
        affected_artifact: str = "",
        location: str = "",
        evidence: dict | list | str | None = None,
        impact: str = "",
        required_action: str = "",
        standard_id: str | None = None,
        finding_type: str = "QA_FINDING",
        actor: str = "owner",
    ) -> str:
        description = " ".join(description.strip().split())
        if not task_id.strip():
            raise ValueError("Задача обязательна.")
        if not description:
            raise ValueError("Описание finding обязательно.")
        self._require_severity(severity)
        self._require_confidence(confidence)
        repeat_key = self._repeat_key(standard_id, affected_artifact, location, description)
        return self.database.create_finding(
            task_id=task_id.strip(),
            description=description,
            severity=severity,
            confidence=confidence,
            reviewer_run_id=reviewer_run_id,
            affected_artifact=affected_artifact.strip(),
            location=location.strip(),
            evidence=evidence,
            impact=impact.strip(),
            required_action=required_action.strip(),
            status="OPEN",
            standard_id=standard_id,
            finding_type=finding_type.strip() or "QA_FINDING",
            repeat_key=repeat_key,
            actor=actor,
        )

    def import_from_structured_response(
        self,
        *,
        envelope: dict[str, Any] | None,
        task_id: str | None = None,
        reviewer_run_id: str | None = None,
        actor: str = "agent",
    ) -> list[str]:
        if not isinstance(envelope, dict):
            return []
        items = envelope.get("findings")
        if not isinstance(items, list) or not items:
            return []

        resolved_task_id = self._text(task_id) or self._text(envelope.get("task_id"))
        if not resolved_task_id:
            return []
        resolved_run_id = self._text(reviewer_run_id) or self._text(envelope.get("run_id")) or None
        existing = {
            (finding.reviewer_run_id, finding.repeat_key)
            for finding in self.list_findings(task_id=resolved_task_id)
        }

        created: list[str] = []
        for item in items:
            data = self._normalize_structured_finding(item)
            description = data["description"]
            if not description:
                continue
            repeat_key = self._repeat_key(
                data["standard_id"],
                data["affected_artifact"],
                data["location"],
                description,
            )
            if resolved_run_id and (resolved_run_id, repeat_key) in existing:
                continue
            finding_id = self.create_finding(
                task_id=resolved_task_id,
                description=description,
                severity=data["severity"],
                confidence=data["confidence"],
                reviewer_run_id=resolved_run_id,
                affected_artifact=data["affected_artifact"],
                location=data["location"],
                evidence=data["evidence"],
                impact=data["impact"],
                required_action=data["required_action"],
                standard_id=data["standard_id"] or None,
                finding_type=data["finding_type"],
                actor=actor,
            )
            created.append(finding_id)
            existing.add((resolved_run_id or "", repeat_key))
        return created

    def list_findings(self, status: str | None = None, task_id: str | None = None) -> list[Finding]:
        return [self._finding_from_row(row) for row in self.database.list_findings(status=status, task_id=task_id)]

    def update_status(
        self,
        finding_id: str,
        status: str,
        *,
        actor: str = "owner",
        resolution: str = "",
        resolved_by_run_id: str | None = None,
        independent_recheck_status: str | None = None,
    ) -> None:
        self._require_status(status)
        self.database.update_finding_status(
            finding_id,
            status,
            actor=actor,
            resolution=resolution.strip(),
            resolved_by_run_id=resolved_by_run_id,
            independent_recheck_status=independent_recheck_status,
        )

    def list_events(self, finding_id: str | None = None) -> list[FindingEvent]:
        return [self._event_from_row(row) for row in self.database.list_finding_events(finding_id)]

    @staticmethod
    def is_blocking(finding: Finding) -> bool:
        return finding.status not in {"RESOLVED", "ACCEPTED_RISK", "REJECTED", "DEFERRED"} and finding.severity in {"HIGH", "CRITICAL"}

    @staticmethod
    def _require_severity(severity: str) -> None:
        if severity not in FINDING_SEVERITIES:
            raise ValueError(f"Недопустимая серьезность finding: {severity}")

    @staticmethod
    def _require_confidence(confidence: str) -> None:
        if confidence not in FINDING_CONFIDENCE:
            raise ValueError(f"Недопустимая уверенность finding: {confidence}")

    @staticmethod
    def _require_status(status: str) -> None:
        if status not in FINDING_STATUSES:
            raise ValueError(f"Недопустимый статус finding: {status}")

    @staticmethod
    def _repeat_key(standard_id: str | None, artifact: str, location: str, description: str) -> str:
        base = "|".join(
            [
                (standard_id or "").strip().lower(),
                artifact.strip().lower(),
                location.strip().lower(),
                " ".join(description.lower().split())[:120],
            ]
        )
        return base.strip("|")

    @classmethod
    def _normalize_structured_finding(cls, item: object) -> dict[str, Any]:
        if isinstance(item, str):
            item = {"description": item, "confidence": "LOW"}
        if not isinstance(item, dict):
            return {
                "description": "",
                "severity": "MEDIUM",
                "confidence": "LOW",
                "affected_artifact": "",
                "location": "",
                "evidence": {},
                "impact": "",
                "required_action": "",
                "standard_id": "",
                "finding_type": "QA_FINDING",
            }
        description = cls._first_text(item, "description", "summary", "issue", "finding")
        affected_artifact = cls._first_text(item, "affected_artifact", "artifact", "file", "path")
        location = cls._first_text(item, "location", "line", "section", "component", "net")
        evidence = item.get("evidence", {})
        if not isinstance(evidence, (dict, list, str)):
            evidence = cls._text(evidence)
        return {
            "description": " ".join(description.split()),
            "severity": cls._normalize_choice(item.get("severity"), FINDING_SEVERITIES, "MEDIUM"),
            "confidence": cls._normalize_choice(item.get("confidence"), FINDING_CONFIDENCE, "MEDIUM"),
            "affected_artifact": affected_artifact,
            "location": location,
            "evidence": evidence,
            "impact": cls._first_text(item, "impact", "risk", "consequence"),
            "required_action": cls._first_text(item, "required_action", "action", "fix", "recommendation"),
            "standard_id": cls._first_text(item, "standard_id", "standard", "rule_id"),
            "finding_type": cls._first_text(item, "finding_type", "type") or "QA_FINDING",
        }

    @staticmethod
    def _normalize_choice(value: object, allowed: tuple[str, ...], default: str) -> str:
        text = FindingService._text(value).upper()
        return text if text in allowed else default

    @staticmethod
    def _first_text(data: dict[str, object], *keys: str) -> str:
        for key in keys:
            text = FindingService._text(data.get(key))
            if text:
                return text
        return ""

    @staticmethod
    def _text(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    @staticmethod
    def _finding_from_row(row) -> Finding:
        return Finding(
            finding_id=str(row["id"]),
            task_id=str(row["task_id"]),
            reviewer_run_id=str(row["reviewer_run_id"] or ""),
            severity=str(row["severity"]),
            confidence=str(row["confidence"]),
            affected_artifact=str(row["affected_artifact"] or ""),
            location=str(row["location"] or ""),
            evidence=str(row["evidence"] or ""),
            description=str(row["description"]),
            impact=str(row["impact"] or ""),
            required_action=str(row["required_action"] or ""),
            status=str(row["status"]),
            resolution=str(row["resolution"] or ""),
            standard_id=str(row["standard_id"] or ""),
            finding_type=str(row["finding_type"] or ""),
            repeat_key=str(row["repeat_key"] or ""),
            independent_recheck_status=str(row["independent_recheck_status"] or ""),
            updated_at=str(row["updated_at"] or ""),
        )

    @staticmethod
    def _event_from_row(row) -> FindingEvent:
        return FindingEvent(
            event_id=str(row["id"]),
            finding_id=str(row["finding_id"]),
            event_type=str(row["event_type"]),
            actor=str(row["actor"]),
            detail=str(row["detail"] or ""),
            created_at=str(row["created_at"] or ""),
        )
