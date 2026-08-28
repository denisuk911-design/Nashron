from core.communication_style_service import CommunicationStyle
from core.config_repository import ConfigurationRepository
from core.database import Database
from core.management_service import ManagementService
from core.provider_hub_service import ProviderHubService
from core.provider_models import ProviderHealth
from core.provider_service import ProviderHealthService, ProviderRegistry
from runtime_v2.feature_flag import RuntimeEngine, selected_runtime


class ReadyAdapter:
    provider_id = "CODEX_CLI"

    def check_health(self):
        return ProviderHealth("CODEX_CLI", "1", "INSTALLED", "AUTHENTICATED", "ACCESS_AVAILABLE", "READY", "SUPPORTED")


def test_packaged_goal_runtime_is_not_gated_by_developer_setting():
    assert selected_runtime({"developer_mode": False, "runtime_engine": "HYBRID_V3_EXPERIMENTAL"}) is RuntimeEngine.HYBRID_V3_EXPERIMENTAL
    assert selected_runtime({"developer_mode": False, "runtime_engine": "V2_EXPERIMENTAL"}) is RuntimeEngine.LEGACY


def test_communication_style_normalizes_untrusted_employee_profile():
    style = CommunicationStyle.from_profile({"directness": 99, "humor": -2, "explanation_style": "wrong"})

    assert style.directness == 5
    assert style.humor == 0
    assert style.explanation_style == "short"
    assert "directness 5/5" in style.prompt_directive("Alex")
    assert "Social mode" in style.directive_for_mode("SOCIAL")
    assert "Work mode" in style.directive_for_mode("WORK")


def test_communication_style_matches_register_without_mirroring_profanity():
    style = CommunicationStyle()

    assert "formal register" in style.directive_for_user_message("Пожалуйста, проверьте файл", "SOCIAL")
    assert "do not mirror profanity" in style.directive_for_user_message("Что за хуйня?", "SOCIAL")
    assert "neutral everyday register" in style.directive_for_user_message("Привет", "SOCIAL")


def test_provider_hub_exposes_sanitized_product_status(tmp_path):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    ManagementService(database, ConfigurationRepository(tmp_path / "management")).ensure_foundations()
    registry = ProviderRegistry(database)
    registry.ensure_defaults()
    health = ProviderHealthService(database, registry, {"CODEX_CLI": ReadyAdapter()})

    entries = ProviderHubService(registry, health).entries(refresh=True)
    codex = next(entry for entry in entries if entry.provider_id == "CODEX_CLI")

    assert codex.ready
    assert codex.status == "Ready"
    assert codex.detail == ""


def test_provider_hub_maps_operational_states_and_hides_diagnostics(tmp_path):
    class Adapter:
        provider_id = "CODEX_CLI"
        def check_health(self):
            return ProviderHealth("CODEX_CLI", "1", "INSTALLED", "AUTHENTICATION_REQUIRED", "NOT_CHECKED", "NOT_READY", "UNKNOWN", diagnostic="secret-like trace")

    database = Database(tmp_path / "team.sqlite3"); database.initialize()
    ManagementService(database, ConfigurationRepository(tmp_path / "management")).ensure_foundations()
    registry = ProviderRegistry(database); registry.ensure_defaults()
    health = ProviderHealthService(database, registry, {"CODEX_CLI": Adapter()})
    product = next(item for item in ProviderHubService(registry, health).entries(refresh=True) if item.provider_id == "CODEX_CLI")
    developer = next(item for item in ProviderHubService(registry, health, developer_mode=True).entries() if item.provider_id == "CODEX_CLI")

    assert product.status == "Login needed" and product.detail == ""
    assert developer.detail == "[REDACTED]-like trace"
