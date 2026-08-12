from __future__ import annotations

from dataclasses import dataclass
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


class DirectorService:
    """Persists delegation plans while keeping specialist work with specialists."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def create_plan(self, organization_id: str, goal: str) -> ProjectPlan:
        goal = " ".join(goal.strip().split())
        if not goal:
            raise ValueError("goal_required")
        director = self._director_member(organization_id)
        if director is None or not director["agent_id"]:
            raise ValueError("director_not_assigned")
        members = self._active_members(organization_id)
        specialists = [row for row in members if str(row["agent_id"] or "") != str(director["agent_id"])]
        missing_roles: list[str] = []
        if not specialists:
            missing_roles.append("SPECIALIST")
        reviewer = next((row for row in specialists if str(row["role_id"] or "") in REVIEW_ROLE_IDS), None)
        creators = [row for row in specialists if row is not reviewer]
        if not creators and reviewer is not None:
            creators = [reviewer]
        if reviewer is None:
            missing_roles.append("REVIEWER")
        owner_approval_required = any(token in goal.casefold() for token in OWNER_APPROVAL_KEYWORDS)
        self.database.ensure_project("project-default", "Team2050 Project")
        status = "AWAITING_OWNER_APPROVAL" if owner_approval_required else "READY"
        if missing_roles:
            status = "NEEDS_STAFFING"
        plan_id = self.database.create_project_plan(
            {
                "organization_id": organization_id,
                "project_id": "project-default",
                "director_agent_id": str(director["agent_id"]),
                "goal": goal,
                "status": status,
                "missing_roles": missing_roles,
                "owner_approval_required": owner_approval_required,
            }
        )
        sequence = 1
        for member in creators:
            self._create_assignment(plan_id, member, goal, sequence, review_required=reviewer is not None)
            sequence += 1
        if reviewer is not None and reviewer not in creators:
            self._create_assignment(plan_id, reviewer, f"Проверить результат: {goal}", sequence, review_required=False)
        return self.get_plan(plan_id)

    def get_plan(self, plan_id: str) -> ProjectPlan:
        row = next((item for item in self.database.list_project_plans() if str(item["id"]) == plan_id), None)
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
        )

    def list_plans(self, organization_id: str | None = None) -> list[ProjectPlan]:
        return [self.get_plan(str(row["id"])) for row in self.database.list_project_plans(organization_id)]

    def _create_assignment(self, plan_id: str, member: Any, title: str, sequence: int, *, review_required: bool) -> None:
        task_id = self.database.create_task("project-default", title[:160], None, "1.0")
        self.database.create_work_assignment(
            {
                "plan_id": plan_id,
                "task_id": task_id,
                "agent_id": member["agent_id"],
                "role_id": member["role_id"],
                "position": member["position"],
                "sequence_no": sequence,
                "review_required": review_required,
                "acceptance_criteria": ["Сохранён результат", "Есть проверяемые доказательства"],
            }
        )

    def _director_member(self, organization_id: str):
        members = self._active_members(organization_id)
        return next((row for row in members if str(row["role_id"] or "") in DIRECTOR_ROLE_IDS), None)

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
        )
