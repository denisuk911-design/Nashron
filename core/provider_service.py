from __future__ import annotations

import shutil
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Protocol

from .database import Database
from .provider_execution import ProviderCapabilityProfile, ProviderExecutionRequest, ProviderExecutionResult
from .provider_models import DEFAULT_PROVIDER_PROFILES, ProviderHealth, ProviderProfile
from .provider_credentials import ProviderCredentialService


class ProviderAdapter(Protocol):
    provider_id: str
    adapter_schema_version: str

    def check_health(self) -> ProviderHealth:
        ...


class CodexProviderAdapter:
    provider_id = "CODEX_CLI"
    adapter_schema_version = "1.0"
    capability_profile = ProviderCapabilityProfile(
        provider_id, capabilities=frozenset({"chat", "filesystem.write", "structured_output", "streaming", "cancellation"}),
        supports_native_tools=True, supports_native_structured_output=False, supports_streaming=True,
    )

    def __init__(self, codex_client) -> None:
        self.codex_client = codex_client
        self._execution_lock = threading.Lock()

    def check_health(self) -> ProviderHealth:
        if not self.codex_client.is_available():
            return ProviderHealth(
                self.provider_id,
                None,
                "NOT_INSTALLED",
                "AUTHENTICATION_REQUIRED",
                "NOT_CHECKED",
                "NOT_READY",
                "NOT_CHECKED",
                diagnostic="Codex executable not found.",
            )
        version = self.codex_client.version()
        try:
            auth = self.codex_client.login_status()
            authenticated = bool(auth.authorized)
            auth_status = "AUTHENTICATED" if authenticated else "AUTHENTICATION_REQUIRED"
            health = "READY" if authenticated else "NOT_READY"
            access = "ACCESS_AVAILABLE" if authenticated else "NOT_CHECKED"
            capability = "SUPPORTED" if authenticated else "NOT_CHECKED"
            diagnostic = auth.message
        except Exception as exc:
            auth_status = "UNKNOWN"
            health = "UNKNOWN"
            access = "UNKNOWN"
            capability = "UNKNOWN"
            diagnostic = str(exc)
        return ProviderHealth(
            self.provider_id,
            version,
            "INSTALLED",
            auth_status,
            access,
            health,
            capability,
            diagnostic=diagnostic,
        )

    def execute(self, request: ProviderExecutionRequest) -> ProviderExecutionResult:
        # The client owns mutable process/output state; serialize one CLI.
        with self._execution_lock:
            result = self.codex_client.generate(request.prompt, allow_full_access=False, on_delta=request.on_delta)
        finished_at = datetime.now(timezone.utc).isoformat()
        return ProviderExecutionResult(
            request.run_id,
            request.employee_id,
            self.provider_id,
            request.work_item_id,
            "SUCCEEDED" if result.ok else "FAILED",
            request.started_at,
            finished_at,
            content=result.content if result.ok else "",
            error=str(result.error or "") if not result.ok else "",
        )

    def cancel(self) -> None:
        self.codex_client.cancel()


class GeminiProviderAdapter:
    provider_id = "GEMINI_CLI"
    adapter_schema_version = "1.0"
    capability_profile = ProviderCapabilityProfile(
        provider_id, model_id="gemini-3.1-flash-lite",
        capabilities=frozenset({"chat", "filesystem.write", "structured_output", "cancellation"}),
        supports_native_tools=True, supports_native_structured_output=True,
    )

    def __init__(self, gemini_client) -> None:
        self.gemini_client = gemini_client
        self._execution_lock = threading.Lock()

    def check_health(self) -> ProviderHealth:
        if not self.gemini_client.is_available():
            return ProviderHealth(
                self.provider_id,
                None,
                "NOT_INSTALLED",
                "AUTHENTICATION_REQUIRED",
                "NOT_CHECKED",
                "NOT_READY",
                "NOT_CHECKED",
                diagnostic="Gemini executable not found.",
            )
        version = self.gemini_client.version()
        authenticated = self.gemini_client.has_api_key()
        return ProviderHealth(
            self.provider_id,
            version,
            "INSTALLED",
            "AUTHENTICATED" if authenticated else "AUTHENTICATION_REQUIRED",
            "ACCESS_AVAILABLE" if authenticated else "NOT_CHECKED",
            "READY" if authenticated else "NOT_READY",
            "SUPPORTED" if authenticated else "NOT_CHECKED",
            diagnostic="Credential configured." if authenticated else "Credential is not configured.",
        )

    def execute(self, request: ProviderExecutionRequest) -> ProviderExecutionResult:
        # The client owns a mutable current-process reference.
        with self._execution_lock:
            result = self.gemini_client.generate(request.prompt, allow_full_access=False, on_delta=request.on_delta)
        finished_at = datetime.now(timezone.utc).isoformat()
        return ProviderExecutionResult(
            request.run_id,
            request.employee_id,
            self.provider_id,
            request.work_item_id,
            "SUCCEEDED" if result.ok else "FAILED",
            request.started_at,
            finished_at,
            content=result.content if result.ok else "",
            error=str(result.error or "") if not result.ok else "",
        )

    def cancel(self) -> None:
        self.gemini_client.cancel()


