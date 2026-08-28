from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .database import Database


SKILL_PACKAGE_STATUSES = (
    "DRAFT", "PRACTICED", "READY_FOR_REVIEW", "REVIEWED", "VERIFIED", "MATURE",
    "ACTIVE", "SUSPENDED", "DEPRECATED", "REJECTED",
)
SKILL_LIFECYCLE_STATES = ("CANDIDATE", "QUALIFIED", "ACTIVE")
EMPLOYEE_SKILL_STATES = (
    "NOT_ASSIGNED",
    "ASSIGNED",
    "STUDYING",
    "PRACTICED",
    "DEMONSTRATED",
    "REVIEWED",
    "QUALIFIED",
    "REQUIRES_RETRAINING",
    "EXPIRED",
)


@dataclass(frozen=True)
class SkillPackage:
    skill_id: str
    name: str
    purpose: str
    supported_roles: list[str]
    prerequisites: str
    source_material: list[str]
    instructions: str
    tools: list[str]
    expected_inputs: str
    expected_outputs: str
    prohibited_actions: str
    validation_checklist: list[str]
    examples: list[str]
    negative_examples: list[str]
    qualification_tasks: list[str]
    test_cases: list[str]
    failure_patterns: list[str]
    version: str
    status: str
    lifecycle_state: str
    created_by: str
    updated_at: str


@dataclass(frozen=True)
class EmployeeSkillAssignment:
    assignment_id: str
    agent_id: str
    skill_id: str
    skill_name: str
    skill_status: str
    state: str
    purpose: str
    version: str
    updated_at: str


@dataclass(frozen=True)
class SkillPackageEvent:
    event_id: str
    skill_id: str
    event_type: str
    actor: str
    detail: str
    created_at: str


