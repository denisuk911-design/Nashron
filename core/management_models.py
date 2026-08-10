from __future__ import annotations

from dataclasses import dataclass, field


MANAGEMENT_SCHEMA_VERSION = "1.0"

OWNER_ROLE = "ORGANIZATION_OWNER"

AGENT_LIFECYCLE_STATES = {
    "DRAFT",
    "ACTIVE",
    "SUSPENDED",
    "DISABLED",
    "ARCHIVED",
}

ROLE_IDS = {
    "PROJECT_MANAGER",
    "DESIGN_ENGINEER",
    "QA_ENGINEER",
    "VERIFICATION_ENGINEER",
    "DOCUMENT_CONTROL_OFFICER",
    "LEARNING_COORDINATOR",
    "RESEARCH_ASSISTANT",
    "CUSTOM_ROLE",
}

PROVIDER_IDS = {
    "CODEX_CLI",
    "GEMINI_CLI",
    "CLAUDE_CLI",
    "FUTURE_PROVIDER",
    "UNAVAILABLE",
}

PERMISSIONS = {
    "CHAT",
    "READ_WORKSPACE",
    "WRITE_WORKSPACE",
    "DELETE_FILES",
    "RUN_COMMANDS",
    "MODIFY_PROJECT",
    "CREATE_DOCUMENTS",
    "REVIEW_ARTIFACTS",
    "CREATE_FINDINGS",
    "CLOSE_FINDINGS",
    "MANAGE_SKILLS",
    "MANAGE_KNOWLEDGE",
    "MANAGE_EMPLOYEES",
    "MANAGE_STANDARDS",
    "REQUEST_APPROVAL",
    "GRANT_APPROVAL",
    "ACCESS_INTERNET",
    "ACCESS_EXTERNAL_PATHS",
}

OWNER_ONLY_PERMISSIONS = {
    "MANAGE_EMPLOYEES",
    "GRANT_APPROVAL",
    "MANAGE_STANDARDS",
}

ROLE_DEFAULT_PERMISSIONS = {
    "PROJECT_MANAGER": {
        "CHAT",
        "READ_WORKSPACE",
        "MODIFY_PROJECT",
        "REQUEST_APPROVAL",
    },
    "DESIGN_ENGINEER": {
        "CHAT",
        "READ_WORKSPACE",
        "WRITE_WORKSPACE",
        "RUN_COMMANDS",
        "MODIFY_PROJECT",
        "CREATE_DOCUMENTS",
    },
    "QA_ENGINEER": {
        "CHAT",
        "READ_WORKSPACE",
        "WRITE_WORKSPACE",
        "RUN_COMMANDS",
        "CREATE_DOCUMENTS",
        "REVIEW_ARTIFACTS",
        "CREATE_FINDINGS",
        "REQUEST_APPROVAL",
    },
    "VERIFICATION_ENGINEER": {
        "CHAT",
        "READ_WORKSPACE",
        "WRITE_WORKSPACE",
        "RUN_COMMANDS",
        "CREATE_DOCUMENTS",
        "REVIEW_ARTIFACTS",
        "CREATE_FINDINGS",
    },
    "DOCUMENT_CONTROL_OFFICER": {
        "CHAT",
        "READ_WORKSPACE",
        "WRITE_WORKSPACE",
        "RUN_COMMANDS",
        "CREATE_DOCUMENTS",
    },
    "LEARNING_COORDINATOR": {
        "CHAT",
        "READ_WORKSPACE",
        "WRITE_WORKSPACE",
        "RUN_COMMANDS",
        "CREATE_DOCUMENTS",
        "MANAGE_KNOWLEDGE",
    },
    "RESEARCH_ASSISTANT": {
        "CHAT",
        "READ_WORKSPACE",
        "WRITE_WORKSPACE",
        "RUN_COMMANDS",
        "CREATE_DOCUMENTS",
        "ACCESS_INTERNET",
    },
    "CUSTOM_ROLE": {
        "CHAT",
        "READ_WORKSPACE",
        "WRITE_WORKSPACE",
        "RUN_COMMANDS",
        "CREATE_DOCUMENTS",
    },
}

LIFECYCLE_TRANSITIONS = {
    "DRAFT": {"ACTIVE", "ARCHIVED", "DISABLED"},
    "ACTIVE": {"SUSPENDED", "DISABLED"},
    "SUSPENDED": {"ACTIVE", "DISABLED"},
    "DISABLED": {"ARCHIVED"},
    "ARCHIVED": set(),
}

