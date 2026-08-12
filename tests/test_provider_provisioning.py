from core.config_repository import ConfigurationRepository
from core.database import Database
from core.management_models import AgentProfile, OWNER_ROLE
from core.management_service import ManagementService
from core.provider_models import ProviderHealth
from core.provider_service import ProviderHealthService, ProviderProvisioningService, ProviderRegistry


class ReadyAdapter:
    provider_id = "CODEX_CLI"

    def check_health(self):
        return ProviderHealth(
            provider_id="CODEX_CLI",
            detected_version="codex 1.0",
            installation_status="INSTALLED",
            authentication_status="AUTHENTICATED",
            access_status="ACCESS_AVAILABLE",
            health_status="READY",
            capability_status="SUPPORTED",
            diagnostic="ok",
        )


class AuthRequiredAdapter:
    provider_id = "GEMINI_CLI"

    def check_health(self):
        return ProviderHealth(
            provider_id="GEMINI_CLI",
            detected_version="gemini 1.0",
            installation_status="INSTALLED",
            authentication_status="AUTHENTICATION_REQUIRED",
            access_status="NOT_CHECKED",
            health_status="NOT_READY",
            capability_status="NOT_CHECKED",
            diagnostic="token api_key secret GEMINI_API_KEY",
        )


def make_services(tmp_path, adapters=None):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    management = ManagementService(db, ConfigurationRepository(tmp_path / "management"))
    management.ensure_foundations()
    for profile, role in (
        (AgentProfile("agent-codex-fixture", "Codex Employee", "test", "ACTIVE", "CODEX_CLI"), "CUSTOM_ROLE"),
        (AgentProfile("agent-gemini-fixture", "Gemini Employee", "test", "ACTIVE", "GEMINI_CLI"), "CUSTOM_ROLE"),
    ):
        management.create_agent(profile, [role], ["CHAT"])
    registry = ProviderRegistry(db)
    registry.ensure_defaults()
    health = ProviderHealthService(db, registry, adapters or {})
    provisioning = ProviderProvisioningService(db, registry, health)
    provisioning.ensure_assignments_for_existing_agents()
    return db, registry, health, provisioning


def test_provider_registry_seeds_codex_gemini_and_claude(tmp_path):
    _db, registry, _health, _provisioning = make_services(tmp_path)

    provider_ids = {profile.provider_id for profile in registry.profiles()}

    assert {"CODEX_CLI", "GEMINI_CLI", "CLAUDE_CLI"} <= provider_ids


def test_existing_agents_get_provider_assignments(tmp_path):
    db, _registry, _health, _provisioning = make_services(tmp_path)

    codex = db.list_agent_provider_assignments("agent-codex-fixture")
    gemini = db.list_agent_provider_assignments("agent-gemini-fixture")

    assert codex[0]["provider_id"] == "CODEX_CLI"
    assert gemini[0]["provider_id"] == "GEMINI_CLI"


def test_unassigned_legacy_employee_does_not_break_provider_bootstrap(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    management = ManagementService(db, ConfigurationRepository(tmp_path / "management"))
    management.ensure_foundations()
    db.create_agent_profile(
        AgentProfile(
            agent_id="agent-unassigned",
            display_name="Новый сотрудник",
            description="Профиль ожидает выбора ИИ-движка.",
            lifecycle_state="ACTIVE",
            provider_id="UNAVAILABLE",
            persona_id=None,
            avatar_path=None,
            aliases=(),
        ),
        actor=OWNER_ROLE,
        reason="legacy fixture",
    )
    registry = ProviderRegistry(db)
    registry.ensure_defaults()
    health = ProviderHealthService(db, registry, {})
    provisioning = ProviderProvisioningService(db, registry, health)

    provisioning.ensure_assignments_for_existing_agents()

    assert db.list_agent_provider_assignments("agent-unassigned") == []
    assert provisioning.readiness_for_employee("agent-unassigned") == "PROVIDER_NOT_ASSIGNED"


def test_ready_provider_makes_active_employee_ready(tmp_path):
    _db, _registry, health, provisioning = make_services(tmp_path, {"CODEX_CLI": ReadyAdapter()})
    health.check_provider("CODEX_CLI")

    assert provisioning.readiness_for_employee("agent-codex-fixture") == "READY"


def test_auth_required_provider_blocks_readiness(tmp_path):
    db, _registry, health, provisioning = make_services(tmp_path, {"GEMINI_CLI": AuthRequiredAdapter()})
    health.check_provider("GEMINI_CLI")

    assert provisioning.readiness_for_employee("agent-gemini-fixture") == "AUTHENTICATION_REQUIRED"
    diagnostic = db.get_latest_provider_health("GEMINI_CLI")["diagnostic"]
    assert "api_key" not in diagnostic
    assert "GEMINI_API_KEY" not in diagnostic


def test_missing_claude_is_not_marked_ready(tmp_path):
    _db, _registry, health, _provisioning = make_services(tmp_path)

    result = health.check_provider("CLAUDE_CLI")

    assert result.health_status == "NOT_READY"
    assert result.capability_status == "UNKNOWN"


def test_provisioning_session_is_recoverable(tmp_path):
    db, _registry, _health, provisioning = make_services(tmp_path)

    session_id = provisioning.create_session({"display_name": "Claude learner"}, "CLAUDE_CLI", "detect_provider")

    with db.connect() as conn:
        row = conn.execute("SELECT * FROM provisioning_sessions WHERE provisioning_session_id = ?", (session_id,)).fetchone()
    assert row["recoverable"] == 1
    assert row["selected_provider"] == "CLAUDE_CLI"
