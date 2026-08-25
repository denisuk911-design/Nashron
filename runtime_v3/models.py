from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class GoalStatus(StrEnum):
    DRAFT = "DRAFT"
    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    REVIEW = "REVIEW"
    REWORK = "REWORK"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WorkItemStatus(StrEnum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    REVIEW = "REVIEW"
    REWORK = "REWORK"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class ActionType(StrEnum):
    FILESYSTEM_READ = "filesystem.read"
    FILESYSTEM_LIST = "filesystem.list"
    FILESYSTEM_WRITE = "filesystem.write"
    ARTIFACT_CREATE = "artifact.create"
    REVIEW_ARTIFACT = "artifact.review"
    MESSAGE = "message"


class ObservationStatus(StrEnum):
    OK = "OK"
    FAILED = "FAILED"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass
class EmployeeBinding:
    employee_id: str
    display_name: str
    role: str
    competencies: list[str]
    provider_binding_id: str = "provider-neutral"


@dataclass
class Goal:
    goal_id: str
    objective: str
    status: GoalStatus = GoalStatus.DRAFT
    plan_id: str | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)


@dataclass
class WorkItem:
    work_item_id: str
    goal_id: str
    objective: str
    assigned_employee_id: str
    dependencies: list[str] = field(default_factory=list)
    input_artifact_ids: list[str] = field(default_factory=list)
    required_capabilities: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    expected_artifact_types: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    evidence_requirements: list[str] = field(default_factory=list)
    status: WorkItemStatus = WorkItemStatus.PENDING
    attempt: int = 0
    checkpoint_id: str | None = None
    result: dict[str, Any] = field(default_factory=dict)


@dataclass
class Plan:
    plan_id: str
    goal_id: str
    supervisor_employee_id: str
    work_item_ids: list[str]
    created_at: str = field(default_factory=utc_now)


@dataclass
class Action:
    action_id: str
    work_item_id: str
    employee_id: str
    action_type: ActionType
    payload: dict[str, Any]
    created_at: str = field(default_factory=utc_now)


@dataclass
class Observation:
    observation_id: str
    action_id: str
    status: ObservationStatus
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)


@dataclass
class Artifact:
    artifact_id: str
    goal_id: str
    work_item_id: str
    artifact_type: str
    logical_uri: str
    path: str
    revision: int
    content_hash: str
    created_by_employee_id: str
    created_from_action_id: str
    created_from_observation_id: str
    created_at: str = field(default_factory=utc_now)


@dataclass
class Evidence:
    evidence_id: str
    goal_id: str
    work_item_id: str
    evidence_type: str
    source_action_id: str
    source_observation_id: str
    summary: str
    passed: bool
    created_at: str = field(default_factory=utc_now)


@dataclass
class Finding:
    finding_id: str
    goal_id: str
    work_item_id: str
    reviewer_employee_id: str
    artifact_id: str
    severity: str
    description: str
    status: str = "OPEN"
    created_at: str = field(default_factory=utc_now)


@dataclass
class ReviewResult:
    accepted: bool
    findings: list[Finding] = field(default_factory=list)


@dataclass
class Handoff:
    handoff_id: str
    from_employee_id: str
    to_employee_id: str
    work_item_id: str
    artifact_ids: list[str]
    context_refs: list[str]
    expected_result: str
    acceptance: list[str]
    evidence_requirements: list[str]
    created_at: str = field(default_factory=utc_now)


@dataclass
class ProviderRun:
    run_id: str
    employee_id: str
    provider_id: str
    work_item_id: str
    status: str
    started_at: str
    finished_at: str
    error: str = ""
    action_count: int = 0


@dataclass
class RuntimeState:
    organization_id: str
    goals: dict[str, Goal] = field(default_factory=dict)
    plans: dict[str, Plan] = field(default_factory=dict)
    work_items: dict[str, WorkItem] = field(default_factory=dict)
    actions: dict[str, Action] = field(default_factory=dict)
    observations: dict[str, Observation] = field(default_factory=dict)
    artifacts: dict[str, Artifact] = field(default_factory=dict)
    evidence: dict[str, Evidence] = field(default_factory=dict)
    findings: dict[str, Finding] = field(default_factory=dict)
    handoffs: dict[str, Handoff] = field(default_factory=dict)
    provider_runs: dict[str, ProviderRun] = field(default_factory=dict)
    checkpoints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RuntimeState":
        state = cls(organization_id=value["organization_id"])
        state.goals = {key: _goal(item) for key, item in value.get("goals", {}).items()}
        state.plans = {key: Plan(**item) for key, item in value.get("plans", {}).items()}
        state.work_items = {key: _work_item(item) for key, item in value.get("work_items", {}).items()}
        state.actions = {key: _action(item) for key, item in value.get("actions", {}).items()}
        state.observations = {key: _observation(item) for key, item in value.get("observations", {}).items()}
        state.artifacts = {key: Artifact(**item) for key, item in value.get("artifacts", {}).items()}
        state.evidence = {key: Evidence(**item) for key, item in value.get("evidence", {}).items()}
        state.findings = {key: Finding(**item) for key, item in value.get("findings", {}).items()}
        state.handoffs = {key: Handoff(**item) for key, item in value.get("handoffs", {}).items()}
        state.provider_runs = {key: ProviderRun(**item) for key, item in value.get("provider_runs", {}).items()}
        state.checkpoints = list(value.get("checkpoints", []))
        return state


def dumps_state(state: RuntimeState) -> str:
    return json.dumps(state.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def load_state(path: Path) -> RuntimeState:
    return RuntimeState.from_dict(json.loads(path.read_text(encoding="utf-8")))


def _goal(item: dict[str, Any]) -> Goal:
    item = dict(item)
    item["status"] = GoalStatus(item["status"])
    return Goal(**item)


def _work_item(item: dict[str, Any]) -> WorkItem:
    item = dict(item)
    item["status"] = WorkItemStatus(item["status"])
    return WorkItem(**item)


def _action(item: dict[str, Any]) -> Action:
    item = dict(item)
    item["action_type"] = ActionType(item["action_type"])
    return Action(**item)


def _observation(item: dict[str, Any]) -> Observation:
    item = dict(item)
    item["status"] = ObservationStatus(item["status"])
    return Observation(**item)
