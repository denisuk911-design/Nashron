from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .database import Database


USAGE_OUTCOMES = {"APPLIED", "IGNORED", "MISAPPLIED"}


@dataclass(frozen=True)
class UsageImportResult:
    knowledge_recorded: int = 0
    standards_recorded: int = 0
    rejected: int = 0


class KnowledgeApplicationService:
    """Records whether supplied knowledge and standards were accounted for.

    This service intentionally trusts only structured response fields and only
    for cards that were supplied to the same run. Free-form chat claims do not
    create application evidence.
    """

    def __init__(self, database: Database) -> None:
        self.database = database

    def import_from_structured_response(
        self,
        *,
        envelope: dict[str, Any],
        task_id: str | None = None,
        run_id: str | None = None,
        role: str = "",
        actor: str = "",
    ) -> UsageImportResult:
        if not run_id:
            return UsageImportResult()
        resolved_task_id = str(envelope.get("task_id") or task_id or "")
        resolved_role = str(envelope.get("role") or role or "")

        supplied_knowledge = self._supplied_ids("knowledge_usage", "knowledge_id", run_id)
        supplied_standards = self._supplied_ids("standard_usage", "standard_id", run_id)
        existing_knowledge = self._existing_outcomes("knowledge_usage", "knowledge_id", run_id)
        existing_standards = self._existing_outcomes("standard_usage", "standard_id", run_id)

        knowledge_result = self._record_knowledge(
            entries=self._usage_entries(envelope, ("knowledge_used", "knowledge_usage", "knowledge_applied")),
            supplied_ids=supplied_knowledge,
            existing=existing_knowledge,
            task_id=resolved_task_id or task_id,
            run_id=run_id,
            role=resolved_role,
            actor=actor,
        )
        standards_result = self._record_standards(
            entries=self._usage_entries(envelope, ("standards_used", "standard_usage", "standards_applied")),
            supplied_ids=supplied_standards,
            existing=existing_standards,
            task_id=resolved_task_id or task_id,
            run_id=run_id,
            role=resolved_role,
            actor=actor,
        )
        ignored_knowledge = self._record_missing_knowledge(
            supplied_ids=supplied_knowledge,
            existing=existing_knowledge | knowledge_result["seen"],
            task_id=resolved_task_id or task_id,
            run_id=run_id,
            role=resolved_role,
            actor=actor,
        )
        ignored_standards = self._record_missing_standards(
            supplied_ids=supplied_standards,
            existing=existing_standards | standards_result["seen"],
            task_id=resolved_task_id or task_id,
            run_id=run_id,
            role=resolved_role,
            actor=actor,
        )
        rejected = knowledge_result["rejected"] + standards_result["rejected"]
        if rejected:
            self.database.log_event("usage_application_rejected", f"{actor}: {rejected} not supplied")
        return UsageImportResult(
            knowledge_recorded=knowledge_result["recorded"] + ignored_knowledge,
            standards_recorded=standards_result["recorded"] + ignored_standards,
            rejected=rejected,
        )

    def record_standard_misapplications_from_findings(
        self,
        *,
        finding_ids: list[str],
        run_id: str | None,
        task_id: str | None = None,
        role: str = "",
        actor: str = "",
    ) -> int:
        if not finding_ids or not run_id:
            return 0
        supplied_standards = self._supplied_ids("standard_usage", "standard_id", run_id)
        if not supplied_standards:
            return 0
        existing = self._existing_outcomes("standard_usage", "standard_id", run_id)
        placeholders = ",".join("?" for _ in finding_ids)
        with self.database.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, task_id, standard_id, description, severity, confidence
                FROM findings
                WHERE id IN ({placeholders})
                """,
                tuple(finding_ids),
            ).fetchall()
        recorded = 0
        for row in rows:
            standard_id = str(row["standard_id"] or "").strip()
            if not standard_id or standard_id not in supplied_standards or standard_id in existing:
                continue
            self.database.record_standard_usage(
                standard_id=standard_id,
                role=role,
                usage_type="MISAPPLIED",
                task_id=str(row["task_id"] or task_id or ""),
                run_id=run_id,
                evidence={
                    "reason": "structured QA finding references supplied standard",
                    "finding_id": str(row["id"]),
                    "description": str(row["description"] or ""),
                    "severity": str(row["severity"] or ""),
                    "confidence": str(row["confidence"] or ""),
                    "actor": actor,
                },
            )
            existing.add(standard_id)
            recorded += 1
        if recorded:
            self.database.log_event("standard_misapplication_recorded", f"{actor}: {recorded}")
        return recorded

    def _record_knowledge(
        self,
        *,
        entries: list[dict[str, Any]],
        supplied_ids: set[str],
        existing: set[str],
        task_id: str | None,
        run_id: str,
        role: str,
        actor: str,
    ) -> dict[str, Any]:
        recorded = 0
        rejected = 0
        seen: set[str] = set()
        for entry in entries:
            card_id = str(entry.get("id") or entry.get("knowledge_id") or "").strip()
            outcome = self._outcome(entry)
            if not card_id or card_id not in supplied_ids:
                rejected += 1
                continue
            seen.add(card_id)
            if card_id in existing:
                continue
            self.database.record_knowledge_usage(
                knowledge_id=card_id,
                role=role,
                usage_type=outcome,
                task_id=task_id,
                run_id=run_id,
                evidence=self._evidence(entry, actor),
            )
            recorded += 1
        return {"recorded": recorded, "rejected": rejected, "seen": seen}

    def _record_standards(
        self,
        *,
        entries: list[dict[str, Any]],
        supplied_ids: set[str],
        existing: set[str],
        task_id: str | None,
        run_id: str,
        role: str,
        actor: str,
    ) -> dict[str, Any]:
        recorded = 0
        rejected = 0
        seen: set[str] = set()
        for entry in entries:
            card_id = str(entry.get("id") or entry.get("standard_id") or "").strip()
            outcome = self._outcome(entry)
            if not card_id or card_id not in supplied_ids:
                rejected += 1
                continue
            seen.add(card_id)
            if card_id in existing:
                continue
            self.database.record_standard_usage(
                standard_id=card_id,
                role=role,
                usage_type=outcome,
                task_id=task_id,
                run_id=run_id,
                evidence=self._evidence(entry, actor),
            )
            recorded += 1
        return {"recorded": recorded, "rejected": rejected, "seen": seen}

    def _record_missing_knowledge(
        self,
        *,
        supplied_ids: set[str],
        existing: set[str],
        task_id: str | None,
        run_id: str,
        role: str,
        actor: str,
    ) -> int:
        recorded = 0
        for card_id in sorted(supplied_ids - existing):
            self.database.record_knowledge_usage(
                knowledge_id=card_id,
                role=role,
                usage_type="IGNORED",
                task_id=task_id,
                run_id=run_id,
                evidence={"reason": "not referenced in structured response", "actor": actor},
            )
            recorded += 1
        return recorded

    def _record_missing_standards(
        self,
        *,
        supplied_ids: set[str],
        existing: set[str],
        task_id: str | None,
        run_id: str,
        role: str,
        actor: str,
    ) -> int:
        recorded = 0
        for card_id in sorted(supplied_ids - existing):
            self.database.record_standard_usage(
                standard_id=card_id,
                role=role,
                usage_type="IGNORED",
                task_id=task_id,
                run_id=run_id,
                evidence={"reason": "not referenced in structured response", "actor": actor},
            )
            recorded += 1
        return recorded

    def _supplied_ids(self, table: str, id_column: str, run_id: str) -> set[str]:
        with self.database.connect() as conn:
            rows = conn.execute(
                f"SELECT {id_column} FROM {table} WHERE run_id = ? AND usage_type = 'SUPPLIED'",
                (run_id,),
            ).fetchall()
        return {str(row[id_column]) for row in rows}

    def _existing_outcomes(self, table: str, id_column: str, run_id: str) -> set[str]:
        with self.database.connect() as conn:
            rows = conn.execute(
                f"SELECT {id_column} FROM {table} WHERE run_id = ? AND usage_type != 'SUPPLIED'",
                (run_id,),
            ).fetchall()
        return {str(row[id_column]) for row in rows}

    @staticmethod
    def _usage_entries(envelope: dict[str, Any], keys: tuple[str, ...]) -> list[dict[str, Any]]:
        for key in keys:
            value = envelope.get(key)
            if value is None:
                continue
            if not isinstance(value, list):
                return []
            result: list[dict[str, Any]] = []
            for item in value:
                if isinstance(item, str):
                    result.append({"id": item, "outcome": "APPLIED"})
                elif isinstance(item, dict):
                    result.append(dict(item))
            return result
        return []

    @staticmethod
    def _outcome(entry: dict[str, Any]) -> str:
        outcome = str(entry.get("outcome") or entry.get("usage_type") or "APPLIED").strip().upper()
        return outcome if outcome in USAGE_OUTCOMES else "APPLIED"

    @staticmethod
    def _evidence(entry: dict[str, Any], actor: str) -> dict[str, Any]:
        return {
            "reason": str(entry.get("reason") or entry.get("summary") or "").strip(),
            "evidence_ids": entry.get("evidence_ids") if isinstance(entry.get("evidence_ids"), list) else [],
            "influence": str(entry.get("influence") or "").strip(),
            "actor": actor,
        }
