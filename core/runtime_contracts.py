"""Runtime-neutral contracts owned by the Product/Core boundary.

These DTOs deliberately contain product identity references, not SDK agent
instances. Runtime adapters may use their own mechanics behind this boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, Sequence


class ExecutionPolicy(StrEnum):
    CONVERSATIONAL = "conversational"
    DIRECT_ACTION = "direct_action"
    MANAGED_AGENT = "managed_agent"
    DYNAMIC_MULTI_AGENT = "dynamic_multi_agent"
    DETERMINISTIC_WORKFLOW = "deterministic_workflow"
    LONG_RUNNING_PROJECT = "long_running_project"


@dataclass(frozen=True)
class EmployeeRef:
    """Stable product employee identity passed to a runtime adapter."""

    employee_id: str
    display_name: str
    role: str
    provider_binding_id: str = ""
    competencies: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExecutionRequest:
    organization_id: str
    objective: str
    policy: ExecutionPolicy
    employees: tuple[EmployeeRef, ...] = ()
    correlation_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.organization_id.strip():
            raise ValueError("organization_id is required")
        if not self.objective.strip():
            raise ValueError("objective is required")


class RuntimeEventType(StrEnum):
    EXECUTION_STARTED = "execution.started"
    RUN_STARTED = EXECUTION_STARTED
    EXECUTION_PROGRESSED = "execution.progressed"
    EXECUTION_REPLANNED = "execution.replanned"
    EXECUTION_WAITING_FOR_USER = "execution.waiting_for_user"
    PLAN_CREATED = "plan.created"
    WORK_STARTED = "work.started"
    TOOL_CALLED = "tool.called"
    OBSERVATION_RECORDED = "observation.recorded"
    ARTIFACT_CREATED = "artifact.created"
    REVIEW_COMPLETED = "review.completed"
    WORK_FINISHED = "work.finished"
    EXECUTION_COMPLETED = "execution.completed"
    RUN_COMPLETED = EXECUTION_COMPLETED
    EXECUTION_FAILED = "execution.failed"
    RUN_FAILED = EXECUTION_FAILED
    AGENT_STARTED = "agent.started"
    AGENT_PROGRESS = "agent.progressed"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"
    ARTIFACT_UPDATED = "artifact.updated"
    REVIEW_REQUESTED = "review.requested"
    CLARIFICATION_REQUIRED = "clarification.required"


@dataclass(frozen=True)
class RuntimeCapabilities:
    """Mechanics a runtime can provide behind the Product boundary."""

    tool_calls: bool = False
    multi_agent: bool = False
    persistence: bool = False
    recovery: bool = False
    human_approval: bool = False
    streaming: bool = False


@dataclass(frozen=True)
class RuntimeHealth:
    runtime_id: str
    available: bool
    checked_at: str = ""
    detail: str = ""


@dataclass(frozen=True)
class RuntimeUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0
    duration_ms: int = 0


@dataclass(frozen=True)
class RuntimeError:
    code: str
    message: str
    retryable: bool = False
    side_effects_committed: bool = False


@dataclass(frozen=True)
class RuntimeTraceReference:
    trace_id: str = ""
    uri: str = ""


@dataclass(frozen=True)
class RuntimeEvent:
    event_type: RuntimeEventType
    organization_id: str
    correlation_id: str = ""
    run_id: str = ""
    employee_id: str = ""
    work_item_id: str = ""
    artifact_id: str = ""
    evidence_id: str = ""
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionResult:
    ok: bool
    organization_id: str
    runtime_id: str
    summary: str
    correlation_id: str = ""
    goal_id: str = ""
    artifact_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    events: tuple[RuntimeEvent, ...] = ()
    data: dict[str, Any] = field(default_factory=dict)
    usage: RuntimeUsage = field(default_factory=RuntimeUsage)
    errors: tuple[RuntimeError, ...] = ()
    trace_reference: RuntimeTraceReference = field(default_factory=RuntimeTraceReference)
    runtime_metadata: dict[str, Any] = field(default_factory=dict)


class RuntimeAdapter(Protocol):
    runtime_id: str

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        ...


def event_type_from_native_stage(stage: str) -> RuntimeEventType | None:
    """Map Native trace stages without leaking Native enums to Product UI."""
    mapping = {
        "goal_created": RuntimeEventType.RUN_STARTED,
        "plan_created": RuntimeEventType.PLAN_CREATED,
        "work_item_running": RuntimeEventType.WORK_STARTED,
        "tool_called": RuntimeEventType.TOOL_CALLED,
        "tool_observed": RuntimeEventType.OBSERVATION_RECORDED,
        "artifact_created": RuntimeEventType.ARTIFACT_CREATED,
        "review_completed": RuntimeEventType.REVIEW_COMPLETED,
        "work_item_finished": RuntimeEventType.WORK_FINISHED,
        "goal_status:COMPLETED": RuntimeEventType.RUN_COMPLETED,
        "goal_status:FAILED": RuntimeEventType.RUN_FAILED,
    }
    return mapping.get(stage)


def tupled(values: Sequence[str] | None) -> tuple[str, ...]:
    return tuple(str(value) for value in (values or ()) if str(value))
