from core.database import Database
from core.provider_lifecycle_service import ProviderLifecycleService
from core.provider_models import DEFAULT_PROVIDER_PROFILES
from core.provider_service import ProviderRegistry


def test_provider_catalog_has_honest_product_scale(tmp_path):
    database = Database(tmp_path / "catalog.sqlite3")
    database.initialize()
    registry = ProviderRegistry(database)
    registry.ensure_defaults()

    profiles = registry.profiles()
    supported = {profile.provider_id for profile in profiles if profile.support_status == "SUPPORTED"}

    assert len(profiles) >= 20
    assert supported == {"CODEX_CLI", "GEMINI_CLI"}
    assert all(profile.official_url for profile in profiles)


def test_deepseek_is_api_only_without_fake_install_command():
    profile = next(item for item in DEFAULT_PROVIDER_PROFILES if item.provider_id == "DEEPSEEK_API")

    assert profile.integration_type == "API"
    assert profile.install_command == []
    assert profile.support_status == "CATALOG_ONLY"


def test_lifecycle_service_only_exposes_catalog_commands():
    codex = next(item for item in DEFAULT_PROVIDER_PROFILES if item.provider_id == "CODEX_CLI")

    assert ProviderLifecycleService.command_for(codex, "install") == ["npm", "install", "-g", "@openai/codex"]
