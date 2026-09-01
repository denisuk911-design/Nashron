from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .database import Database
from .director_service import DirectorAction, DirectorService, ProjectPlan


class SupervisorApplicationService:
    """Application boundary for Supervisor Guide, Operator and Director modes."""

    def __init__(self, database: Database, director_service: DirectorService | None = None) -> None:
        self.database = database
        self._director = director_service or DirectorService(database)

    def guide(self, organization_id: str, goal: str = "") -> dict[str, Any]:
        """Return an owner-safe explanation of what the Supervisor can do next."""
        plans = self._director.list_plans(organization_id)
        active = next((plan for plan in reversed(plans) if plan.status not in {"COMPLETED", "CANCELLED"}), None)
        if active is None:
            return {
                "mode": "GUIDE",
                "organization_id": organization_id,
                "state": "READY_FOR_GOAL" if goal.strip() else "WAITING_FOR_GOAL",
                "message": "Укажите цель, и Supervisor сам составит план и выберет исполнителей.",
                "plan": None,
            }
        return {
            "mode": "GUIDE",
            "organization_id": organization_id,
            "state": active.status,
            "message": self._guide_message(active),
            "plan": self._public_plan(active),
        }

    def operator(self, plan_id: str) -> DirectorAction | None:
        """Resolve the next executable handoff without executing tools implicitly."""
        return self._director.next_action(plan_id)

    def director(self, organization_id: str, goal: str, *, owner_message_id: int | None = None, project_id: str | None = None) -> ProjectPlan:
        """Create a persistent plan through the Director application service."""
        return self._director.create_plan(organization_id, goal, owner_message_id=owner_message_id, project_id=project_id)

    def approve(self, plan_id: str) -> ProjectPlan:
        return self._director.approve_owner_action(plan_id)

    def cancel(self, plan_id: str, reason: str = "stopped_by_owner") -> ProjectPlan:
        return self._director.cancel_plan(plan_id, reason)

    def replan(self, plan_id: str) -> ProjectPlan:
        """Resume a blocked/rework plan through the Director application boundary."""
        return self._director.replan_plan(plan_id)

    def start_assignment(self, assignment_id: str, run_id: str):
        return self._director.start_assignment(assignment_id, run_id)

    def finish_assignment(self, assignment_id: str, **values: Any) -> ProjectPlan:
        return self._director.finish_assignment(assignment_id, **values)

    def get_plan(self, plan_id: str) -> ProjectPlan:
        return self._director.get_plan(plan_id)

    def list_plans(self, organization_id: str | None = None) -> list[ProjectPlan]:
        return self._director.list_plans(organization_id)

    @staticmethod
    def _guide_message(plan: ProjectPlan) -> str:
        if plan.status == "AWAITING_OWNER_APPROVAL":
            return "План подготовлен и ждёт разрешения владельца на действие с повышенным риском."
        if plan.status == "NEEDS_STAFFING":
            return "Плану не хватает ролей: " + ", ".join(plan.missing_roles)
        if plan.status == "IN_PROGRESS":
            return "Supervisor ведёт план; следующий шаг передан назначенному сотруднику."
        return f"План имеет состояние «{plan.status}». Supervisor продолжит после доступности следующего шага."

    @staticmethod
    def _public_plan(plan: ProjectPlan) -> dict[str, Any]:
        data = asdict(plan)
        data.pop("director_agent_id", None)
        data.pop("owner_message_id", None)
        for assignment in data.get("assignments", []):
            assignment.pop("agent_id", None)
            assignment.pop("result_run_id", None)
        return data
