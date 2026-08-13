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


class TaskState(StrEnum):
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING_RETRY = "WAITING_RETRY"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class StepState(StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ActionClass(StrEnum):
    AUTO = "AUTO"
    NOTIFY = "NOTIFY"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    FORBIDDEN = "FORBIDDEN"


class KnowledgeStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"


class SkillDecision(StrEnum):
    CURRENT = "CURRENT"
    CANDIDATE = "CANDIDATE"
    PROMOTED = "PROMOTED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class AgentIdentity:
    agent_id: str
    organization_id: str
    role_id: str
    display_name: str
    preferred_name: str
    communication_style: str
    avatar_ref: str = ""
    relationship_role: str = "employee"


@dataclass(frozen=True)
class ProfessionalCapability:
    profession_id: str
    competencies: tuple[str, ...] = ()
    skill_refs: tuple[str, ...] = ()
    tool_refs: tuple[str, ...] = ()
    knowledge_refs: tuple[str, ...] = ()
    experience_refs: tuple[str, ...] = ()
    qualification_state: str = "NOT_STUDIED"
    qualification_evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class OrganizationKnowledge:
    knowledge_id: str
    organization_id: str
    profession_id: str
    kind: str
    content: str
    source_refs: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    status: KnowledgeStatus = KnowledgeStatus.CANDIDATE
    contributor_id: str = ""
    contributor_status: str = "ACTIVE"


@dataclass(frozen=True)
class ContextReference:
    ref_id: str
    kind: str
    text: str
    provenance: str
    relevance: int
    token_cost: int


@dataclass(frozen=True)
class WorkspaceReference:
    workspace_id: str
    root_uri: str
    permissions: tuple[str, ...] = ("read",)


@dataclass(frozen=True)
class Artifact:
    artifact_id: str
    organization_id: str
    task_id: str
    artifact_type: str
    logical_uri: str
    owner_agent_id: str
    version: int
    content: str
    content_hash: str
    provenance: tuple[str, ...]
    status: str = "CREATED"


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    claim: str
    action: str
    artifact_ids: tuple[str, ...]
    result: str
    source: str
    created_at: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    ok: bool
    result: str
    evidence_id: str


@dataclass
class TaskStep:
    step_id: str
    instruction: str
    expected_output: str
    effect_key: str
    required_artifact_ids: list[str] = field(default_factory=list)
    output_artifact_id: str = ""
    output_artifact_type: str = "document"
    tool_name: str = ""
    action_class: ActionClass = ActionClass.AUTO
    state: StepState = StepState.PENDING
    provider_id: str = ""
    attempts: int = 0
    last_error: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> TaskStep:
        item = dict(value)
        item["action_class"] = ActionClass(item.get("action_class", ActionClass.AUTO))
        item["state"] = StepState(item.get("state", StepState.PENDING))
        return cls(**item)


@dataclass
class Task:
    task_id: str
    title: str
    goal: str
    acceptance: list[str]
    steps: list[TaskStep]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Task:
        item = dict(value)
        item["steps"] = [TaskStep.from_dict(row) for row in item.get("steps", [])]
        return cls(**item)


@dataclass(frozen=True)
class ProviderBinding:
    provider_id: str
    adapter_id: str
    model: str
    candidate_provider_ids: tuple[str, ...]


@dataclass
class Checkpoint:
    run_id: str
    revision: int = 0
    reason: str = "created"
    created_at: str = field(default_factory=utc_now)


@dataclass
class CanonicalAgentState:
    schema_version: str
    run_id: str
    agent_id: str
    organization_id: str
    role_id: str
    identity: AgentIdentity
    capability: ProfessionalCapability
    active_task: Task
    task_state: TaskState
    task_plan: list[str]
    conversation_summary: str
    working_context: list[ContextReference]
    skills_used: list[str]
    knowledge_used: list[str]
    standards_used: list[str]
    artifact_ids: list[str]
    findings: list[str]
    decisions: list[str]
    tool_results: list[ToolResult]
    evidence: list[EvidenceRecord]
    workspace: WorkspaceReference
    pending_actions: list[str]
    checkpoint: Checkpoint
    provider_binding: ProviderBinding
    completed_effect_keys: list[str]
    trace_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CanonicalAgentState:
        item = dict(value)
        item["identity"] = AgentIdentity(**item["identity"])
        capability = dict(item["capability"])
        for key in (
            "competencies",
            "skill_refs",
            "tool_refs",
            "knowledge_refs",
            "experience_refs",
            "qualification_evidence_ids",
        ):
            capability[key] = tuple(capability.get(key, ()))
        item["capability"] = ProfessionalCapability(**capability)
        item["active_task"] = Task.from_dict(item["active_task"])
        item["task_state"] = TaskState(item["task_state"])
        item["working_context"] = [ContextReference(**row) for row in item.get("working_context", [])]
        item["tool_results"] = [ToolResult(**row) for row in item.get("tool_results", [])]
        item["evidence"] = [
            EvidenceRecord(
                **{
                    **row,
                    "artifact_ids": tuple(row.get("artifact_ids", ())),
                }
            )
            for row in item.get("evidence", [])
        ]
        workspace = dict(item["workspace"])
        workspace["permissions"] = tuple(workspace.get("permissions", ()))
        item["workspace"] = WorkspaceReference(**workspace)
        item["checkpoint"] = Checkpoint(**item["checkpoint"])
        binding = dict(item["provider_binding"])
        binding["candidate_provider_ids"] = tuple(binding.get("candidate_provider_ids", ()))
        item["provider_binding"] = ProviderBinding(**binding)
        return cls(**item)


@dataclass
class StructuredHandoff:
    handoff_id: str
    from_agent_id: str
    to_agent_id: str
    task_id: str
    intent: str
    artifact_ids: list[str]
    expected_output: str
    constraints: list[str]
    context_refs: list[str]
    acceptance: list[str]
    evidence_requirements: list[str]
    status: str = "CREATED"


@dataclass(frozen=True)
class ProviderRequest:
    run_id: str
    agent_id: str
    organization_id: str
    task_id: str
    step: TaskStep
    context: tuple[ContextReference, ...]
    artifact_ids: tuple[str, ...]
    handoff_id: str = ""


@dataclass(frozen=True)
class ProviderResult:
    summary: str
    artifact: Artifact | None = None
    tool_intent: str = ""


@dataclass(frozen=True)
class TraceEvent:
    trace_id: str
    run_id: str
    task_id: str
    agent_id: str
    provider_id: str
    model: str
    event_type: str
    started_at: str
    ended_at: str
    latency_ms: float
    context_input_ids: tuple[str, ...]
    skill_ids: tuple[str, ...]
    knowledge_ids: tuple[str, ...]
    tool_names: tuple[str, ...]
    artifact_ids: tuple[str, ...]
    handoff_ids: tuple[str, ...]
    errors: tuple[str, ...]
    result: str
    usage: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CandidateLesson:
    lesson_id: str
    organization_id: str
    profession_id: str
    skill_id: str
    finding_id: str
    content: str
    evidence_ids: tuple[str, ...]
    contributor_id: str


@dataclass
class SkillVersion:
    skill_id: str
    organization_id: str
    profession_id: str
    version: int
    instructions: str
    source_refs: list[str]
    examples: list[str]
    tools: list[str]
    limitations: list[str]
    behaviors: dict[str, str]
    contributors: list[str]
    status: SkillDecision = SkillDecision.CANDIDATE


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    input_text: str
    expected_output: str
    critical: bool = False


@dataclass(frozen=True)
class EvaluationReport:
    skill_id: str
    current_version: int
    candidate_version: int
    current_score: float
    candidate_score: float
    critical_regressions: tuple[str, ...]
    decision: SkillDecision


@dataclass(frozen=True)
class BootstrapPackage:
    agent_id: str
    profession_id: str
    organizational_knowledge: tuple[OrganizationKnowledge, ...]
    active_skills: tuple[SkillVersion, ...]