class MissingProviderAdapter:
    def __init__(self, profile: ProviderProfile) -> None:
        self.profile = profile
        self.provider_id = profile.provider_id

    def check_health(self) -> ProviderHealth:
        if self.profile.integration_type == "API" and self.profile.credential_kind in {"API_KEY", "OPTIONAL_API_KEY"}:
            try:
                from .secure_storage import WindowsCredentialStore

                configured = bool(WindowsCredentialStore().read(self.profile.provider_id))
            except Exception:
                configured = False
            return ProviderHealth(
                self.provider_id,
                None,
                "INSTALLED",
                "AUTHENTICATED" if configured else "AUTHENTICATION_REQUIRED",
                "NOT_CHECKED",
                "DEGRADED" if configured else "NOT_READY",
                "UNSUPPORTED",
                diagnostic=(
                    "API credential is stored securely; the execution adapter is not implemented."
                    if configured
                    else "API credential is not configured and the execution adapter is not implemented."
                ),
            )
        found = next((name for name in self.profile.executable_names if shutil.which(name)), None)
        return ProviderHealth(
            self.provider_id,
            None,
            "DETECTED" if found else "NOT_INSTALLED",
            "NOT_AUTHENTICATED",
            "NOT_CHECKED",
            "NOT_READY",
            "UNKNOWN",
            diagnostic="Adapter is not implemented in this phase.",
        )


class ProviderRegistry:
    def __init__(self, database: Database) -> None:
        self.database = database

    def ensure_defaults(self) -> None:
        for profile in DEFAULT_PROVIDER_PROFILES:
            self.database.upsert_provider_definition(profile)

    def profiles(self) -> list[ProviderProfile]:
        rows = self.database.list_provider_definitions()
        return [
            ProviderProfile(
                provider_id=row["provider_id"],
                display_name=row["display_name"],
                provider_family=row["provider_family"],
                adapter_id=row["adapter_id"],
                supported_os=self.database.loads(row["supported_os"], []),
                installation_strategy=row["installation_strategy"],
                authentication_strategy=row["authentication_strategy"],
                executable_names=self.database.loads(row["executable_names"], []),
                minimum_supported_version=row["minimum_supported_version"],
                recommended_version=row["recommended_version"],
                setup_instructions=row["setup_instructions"] or "",
                known_limitations=self.database.loads(row["known_limitations"], []),
                required_capabilities=self.database.loads(row["required_capabilities"], []),
                integration_type=str(row["integration_type"] or "CLI"),
                support_status=str(row["support_status"] or "CATALOG_ONLY"),
                official_url=str(row["official_url"] or ""),
                install_command=self.database.loads(row["install_command"], []),
                auth_command=self.database.loads(row["auth_command"], []),
                update_command=self.database.loads(row["update_command"], []),
                uninstall_command=self.database.loads(row["uninstall_command"], []),
                capability_matrix=self.database.loads(row["capability_matrix"], {}),
                credential_kind=str(row["credential_kind"] or "NONE"),
                catalog_class=str(row["catalog_class"] or "UNSUPPORTED"),
                last_verified=str(row["last_verified"] or ""),
                provider_schema_version=row["provider_schema_version"],
            )
            for row in rows
        ]

    def get(self, provider_id: str) -> ProviderProfile | None:
        return next((profile for profile in self.profiles() if profile.provider_id == provider_id), None)


