from __future__ import annotations

from dataclasses import dataclass, field


PROVIDER_SCHEMA_VERSION = "1.0"

INSTALLATION_STATES = {
    "NOT_INSTALLED",
    "DETECTED",
    "INSTALLATION_REQUIRED",
    "INSTALLING",
    "INSTALLED",
    "UPDATE_REQUIRED",
    "INSTALLATION_FAILED",
    "UNSUPPORTED",
}

AUTHENTICATION_STATES = {
    "NOT_AUTHENTICATED",
    "AUTHENTICATION_REQUIRED",
    "AUTHENTICATION_IN_PROGRESS",
    "AUTHENTICATED",
    "AUTHENTICATION_EXPIRED",
    "AUTHENTICATION_FAILED",
    "USER_ACTION_REQUIRED",
}

ACCESS_STATES = {
    "NOT_CHECKED",
    "ACCESS_AVAILABLE",
    "ACCESS_LIMITED",
    "PLAN_INCOMPATIBLE",
    "QUOTA_EXCEEDED",
    "BILLING_REQUIRED",
    "PROVIDER_REJECTED",
    "UNKNOWN",
}

HEALTH_STATES = {
    "READY",
    "DEGRADED",
    "NOT_READY",
    "BLOCKED",
    "UNKNOWN",
}

CAPABILITY_STATES = {
    "NOT_CHECKED",
    "SUPPORTED",
    "PARTIAL",
    "UNSUPPORTED",
    "UNKNOWN",
}

EMPLOYEE_READINESS_STATES = {
    "PROFILE_INCOMPLETE",
    "PROVIDER_NOT_ASSIGNED",
    "PROVIDER_NOT_INSTALLED",
    "INSTALLATION_REQUIRED",
    "AUTHENTICATION_REQUIRED",
    "ACCESS_CHECK_REQUIRED",
    "PLAN_INCOMPATIBLE",
    "CAPABILITY_TEST_REQUIRED",
    "READY",
    "DEGRADED",
    "BLOCKED",
    "SETUP_FAILED",
}

ASSIGNMENT_STATES = {
    "DRAFT",
    "SETUP_REQUIRED",
    "READY",
    "DEGRADED",
    "BLOCKED",
    "DISABLED",
}


@dataclass(frozen=True)
class ProviderProfile:
    provider_id: str
    display_name: str
    provider_family: str
    adapter_id: str
    supported_os: list[str]
    installation_strategy: str
    authentication_strategy: str
    executable_names: list[str]
    minimum_supported_version: str | None = None
    recommended_version: str | None = None
    setup_instructions: str = ""
    known_limitations: list[str] = field(default_factory=list)
    required_capabilities: list[str] = field(default_factory=list)
    provider_schema_version: str = PROVIDER_SCHEMA_VERSION


@dataclass(frozen=True)
class ProviderHealth:
    provider_id: str
    detected_version: str | None
    installation_status: str
    authentication_status: str
    access_status: str
    health_status: str
    capability_status: str
    account_label: str | None = None
    diagnostic: str = ""


@dataclass(frozen=True)
class AgentProviderAssignment:
    assignment_id: str
    agent_id: str
    provider_id: str
    installation_id: str | None
    account_id: str | None
    capability_profile_id: str | None
    execution_mode: str
    priority: int
    fallback_provider_id: str | None
    status: str


DEFAULT_PROVIDER_PROFILES = [
    ProviderProfile(
        provider_id="CODEX_CLI",
        display_name="Codex CLI",
        provider_family="openai",
        adapter_id="codex_cli",
        supported_os=["Windows"],
        installation_strategy="bundled_or_path_or_vscode_extension",
        authentication_strategy="official_cli_login",
        executable_names=["codex", "codex.exe"],
        setup_instructions="Use the official Codex CLI login flow. The app must not store credentials.",
        required_capabilities=["chat", "structured_response", "file_read", "file_write", "command_execution"],
    ),
    ProviderProfile(
        provider_id="GEMINI_CLI",
        display_name="Gemini CLI",
        provider_family="google",
        adapter_id="gemini_cli",
        supported_os=["Windows"],
        installation_strategy="path_executable",
        authentication_strategy="environment_api_key_or_cli_config",
        executable_names=["gemini", "gemini.exe"],
        setup_instructions="Install Gemini CLI and configure GEMINI_API_KEY outside the app.",
        required_capabilities=["chat", "structured_response"],
    ),
    ProviderProfile(
        provider_id="CLAUDE_CLI",
        display_name="Claude CLI / Claude Code",
        provider_family="anthropic",
        adapter_id="claude_cli",
        supported_os=["Windows"],
        installation_strategy="manual_or_future_adapter",
        authentication_strategy="provider_controlled_login",
        executable_names=["claude", "claude.exe"],
        setup_instructions="Claude support is not execution-ready until an official adapter is implemented and tested.",
        known_limitations=["Adapter not implemented in Phase 2A.1."],
        required_capabilities=["chat", "structured_response", "long_context"],
    ),
]
