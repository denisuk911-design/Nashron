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
    integration_type: str = "CLI"
    support_status: str = "CATALOG_ONLY"
    official_url: str = ""
    install_command: list[str] = field(default_factory=list)
    auth_command: list[str] = field(default_factory=list)
    update_command: list[str] = field(default_factory=list)
    uninstall_command: list[str] = field(default_factory=list)
    capability_matrix: dict[str, str] = field(default_factory=dict)
    credential_kind: str = "NONE"
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
        integration_type="CLI",
        support_status="SUPPORTED",
        official_url="https://developers.openai.com/codex",
        install_command=["npm", "install", "-g", "@openai/codex"],
        auth_command=["codex", "login"],
        update_command=["npm", "install", "-g", "@openai/codex"],
        uninstall_command=["npm", "uninstall", "-g", "@openai/codex"],
        capability_matrix={"chat": "SUPPORTED", "files": "SUPPORTED", "commands": "SUPPORTED", "structured_output": "SUPPORTED"},
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
        integration_type="CLI",
        support_status="SUPPORTED",
        official_url="https://github.com/google-gemini/gemini-cli",
        install_command=["npm", "install", "-g", "@google/gemini-cli"],
        auth_command=["gemini"],
        update_command=["npm", "install", "-g", "@google/gemini-cli@latest"],
        uninstall_command=["npm", "uninstall", "-g", "@google/gemini-cli"],
        capability_matrix={"chat": "SUPPORTED", "files": "PARTIAL", "commands": "PARTIAL", "structured_output": "SUPPORTED"},
        credential_kind="OPTIONAL_API_KEY",
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
        integration_type="CLI",
        support_status="EXPERIMENTAL",
        official_url="https://docs.anthropic.com/en/docs/claude-code/getting-started",
        install_command=["npm", "install", "-g", "@anthropic-ai/claude-code"],
        auth_command=["claude"],
        update_command=["claude", "update"],
        uninstall_command=["npm", "uninstall", "-g", "@anthropic-ai/claude-code"],
        capability_matrix={"chat": "ADAPTER_REQUIRED", "files": "ADAPTER_REQUIRED", "commands": "ADAPTER_REQUIRED", "structured_output": "ADAPTER_REQUIRED"},
    ),
    ProviderProfile(
        "GITHUB_COPILOT_CLI", "GitHub Copilot CLI", "github", "copilot_cli", ["Windows", "macOS", "Linux"],
        "official_package_manager", "official_cli_login", ["copilot", "copilot.exe"],
        setup_instructions="Install from WinGet or npm, then use /login on first launch.",
        known_limitations=["Execution adapter is not implemented yet."], required_capabilities=["chat", "file_read", "file_write", "command_execution"],
        integration_type="CLI", support_status="EXPERIMENTAL", official_url="https://docs.github.com/en/copilot/how-tos/copilot-cli/cli-getting-started",
        install_command=["winget", "install", "GitHub.Copilot"], auth_command=["copilot"],
        update_command=["winget", "upgrade", "GitHub.Copilot"], uninstall_command=["winget", "uninstall", "GitHub.Copilot"],
        capability_matrix={"chat": "ADAPTER_REQUIRED", "files": "ADAPTER_REQUIRED", "commands": "ADAPTER_REQUIRED"},
    ),
    ProviderProfile("OPENAI_API", "OpenAI API", "openai", "openai_api", ["Windows", "macOS", "Linux"], "none", "api_key", [], integration_type="API", support_status="CATALOG_ONLY", official_url="https://platform.openai.com/docs/quickstart", credential_kind="API_KEY"),
    ProviderProfile("ANTHROPIC_API", "Anthropic API", "anthropic", "anthropic_api", ["Windows", "macOS", "Linux"], "none", "api_key", [], integration_type="API", support_status="CATALOG_ONLY", official_url="https://docs.anthropic.com/en/api/getting-started", credential_kind="API_KEY"),
    ProviderProfile("GEMINI_API", "Google Gemini API", "google", "gemini_api", ["Windows", "macOS", "Linux"], "none", "api_key", [], integration_type="API", support_status="CATALOG_ONLY", official_url="https://ai.google.dev/gemini-api/docs/quickstart", credential_kind="API_KEY"),
    ProviderProfile("DEEPSEEK_API", "DeepSeek API", "deepseek", "deepseek_api", ["Windows", "macOS", "Linux"], "none", "api_key", [], integration_type="API", support_status="CATALOG_ONLY", official_url="https://api-docs.deepseek.com/", known_limitations=["DeepSeek is available here as an API integration only; there is no claimed official CLI adapter."], credential_kind="API_KEY"),
    ProviderProfile("AZURE_OPENAI_API", "Azure OpenAI", "microsoft", "azure_openai_api", ["Windows", "macOS", "Linux"], "none", "api_key_or_identity", [], integration_type="GATEWAY", support_status="CATALOG_ONLY", official_url="https://learn.microsoft.com/azure/ai-services/openai/", credential_kind="API_KEY"),
    ProviderProfile("MISTRAL_API", "Mistral AI API", "mistral", "mistral_api", ["Windows", "macOS", "Linux"], "none", "api_key", [], integration_type="API", support_status="CATALOG_ONLY", official_url="https://docs.mistral.ai/getting-started/quickstart/", credential_kind="API_KEY"),
    ProviderProfile("GROQ_API", "GroqCloud API", "groq", "groq_api", ["Windows", "macOS", "Linux"], "none", "api_key", [], integration_type="API", support_status="CATALOG_ONLY", official_url="https://console.groq.com/docs/quickstart", credential_kind="API_KEY"),
    ProviderProfile("OPENROUTER_GATEWAY", "OpenRouter", "openrouter", "openrouter_gateway", ["Windows", "macOS", "Linux"], "none", "api_key", [], integration_type="GATEWAY", support_status="CATALOG_ONLY", official_url="https://openrouter.ai/docs/quickstart", credential_kind="API_KEY"),
    ProviderProfile("AWS_BEDROCK", "Amazon Bedrock", "amazon", "bedrock_gateway", ["Windows", "macOS", "Linux"], "aws_cli_optional", "aws_credentials", [], integration_type="GATEWAY", support_status="CATALOG_ONLY", official_url="https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html", credential_kind="EXTERNAL_PROFILE"),
    ProviderProfile("VERTEX_AI", "Google Vertex AI", "google", "vertex_gateway", ["Windows", "macOS", "Linux"], "gcloud_optional", "application_default_credentials", [], integration_type="GATEWAY", support_status="CATALOG_ONLY", official_url="https://cloud.google.com/vertex-ai/generative-ai/docs/start/quickstarts/quickstart-multimodal", credential_kind="EXTERNAL_PROFILE"),
    ProviderProfile("GITHUB_MODELS_API", "GitHub Models API", "github", "github_models_api", ["Windows", "macOS", "Linux"], "none", "token", [], integration_type="API", support_status="CATALOG_ONLY", official_url="https://docs.github.com/en/github-models", credential_kind="API_KEY"),
    ProviderProfile("CEREBRAS_API", "Cerebras Inference API", "cerebras", "cerebras_api", ["Windows", "macOS", "Linux"], "none", "api_key", [], integration_type="API", support_status="CATALOG_ONLY", official_url="https://inference-docs.cerebras.ai/", credential_kind="API_KEY"),
    ProviderProfile("COHERE_API", "Cohere API", "cohere", "cohere_api", ["Windows", "macOS", "Linux"], "none", "api_key", [], integration_type="API", support_status="CATALOG_ONLY", official_url="https://docs.cohere.com/docs/quickstart", credential_kind="API_KEY"),
    ProviderProfile("TOGETHER_API", "Together AI API", "together", "together_api", ["Windows", "macOS", "Linux"], "none", "api_key", [], integration_type="API", support_status="CATALOG_ONLY", official_url="https://docs.together.ai/docs/quickstart", credential_kind="API_KEY"),
    ProviderProfile("OLLAMA_LOCAL", "Ollama", "ollama", "ollama_local", ["Windows", "macOS", "Linux"], "official_installer", "none", ["ollama", "ollama.exe"], integration_type="LOCAL_RUNTIME", support_status="CATALOG_ONLY", official_url="https://docs.ollama.com/", capability_matrix={"chat": "ADAPTER_REQUIRED", "local_execution": "AVAILABLE"}),
    ProviderProfile("LM_STUDIO_LOCAL", "LM Studio", "lmstudio", "lm_studio_local", ["Windows", "macOS", "Linux"], "official_installer", "none", [], integration_type="LOCAL_RUNTIME", support_status="CATALOG_ONLY", official_url="https://lmstudio.ai/docs/"),
    ProviderProfile("LLAMA_CPP_LOCAL", "llama.cpp", "ggml", "llama_cpp_local", ["Windows", "macOS", "Linux"], "official_release", "none", ["llama-cli", "llama-server"], integration_type="LOCAL_RUNTIME", support_status="CATALOG_ONLY", official_url="https://github.com/ggml-org/llama.cpp"),
    ProviderProfile("VLLM_LOCAL", "vLLM", "vllm", "vllm_local", ["Linux"], "python_package", "none", ["vllm"], integration_type="LOCAL_RUNTIME", support_status="CATALOG_ONLY", official_url="https://docs.vllm.ai/en/latest/getting_started/quickstart.html"),
    ProviderProfile("LOCALAI_RUNTIME", "LocalAI", "localai", "localai_runtime", ["Windows", "macOS", "Linux"], "container_or_binary", "none", [], integration_type="LOCAL_RUNTIME", support_status="CATALOG_ONLY", official_url="https://localai.io/basics/getting_started/"),
    ProviderProfile("NVIDIA_NIM_API", "NVIDIA NIM API", "nvidia", "nvidia_nim_api", ["Windows", "macOS", "Linux"], "none", "api_key", [], integration_type="API", support_status="CATALOG_ONLY", official_url="https://docs.api.nvidia.com/nim/", credential_kind="API_KEY"),
]