class ProviderHealthService:
    def __init__(self, database: Database, registry: ProviderRegistry, adapters: dict[str, ProviderAdapter]) -> None:
        self.database = database
        self.registry = registry
        self.adapters = adapters

    def check_provider(self, provider_id: str) -> ProviderHealth:
        profile = self.registry.get(provider_id)
        adapter = self.adapters.get(provider_id)
        if adapter is None and profile is not None:
            adapter = MissingProviderAdapter(profile)
        if adapter is None:
            health = ProviderHealth(provider_id, None, "UNSUPPORTED", "NOT_AUTHENTICATED", "UNKNOWN", "BLOCKED", "UNKNOWN", diagnostic="Unknown provider.")
        else:
            health = adapter.check_health()
        self.database.record_provider_health_check(health)
        return health

    def check_all(self) -> list[ProviderHealth]:
        return [self.check_provider(profile.provider_id) for profile in self.registry.profiles()]

    def latest_health(self, provider_id: str) -> ProviderHealth | None:
        row = self.database.get_latest_provider_health(provider_id)
        if row is None:
            return None
        return ProviderHealth(
            provider_id=row["provider_id"],
            detected_version=row["detected_version"],
            installation_status=row["installation_status"],
            authentication_status=row["authentication_status"],
            access_status=row["access_status"],
            health_status=row["health_status"],
            capability_status=row["capability_status"],
            account_label=row["account_label"],
            diagnostic=row["diagnostic"] or "",
        )

    def discover_capabilities(self, provider_id: str) -> dict[str, object] | None:
        """Persist the adapter-declared execution contract as auditable evidence."""
        adapter = self.adapters.get(provider_id)
        profile = getattr(adapter, "capability_profile", None) if adapter is not None else None
        if profile is None:
            return None
        capabilities = sorted(profile.capabilities)
        evidence = {
            "source": "adapter_capability_profile",
            "adapter_schema_version": str(getattr(adapter, "adapter_schema_version", "1.0")),
            "model_id": profile.model_id,
            "native_tools": profile.supports_native_tools,
            "native_structured_output": profile.supports_native_structured_output,
            "streaming": profile.supports_streaming,
            "cancellation": profile.supports_cancellation,
        }
        profile_id = self.database.record_provider_capabilities(provider_id, capabilities, "SUPPORTED", evidence)
        return {"capability_profile_id": profile_id, "capabilities": capabilities, "evidence": evidence}


class ProviderProvisioningService:
    """Phase 2A.1 coordinator: detection/readiness only, no installation execution."""

    def __init__(
        self,
        database: Database,
        registry: ProviderRegistry,
        health_service: ProviderHealthService,
        credential_service: ProviderCredentialService | None = None,
    ) -> None:
        self.database = database
        self.registry = registry
        self.health_service = health_service
        self.credentials = credential_service or ProviderCredentialService(database)

    def ensure_assignments_for_existing_agents(self) -> None:
        supported_provider_ids = {profile.provider_id for profile in self.registry.profiles()}
        for profile in self.database.list_agent_profiles():
            agent_id = str(profile["agent_id"])
            provider_id = str(profile["provider_id"] or "").strip()
            # UNAVAILABLE and similar legacy values describe provisioning
            # state; they are not provider definitions and cannot satisfy the
            # provider assignment foreign key.
            if agent_id and provider_id in supported_provider_ids:
                self.database.upsert_agent_provider_assignment(agent_id, provider_id, "DRAFT")

    def readiness_for_employee(self, agent_id: str) -> str:
        profile = self.database.get_agent_profile(agent_id)
        if profile is None:
            return "PROFILE_INCOMPLETE"
        if str(profile["lifecycle_state"]) in ("SUSPENDED", "DISABLED", "ARCHIVED"):
            return "BLOCKED"
        provider_id = str(profile["provider_id"] or "")
        if not provider_id or self.registry.get(provider_id) is None:
            return "PROVIDER_NOT_ASSIGNED"
        health = self.health_service.latest_health(provider_id) or self.health_service.check_provider(provider_id)
        if health.installation_status in ("NOT_INSTALLED", "UNSUPPORTED"):
            return "PROVIDER_NOT_INSTALLED"
        if health.authentication_status not in ("AUTHENTICATED",):
            return "AUTHENTICATION_REQUIRED"
        if health.access_status in ("PLAN_INCOMPATIBLE", "BILLING_REQUIRED", "PROVIDER_REJECTED"):
            return "PLAN_INCOMPATIBLE"
        if health.access_status in ("NOT_CHECKED", "UNKNOWN"):
            return "ACCESS_CHECK_REQUIRED"
        if health.capability_status in ("NOT_CHECKED", "UNKNOWN"):
            return "CAPABILITY_TEST_REQUIRED"
        if health.health_status == "READY":
            return "READY"
        if health.health_status == "DEGRADED":
            return "DEGRADED"
        return "BLOCKED"

    def create_session(self, target_employee_draft: dict, provider_id: str, current_step: str) -> str:
        return self.database.create_provisioning_session(
            target_employee_draft=target_employee_draft,
            provider_id=provider_id,
            current_step=current_step,
            install_plan_hash=None,
            recoverable=True,
            started_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )


def provider_profile_to_json(profile: ProviderProfile) -> dict:
    return asdict(profile)