RISKY_PERMISSIONS = {
    "DELETE_FILES",
    "RUN_COMMANDS",
    "WRITE_WORKSPACE",
    "ACCESS_EXTERNAL_PATHS",
    "MANAGE_KNOWLEDGE",
    "MANAGE_SKILLS",
}


@dataclass(frozen=True)
class RoleProfile:
    role_id: str
    display_name: str
    description: str
    responsibilities: list[str] = field(default_factory=list)
    restrictions: list[str] = field(default_factory=list)
    schema_version: str = MANAGEMENT_SCHEMA_VERSION


@dataclass(frozen=True)
class AgentProfile:
    agent_id: str
    display_name: str
    description: str
    lifecycle_state: str
    provider_id: str
    persona_id: str | None = None
    avatar_path: str | None = None
    aliases: tuple[str, ...] = ()
    schema_version: str = MANAGEMENT_SCHEMA_VERSION


ROLE_TEMPLATES = [
    RoleProfile(
        "PROJECT_MANAGER",
        "Project Manager",
        "Formalizes objectives, plans tasks and tracks status.",
        ["formalize_tasks", "create_plans", "track_blockers", "coordinate_handoffs"],
        ["no_final_engineering_approval", "no_silent_artifact_changes"],
    ),
    RoleProfile(
        "DESIGN_ENGINEER",
        "Design Engineer",
        "Creates engineering artifacts and performs self-checks.",
        ["schematic_design", "pcb_design", "bom", "documentation", "self_check"],
        ["cannot_verify_own_work", "cannot_close_qa_findings"],
    ),
    RoleProfile(
        "QA_ENGINEER",
        "QA Engineer",
        "Independently reviews requirements, artifacts, standards and evidence.",
        ["technical_review", "standard_compliance", "erc_drc_review", "create_findings"],
        ["does_not_act_as_original_author", "does_not_grant_owner_approval"],
    ),
    RoleProfile(
        "VERIFICATION_ENGINEER",
        "Verification Engineer",
        "Checks reproducibility, tool claims and negative cases.",
        ["reproduce_checks", "validate_outputs", "negative_tests", "verify_instructions"],
        ["does_not_act_as_original_author"],
    ),
    RoleProfile(
        "DOCUMENT_CONTROL_OFFICER",
        "Document Control Officer",
        "Maintains required documents, indexes, revisions and packages.",
        ["document_indexes", "missing_document_detection", "revision_tracking", "package_preparation"],
        ["cannot_invent_engineering_facts", "cannot_approve_documents", "cannot_delete_source_history"],
    ),
    RoleProfile(
        "LEARNING_COORDINATOR",
        "Learning Coordinator",
        "Maintains learning queues, qualification tasks and retraining recommendations.",
        ["learning_queue", "source_registration", "qualification_tracking", "weak_area_detection"],
        ["cannot_activate_unreviewed_knowledge", "cannot_change_standards", "no_unbounded_research"],
    ),
    RoleProfile(
        "RESEARCH_ASSISTANT",
        "Research Assistant",
        "Finds public datasheets, application notes, reference designs and source metadata.",
        ["source_search", "authority_labeling", "component_documentation"],
        ["cannot_approve_knowledge", "cannot_change_standards"],
    ),
    RoleProfile(
        "CUSTOM_ROLE",
        "Custom Role",
        "User-defined employee role prepared for later specialization.",
        ["owner_defined_scope", "manual_responsibility_assignment"],
        ["requires_manual_review_before_activation"],
    ),
]


DEFAULT_AGENT_PROFILES = [
    AgentProfile(
        agent_id="agent-roman",
        display_name="Roman",
        description="Current Codex-backed engineering execution agent.",
        lifecycle_state="ACTIVE",
        provider_id="CODEX_CLI",
        persona_id="roman_2050",
        aliases=("Роман",),
    ),
    AgentProfile(
        agent_id="agent-petr",
        display_name="Petr",
        description="Current Gemini-backed QA/review agent.",
        lifecycle_state="ACTIVE",
        provider_id="GEMINI_CLI",
        persona_id="petr_2050",
        aliases=("Петр", "Пётр"),
    ),
]
