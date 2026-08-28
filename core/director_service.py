from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .database import Database


DIRECTOR_ROLE_IDS = {"PROJECT_MANAGER", "ORGANIZATION_MANAGER", "DIRECTOR"}
REVIEW_ROLE_IDS = {"QA_ENGINEER", "VERIFICATION_ENGINEER", "REVIEWER"}
OWNER_APPROVAL_KEYWORDS = {
    "delete", "remove", "удал", "видал",
    "install", "установ", "встанов",
    "purchase", "buy", "купить", "купити", "оплат",
    "permission", "доступ", "прав",
}
FINAL_PLAN_STATUSES = {"COMPLETED", "BLOCKED", "CANCELLED"}
ACTIONABLE_ASSIGNMENT_STATUSES = {"ASSIGNED", "REWORK_REQUIRED", "EVIDENCE_REQUIRED"}


@dataclass(frozen=True)
class PlannedAssignment:
    assignment_id: str
    task_id: str
    agent_id: str | None
    employee_name: str
    role_id: str
    position: str
    sequence_no: int
    review_required: bool
    status: str
    assignment_type: str
    responsibility: str
    attempt_no: int
    result_run_id: str | None
    result_summary: str
    review_decision: str
    failure_reason: str


@dataclass(frozen=True)
class ProjectPlan:
    plan_id: str
    organization_id: str
    director_agent_id: str
    director_name: str
    goal: str
    status: str
    missing_roles: tuple[str, ...]
    owner_approval_required: bool
    assignments: tuple[PlannedAssignment, ...]
    summary: str = ""
    owner_message_id: int | None = None
    max_rework_attempts: int = 2


@dataclass(frozen=True)
class DirectorAction:
    plan_id: str
    assignment_id: str
    task_id: str
    agent_id: str
    agent_key: str
    assignment_type: str
    instruction: str
    acceptance_criteria: tuple[str, ...]
    attempt_no: int


