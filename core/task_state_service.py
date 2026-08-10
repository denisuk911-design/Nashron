from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from .database import Database


STATE_MACHINE_VERSION = "1.0"

TASK_STATES = (
    "NEW",
    "REQUIREMENTS_DRAFT",
    "READY_FOR_DESIGN",
    "IN_DESIGN",
    "READY_FOR_REVIEW",
    "IN_REVIEW",
    "REWORK_REQUIRED",
    "READY_FOR_VERIFICATION",
    "IN_VERIFICATION",
    "OWNER_REVIEW",
    "COMPLETED",
    "BLOCKED",
    "CANCELLED",
)

LEGAL_TRANSITIONS: dict[str, set[str]] = {
    "NEW": {"REQUIREMENTS_DRAFT", "READY_FOR_DESIGN", "BLOCKED", "CANCELLED"},
    "REQUIREMENTS_DRAFT": {"READY_FOR_DESIGN", "BLOCKED", "CANCELLED"},
    "READY_FOR_DESIGN": {"IN_DESIGN", "BLOCKED", "CANCELLED"},
    "IN_DESIGN": {"READY_FOR_REVIEW", "BLOCKED", "CANCELLED"},
    "READY_FOR_REVIEW": {"IN_REVIEW", "BLOCKED", "CANCELLED"},
    "IN_REVIEW": {"REWORK_REQUIRED", "READY_FOR_VERIFICATION", "BLOCKED", "CANCELLED"},
    "REWORK_REQUIRED": {"IN_DESIGN", "BLOCKED", "CANCELLED"},
    "READY_FOR_VERIFICATION": {"IN_VERIFICATION", "BLOCKED", "CANCELLED"},
    "IN_VERIFICATION": {"OWNER_REVIEW", "REWORK_REQUIRED", "BLOCKED", "CANCELLED"},
    "OWNER_REVIEW": {"COMPLETED", "REWORK_REQUIRED", "BLOCKED", "CANCELLED"},
    "BLOCKED": {"REQUIREMENTS_DRAFT", "READY_FOR_DESIGN", "IN_DESIGN", "IN_REVIEW", "IN_VERIFICATION", "CANCELLED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
}

ROLE_FORBIDDEN_TRANSITIONS = {
    "DESIGN_ENGINEER": {"COMPLETED"},
    "QA_ENGINEER": {"COMPLETED"},
    "VERIFICATION_ENGINEER": {"COMPLETED"},
}


@dataclass(frozen=True)
class TaskTransitionRequest:
    task_id: str
    next_state: str
    actor: str
    logical_role: str
    reason: str
    supporting_message_id: int | None = None
    run_id: str | None = None
    artifacts_affected: Iterable[str] = ()
    checks_performed: Iterable[str] = ()
    unresolved_risks: Iterable[str] = ()
    owner_approval_required: bool = False


class TaskStateError(ValueError):
    pass


class TaskStateService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create_task(self, project_id: str, title: str, owner_message_id: int | None = None) -> str:
        return self.database.create_task(project_id, title, owner_message_id, STATE_MACHINE_VERSION)

    def get_state(self, task_id: str) -> str:
        task = self.database.get_task(task_id)
        if task is None:
            raise TaskStateError(f"Unknown task: {task_id}")
        return str(task["state"])

    def transition(self, request: TaskTransitionRequest) -> None:
        previous_state = self.get_state(request.task_id)
        self.validate_transition(previous_state, request.next_state, request.logical_role)
        if request.next_state == "COMPLETED" and self.database.task_has_blocking_findings(request.task_id):
            raise TaskStateError("Cannot complete a task with unresolved blocking findings")
        self.database.record_task_transition(
            task_id=request.task_id,
            previous_state=previous_state,
            next_state=request.next_state,
            actor=request.actor,
            logical_role=request.logical_role,
            reason=request.reason,
            supporting_message_id=request.supporting_message_id,
            run_id=request.run_id,
            artifacts_affected=list(request.artifacts_affected),
            checks_performed=list(request.checks_performed),
            unresolved_risks=list(request.unresolved_risks),
            owner_approval_required=request.owner_approval_required,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )

    def validate_transition(self, previous_state: str, next_state: str, logical_role: str) -> None:
        if previous_state not in TASK_STATES:
            raise TaskStateError(f"Unknown previous state: {previous_state}")
        if next_state not in TASK_STATES:
            raise TaskStateError(f"Unknown next state: {next_state}")
        if next_state not in LEGAL_TRANSITIONS[previous_state]:
            raise TaskStateError(f"Illegal transition: {previous_state} -> {next_state}")
        if next_state in ROLE_FORBIDDEN_TRANSITIONS.get(logical_role, set()):
            raise TaskStateError(f"Role {logical_role} cannot move task to {next_state}")
