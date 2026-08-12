from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .database import Database
from .learning_evidence_service import ExperienceRecord, LearningEvidenceService, LearningQueueItem
from .skill_package_service import SkillPackageService


REVIEW_ROLES = {"QA_ENGINEER", "VERIFICATION_ENGINEER", "REVIEWER"}


@dataclass(frozen=True)
class LearningRetrospective:
    plan_id: str
    candidates_created: int
    queue_items_created: int
    coordinator_agent_id: str | None
    warnings: tuple[str, ...]


class LearningManagerService:
    """Evidence-gated professional learning, practice and requalification."""

    def __init__(
        self,
        database: Database,
        evidence_service: LearningEvidenceService,
        skill_packages: SkillPackageService,
    ) -> None:
        self.database = database
        self.evidence_service = evidence_service
        self.skill_packages = skill_packages

    def retrospective_for_plan(self, plan_id: str) -> LearningRetrospective:
        plan = self.database.get_project_plan(plan_id)
        if plan is None:
            raise ValueError("unknown_plan")
        organization_id = str(plan["organization_id"])
        coordinator = self._coordinator(organization_id)
        task_ids = {str(row["task_id"]) for row in self.database.list_work_assignments(plan_id)}
        experiences = [item for item in self.evidence_service.list_experience() if item.task_id in task_ids]
        candidates = 0
        queue_items = 0
        for experience in experiences:
            for competence in experience.skills_used:
                if self._ensure_skill_candidate(experience, competence):
                    candidates += 1
        for row in self.database.list_work_assignments(plan_id):
            reason = str(row["failure_reason"] or "").strip()
            if not reason and str(row["status"]) not in {"FAILED", "REWORK_REQUIRED"}:
                continue
            agent_id = str(row["agent_id"] or "")
            if not agent_id or self._has_open_queue(agent_id, str(row["role_id"] or "Professional practice")):
                continue
            self.evidence_service.propose_learning(
                agent_id=agent_id,
                competence=str(row["role_id"] or "Professional practice"),
                reason=reason or "Результат был возвращён на доработку независимой проверкой.",
                practice_task="Повторить проблемную операцию на проверочной задаче и получить независимое ревью.",
                evidence={"plan_id": plan_id, "assignment_id": str(row["id"]), "status": str(row["status"])},
                created_by=coordinator or "SYSTEM_LEARNING_MANAGER",
            )
            queue_items += 1
        warnings = () if coordinator else ("В организации не назначен координатор обучения; предложения созданы системой и требуют контроля владельца.",)
        self.database.audit_event(
            "learning_retrospective_completed",
            None,
            {
                "plan_id": plan_id,
                "candidates_created": candidates,
                "queue_items_created": queue_items,
                "coordinator_agent_id": coordinator,
                "warnings": list(warnings),
            },
        )
        return LearningRetrospective(plan_id, candidates, queue_items, coordinator, warnings)

    def prepare_learning_item(self, item_id: str) -> LearningQueueItem:
        row = self._queue_row(item_id)
        if str(row["status"]) not in {"PROPOSED", "APPROVED", "PRACTICE_REQUIRED"}:
            raise ValueError("learning_item_not_plannable")
        agent_id = str(row["agent_id"] or "")
        if not agent_id:
            raise ValueError("learning_employee_missing")
        skill_id = str(row["skill_id"] or "") or self._skill_id_for_competence(
            str(row["competence"]),
            str(row["reason"]),
            str(row["created_by"] or "SYSTEM_LEARNING_MANAGER"),
        )
        self.skill_packages.assign_to_employee(
            agent_id,
            skill_id,
            state="STUDYING",
            actor=str(row["created_by"] or "SYSTEM_LEARNING_MANAGER"),
            reason=f"learning_queue:{item_id}",
        )
        self.database.update_learning_queue_item(
            item_id,
            {
                "status": "PRACTICE_REQUIRED",
                "skill_id": skill_id,
                "practice_task": str(row["practice_task"] or "Выполнить проверочную задачу с сохранением результата и evidence."),
            },
        )
        return self._queue_item(item_id)

    def record_practice(self, item_id: str, run_id: str) -> LearningQueueItem:
        row = self._queue_row(item_id)
        if str(row["status"]) not in {"PRACTICE_REQUIRED", "IN_PROGRESS"}:
            raise ValueError("practice_not_expected")
        run = self.database.get_agent_run(run_id)
        if run is None or not int(run["ok"] or 0) or int(run["cancelled"] or 0):
            raise ValueError("successful_practice_run_required")
        if str(run["agent_id"]) != str(row["agent_id"]):
            raise ValueError("practice_employee_mismatch")
        experience = next((item for item in self.evidence_service.list_experience(str(row["agent_id"])) if item.run_id == run_id), None)
        if experience is None or not any(bool(value) for value in experience.evidence.values()):
            raise ValueError("practice_evidence_required")
        skill_id = str(row["skill_id"] or "")
        if not skill_id:
            raise ValueError("learning_skill_not_prepared")
        self.skill_packages.update_status(skill_id, "PRACTICED", actor="SYSTEM_LEARNING_MANAGER", reason=f"practice_run:{run_id}")
        self.skill_packages.assign_to_employee(
            str(row["agent_id"]), skill_id, state="DEMONSTRATED", actor="SYSTEM_LEARNING_MANAGER", reason=f"practice_run:{run_id}"
        )
        evidence = self._merge_evidence(row, {"practice_run_id": run_id, "experience_record_id": experience.record_id})
        self.database.update_learning_queue_item(
            item_id,
            {"status": "READY_FOR_REVIEW", "practice_run_id": run_id, "evidence": evidence},
        )
        return self._queue_item(item_id)

    def record_qualification(self, item_id: str, review_run_id: str, *, approved: bool) -> LearningQueueItem:
        row = self._queue_row(item_id)
        if str(row["status"]) != "READY_FOR_REVIEW":
            raise ValueError("qualification_not_expected")
        run = self.database.get_agent_run(review_run_id)
        if run is None or not int(run["ok"] or 0) or int(run["cancelled"] or 0):
            raise ValueError("successful_review_run_required")
        if str(run["agent_id"]) == str(row["agent_id"]):
            raise ValueError("independent_reviewer_required")
        if str(run["logical_role"] or "") not in REVIEW_ROLES:
            raise ValueError("qualified_reviewer_role_required")
        parsed = Database.loads(str(run["parsed_response"] or "{}"), {})
        checks = parsed.get("checks", []) if isinstance(parsed, dict) else []
        findings = parsed.get("findings", []) if isinstance(parsed, dict) else []
        if not checks and not findings:
            raise ValueError("review_evidence_required")
        blocking = any(
            isinstance(item, dict)
            and (bool(item.get("blocking")) or str(item.get("severity", "")).upper() in {"BLOCKER", "CRITICAL", "HIGH"})
            for item in findings
        )
        skill_id = str(row["skill_id"] or "")
        evidence = self._merge_evidence(
            row,
            {"review_run_id": review_run_id, "review_checks": checks, "review_findings": findings, "approved": approved and not blocking},
        )
        if approved and not blocking:
            self.skill_packages.update_status(skill_id, "VERIFIED", actor=str(run["agent_id"]), reason=f"review_run:{review_run_id}")
            self.skill_packages.assign_to_employee(
                str(row["agent_id"]), skill_id, state="QUALIFIED", actor=str(run["agent_id"]), reason=f"review_run:{review_run_id}"
            )
            values = {"status": "VERIFIED", "review_run_id": review_run_id, "evidence": evidence, "completed_at": self._now()}
        else:
            self.skill_packages.assign_to_employee(
                str(row["agent_id"]), skill_id, state="REQUIRES_RETRAINING", actor=str(run["agent_id"]), reason=f"review_run:{review_run_id}"
            )
            values = {"status": "PRACTICE_REQUIRED", "review_run_id": review_run_id, "evidence": evidence}
        self.database.update_learning_queue_item(item_id, values)
        return self._queue_item(item_id)

    def _ensure_skill_candidate(self, experience: ExperienceRecord, competence: str) -> bool:
        existing = next((item for item in self.skill_packages.list_packages() if item.name.casefold() == competence.casefold()), None)
        created = existing is None
        if existing is None:
            skill_id = self.skill_packages.create_package(
                name=competence,
                purpose=f"Проверяемая практика из опыта {experience.record_id}",
                supported_roles=[],
                source_material=[f"experience:{experience.record_id}"],
                instructions="Применять только в пределах подтверждённого рабочего сценария.",
                validation_checklist=["Есть сохранённый результат", "Есть независимая проверка"],
                qualification_tasks=["Повторить операцию на отдельной проверочной задаче"],
                status="PRACTICED",
                actor="SYSTEM_LEARNING_MANAGER",
            )
        else:
            skill_id = existing.skill_id
            if existing.status == "DRAFT":
                self.skill_packages.update_status(skill_id, "PRACTICED", actor="SYSTEM_LEARNING_MANAGER", reason=experience.record_id)
        if experience.agent_id:
            self.skill_packages.assign_to_employee(
                experience.agent_id,
                skill_id,
                state="PRACTICED",
                actor="SYSTEM_LEARNING_MANAGER",
                reason=f"experience:{experience.record_id}",
            )
        return created

    def _skill_id_for_competence(self, competence: str, reason: str, actor: str) -> str:
        existing = next((item for item in self.skill_packages.list_packages() if item.name.casefold() == competence.casefold()), None)
        if existing is not None:
            return existing.skill_id
        return self.skill_packages.create_package(
            name=competence,
            purpose=reason,
            validation_checklist=["Практика подтверждена evidence", "Независимый reviewer принял результат"],
            qualification_tasks=["Выполнить исправленную операцию повторно"],
            status="DRAFT",
            actor=actor,
        )

    def _coordinator(self, organization_id: str) -> str | None:
        for row in self.database.list_organization_members(organization_id):
            if str(row["status"] or "ACTIVE").upper() == "ACTIVE" and str(row["role_id"] or "") == "LEARNING_COORDINATOR" and row["agent_id"]:
                return str(row["agent_id"])
        return None

    def _has_open_queue(self, agent_id: str, competence: str) -> bool:
        return any(
            item.competence == competence and item.status not in {"VERIFIED", "REJECTED"}
            for item in self.evidence_service.list_learning_queue(agent_id)
        )

    def _queue_row(self, item_id: str):
        row = self.database.get_learning_queue_item(item_id)
        if row is None:
            raise ValueError("unknown_learning_item")
        return row

    def _queue_item(self, item_id: str) -> LearningQueueItem:
        row = self._queue_row(item_id)
        return next(item for item in self.evidence_service.list_learning_queue() if item.item_id == str(row["id"]))

    @staticmethod
    def _merge_evidence(row: Any, values: dict[str, Any]) -> dict[str, Any]:
        existing = Database.loads(str(row["evidence"] or "{}"), {})
        if not isinstance(existing, dict):
            existing = {}
        return {**existing, **values}

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")
