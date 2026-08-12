from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .database import Database


LEARNING_QUEUE_STATUSES = {
    "PROPOSED",
    "APPROVED",
    "IN_PROGRESS",
    "PRACTICE_REQUIRED",
    "READY_FOR_REVIEW",
    "VERIFIED",
    "REJECTED",
}


@dataclass(frozen=True)
class ExperienceRecord:
    record_id: str
    agent_id: str | None
    employee_name: str
    organization_id: str | None
    task_id: str | None
    run_id: str | None
    summary: str
    skills_used: tuple[str, ...]
    errors_found: tuple[str, ...]
    corrections: tuple[str, ...]
    lessons_learned: tuple[str, ...]
    evidence: dict[str, Any]
    outcome: str
    created_at: str


@dataclass(frozen=True)
class LearningQueueItem:
    item_id: str
    agent_id: str | None
    employee_name: str
    competence: str
    reason: str
    source_id: str | None
    status: str
    practice_task: str
    evidence: dict[str, Any]
    created_by: str
    updated_at: str


class LearningEvidenceService:
    """Creates professional-growth records only from persisted work evidence."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def record_completed_run(
        self,
        run_id: str,
        *,
        organization_id: str | None = None,
        summary: str = "",
    ) -> ExperienceRecord | None:
        existing = next((item for item in self.list_experience() if item.run_id == run_id), None)
        if existing is not None:
            return existing
        run = self.database.get_agent_run(run_id)
        if run is None or not int(run["ok"] or 0) or int(run["cancelled"] or 0):
            return None
        profile = self.database.get_agent_profile(str(run["agent_id"]))
        if profile is None:
            return None
        envelope = Database.loads(str(run["parsed_response"] or "{}"), {})
        if not isinstance(envelope, dict):
            envelope = {}
        artifacts, findings, tools, knowledge = self._run_evidence(run_id)
        evidence_count = len(artifacts) + len(findings) + len(tools)
        if evidence_count == 0:
            return None

        skills = self._skills(envelope)
        self._record_skill_usage(run, skills)
        errors = [str(row["description"]) for row in findings if str(row["description"] or "").strip()]
        corrections = self._string_values(envelope.get("files_modified"))
        lessons = [f"Зафиксировано проверяемых следов работы: {evidence_count}."]
        if findings:
            lessons.append(f"Проверка выявила замечаний: {len(findings)}; требуется закрытие по evidence.")
        evidence = {
            "artifact_ids": [str(row["id"]) for row in artifacts],
            "finding_ids": [str(row["id"]) for row in findings],
            "tool_evidence_ids": [str(row["id"]) for row in tools],
            "knowledge_ids": [str(row["knowledge_id"]) for row in knowledge],
        }
        record_id = self.database.create_experience_record(
            {
                "agent_id": str(run["agent_id"]),
                "employee_name": str(profile["display_name"]),
                "organization_id": organization_id,
                "task_id": str(run["task_id"]),
                "run_id": run_id,
                "summary": " ".join(summary.split())[:500],
                "skills_used": skills,
                "errors_found": errors,
                "corrections": corrections,
                "lessons_learned": lessons,
                "knowledge_created": [str(row["knowledge_id"]) for row in knowledge],
                "evidence": evidence,
                "outcome": "REVIEW_FINDINGS" if findings else "EVIDENCE_RECORDED",
            }
        )
        record = next(item for item in self.list_experience() if item.record_id == record_id)
        if findings:
            self._propose_correction_learning(record, str(run["logical_role"] or "Professional practice"))
        return record

    def propose_learning(
        self,
        *,
        agent_id: str,
        competence: str,
        reason: str,
        evidence: dict[str, Any],
        practice_task: str = "",
        source_id: str | None = None,
        created_by: str = "SYSTEM_LEARNING_MANAGER",
    ) -> str:
        if not competence.strip() or not reason.strip():
            raise ValueError("competence_and_reason_required")
        if not evidence:
            raise ValueError("learning_evidence_required")
        profile = self.database.get_agent_profile(agent_id)
        if profile is None:
            raise ValueError("unknown_employee")
        return self.database.create_learning_queue_item(
            {
                "agent_id": agent_id,
                "employee_name": str(profile["display_name"]),
                "competence": competence.strip(),
                "reason": reason.strip(),
                "source_id": source_id,
                "status": "PROPOSED",
                "practice_task": practice_task.strip(),
                "evidence": evidence,
                "created_by": created_by,
            }
        )

    def update_learning_status(self, item_id: str, status: str, evidence: dict[str, Any]) -> None:
        if status not in LEARNING_QUEUE_STATUSES:
            raise ValueError("invalid_learning_status")
        if status == "VERIFIED" and not evidence:
            raise ValueError("verification_evidence_required")
        self.database.update_learning_queue_status(item_id, status, evidence)

    def list_experience(self, agent_id: str | None = None) -> list[ExperienceRecord]:
        return [self._experience(row) for row in self.database.list_experience_records(agent_id)]

    def list_learning_queue(self, agent_id: str | None = None) -> list[LearningQueueItem]:
        return [self._queue_item(row) for row in self.database.list_learning_queue(agent_id)]

    def _run_evidence(self, run_id: str):
        with self.database.connect() as conn:
            artifacts = conn.execute(
                "SELECT id, relative_path, validation_status FROM artifacts WHERE created_by_run_id = ? AND deleted = 0",
                (run_id,),
            ).fetchall()
            findings = conn.execute(
                "SELECT id, description, severity, status FROM findings WHERE reviewer_run_id = ?",
                (run_id,),
            ).fetchall()
            tools = conn.execute(
                "SELECT id, tool_name, evidence_path, result FROM tool_evidence WHERE run_id = ?",
                (run_id,),
            ).fetchall()
            knowledge = conn.execute(
                "SELECT knowledge_id, usage_type FROM knowledge_usage WHERE run_id = ?",
                (run_id,),
            ).fetchall()
        return artifacts, findings, tools, knowledge

    def _record_skill_usage(self, run: Any, skills: list[str]) -> None:
        if not skills:
            return
        with self.database.connect() as conn:
            existing = {
                str(row["skill_id"]).strip().lower()
                for row in conn.execute("SELECT skill_id FROM skill_usage WHERE run_id = ?", (str(run["id"]),)).fetchall()
            }
        for skill in skills:
            if skill.lower() in existing:
                continue
            self.database.record_skill_usage(
                skill_id=skill,
                role=str(run["logical_role"] or ""),
                usage_type="DECLARED_WITH_WORK_EVIDENCE",
                task_id=str(run["task_id"]),
                run_id=str(run["id"]),
            )

    def _propose_correction_learning(self, record: ExperienceRecord, competence: str) -> None:
        open_items = [
            item
            for item in self.list_learning_queue(record.agent_id)
            if item.competence == competence and item.status not in {"VERIFIED", "REJECTED"}
        ]
        if open_items or record.agent_id is None:
            return
        self.propose_learning(
            agent_id=record.agent_id,
            competence=competence,
            reason=f"В рабочем результате зафиксировано замечаний: {len(record.errors_found)}.",
            practice_task="Исправить замечание и пройти независимую повторную проверку.",
            evidence={"experience_record_id": record.record_id, **record.evidence},
        )

    @staticmethod
    def _skills(envelope: dict[str, Any]) -> list[str]:
        values = envelope.get("skills_used") or envelope.get("skill_usage") or envelope.get("skills") or []
        result: list[str] = []
        if not isinstance(values, list):
            return result
        for value in values:
            if isinstance(value, dict):
                value = value.get("skill_id") or value.get("title") or value.get("name")
            if isinstance(value, str) and value.strip() and value.strip() not in result:
                result.append(value.strip())
        return result

    @staticmethod
    def _string_values(values: Any) -> list[str]:
        if not isinstance(values, list):
            return []
        result: list[str] = []
        for value in values:
            if isinstance(value, dict):
                value = value.get("path") or value.get("file") or value.get("relative_path")
            if isinstance(value, str) and value.strip():
                result.append(value.strip())
        return result

    @staticmethod
    def _experience(row: Any) -> ExperienceRecord:
        return ExperienceRecord(
            record_id=str(row["id"]),
            agent_id=str(row["agent_id"]) if row["agent_id"] else None,
            employee_name=str(row["employee_name"] or "Удалённый сотрудник"),
            organization_id=str(row["organization_id"]) if row["organization_id"] else None,
            task_id=str(row["task_id"]) if row["task_id"] else None,
            run_id=str(row["run_id"]) if row["run_id"] else None,
            summary=str(row["summary"] or ""),
            skills_used=tuple(map(str, Database.loads(str(row["skills_used"] or "[]"), []))),
            errors_found=tuple(map(str, Database.loads(str(row["errors_found"] or "[]"), []))),
            corrections=tuple(map(str, Database.loads(str(row["corrections"] or "[]"), []))),
            lessons_learned=tuple(map(str, Database.loads(str(row["lessons_learned"] or "[]"), []))),
            evidence=Database.loads(str(row["evidence"] or "{}"), {}),
            outcome=str(row["outcome"] or ""),
            created_at=str(row["created_at"] or ""),
        )

    @staticmethod
    def _queue_item(row: Any) -> LearningQueueItem:
        return LearningQueueItem(
            item_id=str(row["id"]),
            agent_id=str(row["agent_id"]) if row["agent_id"] else None,
            employee_name=str(row["employee_name"] or "Удалённый сотрудник"),
            competence=str(row["competence"]),
            reason=str(row["reason"]),
            source_id=str(row["source_id"]) if row["source_id"] else None,
            status=str(row["status"]),
            practice_task=str(row["practice_task"] or ""),
            evidence=Database.loads(str(row["evidence"] or "{}"), {}),
            created_by=str(row["created_by"] or ""),
            updated_at=str(row["updated_at"] or ""),
        )