class SkillPackageService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create_package(
        self,
        *,
        name: str,
        purpose: str = "",
        supported_roles: list[str] | None = None,
        prerequisites: str = "",
        source_material: list[str] | None = None,
        instructions: str = "",
        tools: list[str] | None = None,
        expected_inputs: str = "",
        expected_outputs: str = "",
        prohibited_actions: str = "",
        validation_checklist: list[str] | None = None,
        examples: list[str] | None = None,
        negative_examples: list[str] | None = None,
        qualification_tasks: list[str] | None = None,
        test_cases: list[str] | None = None,
        failure_patterns: list[str] | None = None,
        version: str = "0.1.0",
        status: str = "DRAFT",
        actor: str = "owner",
        organization_id: str | None = None,
    ) -> str:
        name = " ".join(name.strip().split())
        if not name:
            raise ValueError("Название навыка обязательно.")
        self._require_status(status)
        return self.database.create_skill_package(
            name=name,
            purpose=purpose.strip(),
            supported_roles=supported_roles or [],
            prerequisites=prerequisites.strip(),
            source_material=source_material or [],
            instructions=instructions.strip(),
            tools=tools or [],
            expected_inputs=expected_inputs.strip(),
            expected_outputs=expected_outputs.strip(),
            prohibited_actions=prohibited_actions.strip(),
            validation_checklist=validation_checklist or [],
            examples=examples or [],
            negative_examples=negative_examples or [],
            qualification_tasks=qualification_tasks or [],
            test_cases=test_cases or [],
            failure_patterns=failure_patterns or [],
            version=version.strip() or "0.1.0",
            status=status,
            actor=actor,
            organization_id=organization_id,
        )

    def list_packages(self, organization_id: str | None = None) -> list[SkillPackage]:
        return [self._package_from_row(row) for row in self.database.list_skill_packages(organization_id)]

    def update_status(self, skill_id: str, status: str, *, actor: str = "owner", reason: str = "", organization_id: str | None = None) -> None:
        self._require_status(status)
        if status == "ACTIVE":
            if not organization_id or not self.database.has_qualified_skill_assignment(skill_id, organization_id):
                raise ValueError("skill activation requires an independently qualified employee")
        if status in {"VERIFIED", "MATURE", "ACTIVE"} and "evidence:" not in reason.lower() and actor != "owner":
            raise ValueError("Переход навыка требует evidence.")
        self.database.update_skill_package_status(skill_id, status, actor, reason.strip(), organization_id)

    def uninstall_package(self, skill_id: str, organization_id: str, *, actor: str = "owner") -> bool:
        return self.database.delete_skill_package(skill_id, organization_id, actor)

    def set_version(self, skill_id: str, version: str, *, actor: str = "owner", organization_id: str | None = None) -> None:
        self.database.update_skill_package_version(skill_id, version, actor, organization_id)

    def assign_to_employee(self, agent_id: str, skill_id: str, *, state: str = "ASSIGNED", actor: str = "owner", reason: str = "") -> str:
        self._require_employee_state(state)
        if state == "QUALIFIED" and "review_run:" not in reason:
            raise ValueError("employee qualification requires independent review evidence")
        if not agent_id.strip():
            raise ValueError("Сотрудник обязателен.")
        return self.database.assign_skill_to_agent(
            agent_id=agent_id.strip(),
            skill_id=skill_id,
            state=state,
            actor=actor,
            reason=reason.strip(),
        )

    def list_assignments(self, agent_id: str | None = None) -> list[EmployeeSkillAssignment]:
        return [self._assignment_from_row(row) for row in self.database.list_employee_skill_assignments(agent_id)]

    def list_events(self, skill_id: str | None = None) -> list[SkillPackageEvent]:
        return [self._event_from_row(row) for row in self.database.list_skill_package_events(skill_id)]

    @staticmethod
    def _require_status(status: str) -> None:
        if status not in SKILL_PACKAGE_STATUSES:
            raise ValueError(f"Недопустимый статус навыка: {status}")

    @staticmethod
    def _require_employee_state(state: str) -> None:
        if state not in EMPLOYEE_SKILL_STATES:
            raise ValueError(f"Недопустимое состояние сотрудника по навыку: {state}")

    def _package_from_row(self, row) -> SkillPackage:
        return SkillPackage(
            skill_id=str(row["id"]),
            name=str(row["name"]),
            purpose=str(row["purpose"] or ""),
            supported_roles=self._json_list(row["supported_roles"]),
            prerequisites=str(row["prerequisites"] or ""),
            source_material=self._json_list(row["source_material"]),
            instructions=str(row["instructions"] or ""),
            tools=self._json_list(row["tools"]),
            expected_inputs=str(row["expected_inputs"] or ""),
            expected_outputs=str(row["expected_outputs"] or ""),
            prohibited_actions=str(row["prohibited_actions"] or ""),
            validation_checklist=self._json_list(row["validation_checklist"]),
            examples=self._json_list(row["examples"]),
            negative_examples=self._json_list(row["negative_examples"]),
            qualification_tasks=self._json_list(row["qualification_tasks"]),
            test_cases=self._json_list(row["test_cases"]),
            failure_patterns=self._json_list(row["failure_patterns"]),
            version=str(row["version"] or ""),
            status=str(row["status"] or ""),
            lifecycle_state=str(row["lifecycle_state"] or "CANDIDATE"),
            created_by=str(row["created_by"] or ""),
            updated_at=str(row["updated_at"] or ""),
        )

    @staticmethod
    def _assignment_from_row(row) -> EmployeeSkillAssignment:
        return EmployeeSkillAssignment(
            assignment_id=str(row["id"]),
            agent_id=str(row["agent_id"]),
            skill_id=str(row["skill_id"]),
            skill_name=str(row["name"]),
            skill_status=str(row["skill_status"]),
            state=str(row["state"]),
            purpose=str(row["purpose"] or ""),
            version=str(row["version"] or ""),
            updated_at=str(row["updated_at"] or ""),
        )

    @staticmethod
    def _event_from_row(row) -> SkillPackageEvent:
        return SkillPackageEvent(
            event_id=str(row["id"]),
            skill_id=str(row["skill_id"]),
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
