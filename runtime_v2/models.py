from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


class WorkIntent(StrEnum):
    SOCIAL = "SOCIAL"
    QUESTION = "QUESTION"
    DISCUSSION = "DISCUSSION"
    WORK_REQUEST = "WORK_REQUEST"
    WORK_CONTINUATION = "WORK_CONTINUATION"
    WORK_MODIFICATION = "WORK_MODIFICATION"
    WORK_STOP = "WORK_STOP"
    WORK_REVIEW = "WORK_REVIEW"


class WorkflowStatus(StrEnum):
    DRAFT = "DRAFT"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING_FOR_OWNER = "WAITING_FOR_OWNER"
    PAUSED = "PAUSED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StepStatus(StrEnum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    INVALIDATED = "INVALIDATED"
    CANCELLED = "CANCELLED"


class HandoffStatus(StrEnum):
    CREATED = "CREATED"
    ACCEPTED = "ACCEPTED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


class FindingStatus(StrEnum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    REOPENED = "REOPENED"


class FailureReason(StrEnum):
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_CRASH = "PROVIDER_CRASH"
    TIMEOUT = "TIMEOUT"
    INVALID_OUTPUT = "INVALID_OUTPUT"
    MISSING_ARTIFACT = "MISSING_ARTIFACT"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    EMPLOYEE_DISABLED = "EMPLOYEE_DISABLED"
    ORGANIZATION_CHANGED = "ORGANIZATION_CHANGED"
    CANCELLED = "CANCELLED"


class ActionRisk(StrEnum):
    READ = "READ"
    WRITE = "WRITE"
    EXECUTE = "EXECUTE"
    NETWORK = "NETWORK"
    INSTALL = "INSTALL"
    DELETE = "DELETE"
    PUBLISH = "PUBLISH"
    EXTERNAL_SIDE_EFFECT = "EXTERNAL_SIDE_EFFECT"


RETRYABLE_FAILURES = {
    FailureReason.PROVIDER_UNAVAILABLE,
    FailureReason.PROVIDER_CRASH,
    FailureReason.TIMEOUT,
    FailureReason.INVALID_OUTPUT,
    FailureReason.MISSING_ARTIFACT,
}


@dataclass
class WorkflowStep:
    step_id: str
    employee_id: str
    operation: str
    expected_output: str
    dependencies: list[str] = field(default_factory=list)
    input_artifacts: list[str] = field(default_factory=list)
    requirement_keys: list[str] = field(default_factory=list)
    preferred_provider: str = "provider-a"
    fallback_providers: list[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    attempts: int = 0
    max_retries: int = 2
    requires_owner_approval: bool = False
    risk: ActionRisk = ActionRisk.READ
    output_artifacts: list[str] = field(default_factory=list)
    last_provider: str = ""
    last_error: str = ""
    started_at: str = ""
    completed_at: str = ""
    wave: int = 0


@dataclass
class WorkflowDefinition:
    name: str
    steps: list[WorkflowStep]
    max_handoffs: int = 16
    max_retries: int = 12
    max_review_cycles: int = 3
    max_agent_calls: int = 32


@dataclass
class ArtifactRevision:
    revision: int
    producer_employee_id: str
    provider_id: str
    content_hash: str
    evidence: dict[str, Any]
    created_at: str = field(default_factory=utc_now)


@dataclass
class Artifact:
    artifact_id: str
    task_id: str
    artifact_type: str
    revisions: list[ArtifactRevision] = field(default_factory=list)

    @property
    def current_revision(self) -> int:
        return self.revisions[-1].revision if self.revisions else 0


@dataclass
class Finding:
    finding_id: str
    artifact_id: str
    revision: int
    severity: str
    description: str
    evidence: dict[str, Any]
    owner_employee_id: str
    status: FindingStatus = FindingStatus.OPEN
    created_at: str = field(default_factory=utc_now)


@dataclass
class Handoff:
    handoff_id: str
    task_id: str
    source_employee: str
    target_employee: str
    input_artifacts: list[str]
    instructions: str
    expected_output: str
    status: HandoffStatus = HandoffStatus.CREATED
    created_at: str = field(default_factory=utc_now)
    completed_at: str = ""


@dataclass
class ProviderRun:
    run_id: str
    employee_id: str
    step_id: str
    provider_id: str
    model: str
    ok: bool
    failure_reason: str = ""
    duration_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    created_at: str = field(default_factory=utc_now)


@dataclass
class WorkflowState:
    workflow_id: str
    task_id: str
    organization_id: str
    goal: str
    definition_name: str
    status: WorkflowStatus
    steps: dict[str, WorkflowStep]
    requirements: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Artifact] = field(default_factory=dict)
    findings: dict[str, Finding] = field(default_factory=dict)
    handoffs: dict[str, Handoff] = field(default_factory=dict)
    provider_runs: list[ProviderRun] = field(default_factory=list)
    owner_decisions: dict[str, bool] = field(default_factory=dict)
    revision: int = 0
    wave: int = 0
    total_retries: int = 0
    total_agent_calls: int = 0
    review_cycles: int = 0
    max_handoffs: int = 16
    max_retries: int = 12
    max_review_cycles: int = 3
    max_agent_calls: int = 32
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowState":
        steps = {
            key: WorkflowStep(
                **{
                    **value,
                    "status": StepStatus(value["status"]),
                    "risk": ActionRisk(value.get("risk", ActionRisk.READ)),
                }
            )
            for key, value in data.get("steps", {}).items()
        }
        artifacts = {
            key: Artifact(
                artifact_id=value["artifact_id"],
                task_id=value["task_id"],
                artifact_type=value["artifact_type"],
                revisions=[ArtifactRevision(**item) for item in value.get("revisions", [])],
            )
            for key, value in data.get("artifacts", {}).items()
        }
        findings = {
            key: Finding(**{**value, "status": FindingStatus(value["status"])})
            for key, value in data.get("findings", {}).items()
        }
        handoffs = {
            key: Handoff(**{**value, "status": HandoffStatus(value["status"])})
            for key, value in data.get("handoffs", {}).items()
        }
        return cls(
            **{
                **data,
                "status": WorkflowStatus(data["status"]),
                "steps": steps,
                "artifacts": artifacts,
                "findings": findings,
                "handoffs": handoffs,
                "provider_runs": [ProviderRun(**item) for item in data.get("provider_runs", [])],
            }
        )


@dataclass
class AgentAction:
    workflow_id: str
    task_id: str
    organization_id: str
    employee_id: str
    step_id: str
    operation: str
    expected_output: str
    requirements: dict[str, Any]
    input_artifacts: list[Artifact]
    risk: ActionRisk


@dataclass
class AgentResult:
    ok: bool
    provider_id: str
    model: str = "test-model"
    summary: str = ""
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    failure_reason: FailureReason | None = None
    duration_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class TraceEvent:
    trace_id: str
    workflow_id: str
    event_type: str
    detail: dict[str, Any]
    created_at: str = field(default_factory=utc_now)