class DirectorService:
    """Persistent project delegation and evidence-based review workflow."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def create_plan(
        self,
        organization_id: str,
        goal: str,
        *,
        owner_message_id: int | None = None,
        max_rework_attempts: int = 2,
    ) -> ProjectPlan:
        goal = " ".join(goal.strip().split())
        if not goal:
            raise ValueError("goal_required")
        director = self._director_member(organization_id)
        if director is None or not director["agent_id"]:
            raise ValueError("director_not_assigned")
        members = self._active_members(organization_id)
        specialists = [row for row in members if str(row["agent_id"] or "") != str(director["agent_id"])]
        reviewer = next((row for row in specialists if str(row["role_id"] or "") in REVIEW_ROLE_IDS), None)
        creators = [row for row in specialists if row is not reviewer and str(row["role_id"] or "") != "LEARNING_COORDINATOR"]
        missing_roles: list[str] = []
        if not creators:
            missing_roles.append("SPECIALIST")
        if reviewer is None:
            missing_roles.append("REVIEWER")
        owner_approval_required = any(token in goal.casefold() for token in OWNER_APPROVAL_KEYWORDS)
        project_id = f"project-{organization_id}"
        self.database.ensure_project(project_id, "Team2050 Project", organization_id)
        status = "AWAITING_OWNER_APPROVAL" if owner_approval_required else "READY"
        if missing_roles:
            status = "NEEDS_STAFFING"
        plan_id = self.database.create_project_plan(
            {
                "organization_id": organization_id,
                "project_id": project_id,
                "director_agent_id": str(director["agent_id"]),
                "goal": goal,
                "status": status,
                "missing_roles": missing_roles,
                "owner_approval_required": owner_approval_required,
                "owner_message_id": owner_message_id,
                "max_rework_attempts": max(1, int(max_rework_attempts)),
            }
        )
        execution_ids: list[str] = []
        for sequence, member in enumerate(creators, start=1):
            responsibility = str(member["position"] or member["role_id"] or "специалист")
            execution_ids.append(
                self._create_assignment(
                    plan_id,
                    member,
                    f"{responsibility}: профильная часть цели — {goal}",
                    sequence,
                    assignment_type="EXECUTION",
                    responsibility="RESPONSIBLE",
                    review_required=True,
                )
            )
        if reviewer is not None and execution_ids:
            self._create_assignment(
                plan_id,
                reviewer,
                f"Проверить результаты по цели: {goal}",
                len(execution_ids) + 1,
                assignment_type="REVIEW",
                responsibility="REVIEWER",
                review_required=False,
            )
        self._event(plan_id, "PLAN_CREATED", actor=str(director["agent_id"]), detail={"status": status})
        return self.get_plan(plan_id)

    def get_plan(self, plan_id: str) -> ProjectPlan:
        row = self.database.get_project_plan(plan_id)
        if row is None:
            raise ValueError("unknown_plan")
        profile = self.database.get_agent_profile(str(row["director_agent_id"]))
        assignments = tuple(self._assignment(item) for item in self.database.list_work_assignments(plan_id))
        return ProjectPlan(
            plan_id=str(row["id"]),
            organization_id=str(row["organization_id"]),
            director_agent_id=str(row["director_agent_id"]),
            director_name=str(profile["display_name"]) if profile is not None else "Удалённый сотрудник",
            goal=str(row["goal"]),
            status=str(row["status"]),
            missing_roles=tuple(map(str, Database.loads(str(row["missing_roles"] or "[]"), []))),
            owner_approval_required=bool(row["owner_approval_required"]),
            assignments=assignments,
            summary=str(row["summary"] or ""),
            owner_message_id=int(row["owner_message_id"]) if row["owner_message_id"] is not None else None,
            max_rework_attempts=int(row["max_rework_attempts"]),
        )

    def list_plans(self, organization_id: str | None = None) -> list[ProjectPlan]:
        return [self.get_plan(str(row["id"])) for row in self.database.list_project_plans(organization_id)]

    def approve_owner_action(self, plan_id: str) -> ProjectPlan:
        plan = self.get_plan(plan_id)
        if plan.status != "AWAITING_OWNER_APPROVAL":
            raise ValueError("owner_approval_not_expected")
        self.database.update_project_plan(plan_id, {"status": "READY", "owner_approval_required": 0})
        self._event(plan_id, "OWNER_APPROVED")
        return self.get_plan(plan_id)

    def cancel_plan(self, plan_id: str, reason: str = "stopped_by_owner") -> ProjectPlan:
        plan = self.get_plan(plan_id)
        if plan.status not in FINAL_PLAN_STATUSES:
            self.database.update_project_plan(plan_id, {"status": "CANCELLED", "summary": reason})
            self._event(plan_id, "PLAN_CANCELLED", detail={"reason": reason})
        return self.get_plan(plan_id)

    def replan_plan(self, plan_id: str) -> ProjectPlan:
        plan = self.get_plan(plan_id)
        if plan.status == "COMPLETED":
            raise ValueError("completed_plan_cannot_be_replanned")
        rows = self.database.list_work_assignments(plan_id)
        if not rows:
            raise ValueError("plan_has_no_assignments")
        for row in rows:
            if str(row["status"]) in {"FAILED", "BLOCKED", "REWORK_REQUIRED", "EVIDENCE_REQUIRED"}:
                self.database.update_work_assignment(str(row["id"]), {"status": "ASSIGNED", "failure_reason": ""})
        self.database.update_project_plan(plan_id, {"status": "READY", "summary": "Replanned by Supervisor"})
        self._event(plan_id, "PLAN_REPLANNED")
        return self.get_plan(plan_id)

    def next_action(self, plan_id: str) -> DirectorAction | None:
        plan = self.get_plan(plan_id)
        if plan.status in FINAL_PLAN_STATUSES or plan.status in {"NEEDS_STAFFING", "AWAITING_OWNER_APPROVAL"}:
            return None
        rows = self.database.list_work_assignments(plan_id)
        executions = [row for row in rows if str(row["assignment_type"]) == "EXECUTION"]
        reviews = [row for row in rows if str(row["assignment_type"]) == "REVIEW"]
        for row in executions:
            if str(row["status"]) in ACTIONABLE_ASSIGNMENT_STATUSES:
                return self._action(plan, row)
            if str(row["status"]) in {"RUNNING", "FAILED"}:
                return None
        if executions and all(str(row["status"]) in {"AWAITING_REVIEW", "COMPLETED"} for row in executions):
            for row in reviews:
                if str(row["status"]) in ACTIONABLE_ASSIGNMENT_STATUSES:
                    return self._action(plan, row)
                if str(row["status"]) == "RUNNING":
                    return None
        if rows and all(str(row["status"]) == "COMPLETED" for row in rows):
            self._complete_plan(plan_id)
        return None

    def start_assignment(self, assignment_id: str, run_id: str) -> PlannedAssignment:
        row = self._required_assignment(assignment_id)
        if str(row["status"]) not in ACTIONABLE_ASSIGNMENT_STATUSES:
            raise ValueError("assignment_not_actionable")
        attempt = int(row["attempt_no"] or 0) + 1
        self.database.update_work_assignment(
            assignment_id,
            {
                "status": "RUNNING",
                "attempt_no": attempt,
                "result_run_id": run_id,
                "started_at": self._now(),
                "failure_reason": "",
            },
        )
        self.database.update_project_plan(str(row["plan_id"]), {"status": "IN_PROGRESS"})
        self._event(str(row["plan_id"]), "ASSIGNMENT_STARTED", assignment_id, str(row["agent_id"]), {"run_id": run_id, "attempt": attempt})
        return self._assignment(self._required_assignment(assignment_id))

    def finish_assignment(
        self,
        assignment_id: str,
        *,
        ok: bool,
        run_id: str,
        message_id: int | None,
        summary: str,
        evidence: dict[str, Any] | None = None,
        review_decision: str = "",
        findings: list[dict[str, Any]] | None = None,
        error: str = "",
    ) -> ProjectPlan:
        row = self._required_assignment(assignment_id)
        plan_id = str(row["plan_id"])
        if str(row["status"]) != "RUNNING":
            raise ValueError("assignment_not_running")
        if str(row["result_run_id"] or "") != run_id:
            raise ValueError("assignment_run_mismatch")
        if not ok:
            return self._retry_or_block(row, error or "provider_run_failed")
        payload = dict(evidence or {})
        payload.setdefault("run_id", run_id)
        if message_id is not None:
            payload.setdefault("message_id", message_id)
        if str(row["assignment_type"]) == "REVIEW":
            return self._finish_review(row, message_id, summary, payload, review_decision, findings or [])
        if not self._has_verifiable_evidence(payload):
            return self._retry_or_block(row, "verifiable_evidence_required", status="EVIDENCE_REQUIRED")
        next_status = "AWAITING_REVIEW" if bool(row["review_required"]) else "COMPLETED"
        self.database.update_work_assignment(
            assignment_id,
            {
                "status": next_status,
                "result_message_id": message_id,
                "result_summary": summary.strip(),
                "evidence": payload,
                "completed_at": self._now(),
            },
        )
        self._event(plan_id, "EXECUTION_RECORDED", assignment_id, str(row["agent_id"]), {"status": next_status, "evidence": payload})
        if next_status == "COMPLETED" and self.next_action(plan_id) is None:
            self._complete_plan(plan_id)
        return self.get_plan(plan_id)

    def _finish_review(
        self,
        row: Any,
        message_id: int | None,
        summary: str,
        evidence: dict[str, Any],
        review_decision: str,
        findings: list[dict[str, Any]],
    ) -> ProjectPlan:
        plan_id = str(row["plan_id"])
        decision = self._normalized_review_decision(review_decision, findings)
        if decision == "":
            return self._retry_or_block(row, "structured_review_decision_required")
        self.database.update_work_assignment(
            str(row["id"]),
            {
                "status": "COMPLETED",
                "result_message_id": message_id,
                "result_summary": summary.strip(),
                "evidence": {**evidence, "findings": findings},
                "review_decision": decision,
                "completed_at": self._now(),
            },
        )
        executions = [
            item for item in self.database.list_work_assignments(plan_id)
            if str(item["assignment_type"]) == "EXECUTION" and str(item["status"]) == "AWAITING_REVIEW"
        ]
        if decision == "APPROVED":
            for item in executions:
                self.database.update_work_assignment(str(item["id"]), {"status": "COMPLETED"})
            self._event(plan_id, "REVIEW_APPROVED", str(row["id"]), str(row["agent_id"]), {"findings": findings})
            self._complete_plan(plan_id, summary)
            return self.get_plan(plan_id)
        for item in executions:
            self.database.update_work_assignment(str(item["id"]), {"status": "REWORK_REQUIRED"})
        self.database.update_work_assignment(
            str(row["id"]),
            {"status": "ASSIGNED", "review_decision": "", "completed_at": None},
        )
        self._event(plan_id, "REWORK_REQUESTED", str(row["id"]), str(row["agent_id"]), {"findings": findings})
        return self.get_plan(plan_id)

    def _retry_or_block(self, row: Any, reason: str, *, status: str = "ASSIGNED") -> ProjectPlan:
        plan = self.get_plan(str(row["plan_id"]))
        assignment_id = str(row["id"])
        attempt = int(row["attempt_no"] or 0)
        if attempt >= plan.max_rework_attempts:
            self.database.update_work_assignment(assignment_id, {"status": "FAILED", "failure_reason": reason})
            self.database.update_project_plan(plan.plan_id, {"status": "BLOCKED", "summary": reason})
            self._event(plan.plan_id, "PLAN_BLOCKED", assignment_id, str(row["agent_id"] or ""), {"reason": reason, "attempt": attempt})
        else:
            self.database.update_work_assignment(assignment_id, {"status": status, "failure_reason": reason})
            self.database.update_project_plan(plan.plan_id, {"status": "IN_PROGRESS"})
            self._event(plan.plan_id, "ASSIGNMENT_RETRY_REQUIRED", assignment_id, str(row["agent_id"] or ""), {"reason": reason, "attempt": attempt})
        return self.get_plan(plan.plan_id)

    def _complete_plan(self, plan_id: str, summary: str = "") -> None:
        plan = self.get_plan(plan_id)
        if plan.status == "COMPLETED":
            return
        final_summary = summary.strip() or self._build_summary(plan)
        self.database.update_project_plan(
            plan_id,
            {"status": "COMPLETED", "summary": final_summary, "completed_at": self._now()},
        )
        self._event(plan_id, "PLAN_COMPLETED", actor=plan.director_agent_id, detail={"summary": final_summary})

    def _create_assignment(
        self,
        plan_id: str,
        member: Any,
        title: str,
        sequence: int,
        *,
        assignment_type: str,
        responsibility: str,
        review_required: bool,
    ) -> str:
        plan_row = self.database.get_project_plan(plan_id)
        if plan_row is None:
            raise ValueError("unknown_plan")
        project_id = str(plan_row["project_id"])
        organization_id = str(plan_row["organization_id"])
        self.database.ensure_project(project_id, "Organization project", organization_id)
        task_id = self.database.create_task(project_id, title[:160], None, "1.0", organization_id)
        return self.database.create_work_assignment(
            {
                "plan_id": plan_id,
                "task_id": task_id,
                "agent_id": member["agent_id"],
                "role_id": member["role_id"],
                "position": member["position"],
                "sequence_no": sequence,
                "review_required": review_required,
                "assignment_type": assignment_type,
                "responsibility": responsibility,
                "acceptance_criteria": [
                    "Результат сохранён или зарегистрирован",
                    "Есть проверяемые доказательства выполнения",
                    "Результат проверен независимым сотрудником",
                ],
            }
        )

    def _action(self, plan: ProjectPlan, row: Any) -> DirectorAction:
        criteria = tuple(map(str, Database.loads(str(row["acceptance_criteria"] or "[]"), [])))
        assignment_type = str(row["assignment_type"])
        prefix = "Независимо проверь результаты исполнителей" if assignment_type == "REVIEW" else "Выполни назначенную часть цели"
        task = self.database.get_task(str(row["task_id"]))
        task_title = str(task["title"]) if task is not None else plan.goal
        instruction = (
            f"{prefix}. Твоё назначение: {task_title}. Общая цель: {plan.goal}. "
            "Работай инструментами, сохраняй результат и верни структурированные доказательства. "
            "Для ревью укажи action=APPROVE либо action=REWORK и конкретные findings."
        )
        agent_id = str(row["agent_id"] or "")
        if not agent_id:
            raise ValueError("assignment_agent_missing")
        return DirectorAction(
            plan_id=plan.plan_id,
            assignment_id=str(row["id"]),
            task_id=str(row["task_id"]),
            agent_id=agent_id,
            agent_key=agent_id.removeprefix("agent-"),
            assignment_type=assignment_type,
            instruction=instruction,
            acceptance_criteria=criteria,
            attempt_no=int(row["attempt_no"] or 0) + 1,
        )

    def _required_assignment(self, assignment_id: str):
        row = self.database.get_work_assignment(assignment_id)
        if row is None:
            raise ValueError("unknown_assignment")
        return row

    def _director_member(self, organization_id: str):
        return next((row for row in self._active_members(organization_id) if str(row["role_id"] or "") in DIRECTOR_ROLE_IDS), None)

    def _active_members(self, organization_id: str):
        return [
            row for row in self.database.list_organization_members(organization_id)
            if str(row["status"] or "ACTIVE").upper() == "ACTIVE"
            and row["agent_id"]
            and self.database.get_agent_profile(str(row["agent_id"])) is not None
        ]

    def _assignment(self, row: Any) -> PlannedAssignment:
        profile = self.database.get_agent_profile(str(row["agent_id"])) if row["agent_id"] else None
        return PlannedAssignment(
            assignment_id=str(row["id"]),
            task_id=str(row["task_id"]),
            agent_id=str(row["agent_id"]) if row["agent_id"] else None,
            employee_name=str(profile["display_name"]) if profile is not None else "Не назначен",
            role_id=str(row["role_id"] or ""),
            position=str(row["position"] or ""),
            sequence_no=int(row["sequence_no"]),
            review_required=bool(row["review_required"]),
            status=str(row["status"]),
            assignment_type=str(row["assignment_type"]),
            responsibility=str(row["responsibility"]),
            attempt_no=int(row["attempt_no"] or 0),
            result_run_id=str(row["result_run_id"]) if row["result_run_id"] else None,
            result_summary=str(row["result_summary"] or ""),
            review_decision=str(row["review_decision"] or ""),
            failure_reason=str(row["failure_reason"] or ""),
        )

    def _event(
        self,
        plan_id: str,
        event_type: str,
        assignment_id: str | None = None,
        actor: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.database.record_director_workflow_event(
            plan_id,
            event_type,
            assignment_id=assignment_id,
            actor_agent_id=actor,
            detail=detail,
        )

    @staticmethod
    def _normalized_review_decision(decision: str, findings: list[dict[str, Any]]) -> str:
        blocking = any(
            bool(item.get("blocking"))
            or str(item.get("severity", "")).upper() in {"BLOCKER", "CRITICAL", "HIGH"}
            for item in findings
            if isinstance(item, dict)
        )
        normalized = decision.strip().upper().replace(" ", "_")
        if blocking or normalized in {"REWORK", "REQUEST_CHANGES", "REJECT", "REJECTED"}:
            return "REWORK"
        if normalized in {"APPROVE", "APPROVED", "PASS", "PASSED", "ACCEPT", "ACCEPTED", "COMPLETE"}:
            return "APPROVED"
        return ""

    @staticmethod
    def _has_verifiable_evidence(evidence: dict[str, Any]) -> bool:
        keys = {
            "artifacts", "artifact_ids", "files_created", "files_modified", "checks",
            "findings", "tool_evidence", "commands", "sources",
        }
        return any(bool(evidence.get(key)) for key in keys)

    @staticmethod
    def _build_summary(plan: ProjectPlan) -> str:
        completed = [item for item in plan.assignments if item.assignment_type == "EXECUTION"]
        return f"Цель выполнена и прошла независимую проверку. Исполнено назначений: {len(completed)}."

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")
