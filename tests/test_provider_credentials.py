from core.database import Database
from core.provider_credentials import ProviderCredentialService
from core.provider_service import GeminiProviderAdapter, ProviderHealthService, ProviderProvisioningService, ProviderRegistry


class MemoryCredentialStore:
    def __init__(self):
        self.values = {}

    def read(self, key):
        return self.values.get(key)

    def write(self, key, secret):
        self.values[key] = secret
        return f"Team2050/{key}"

    def delete(self, key):
        return self.values.pop(key, None) is not None


class GeminiClientStub:
    def is_available(self):
        return True

    def version(self):
        return "gemini 1.0"

    def has_api_key(self):
        return True


def test_secure_connection_can_be_removed_and_reconnected_without_database_secret(tmp_path):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    credentials = ProviderCredentialService(database, MemoryCredentialStore())

    reference = credentials.save("GEMINI_CLI", "secret-value")

    assert reference == "Team2050/GEMINI_CLI"
    assert credentials.read("GEMINI_CLI") == "secret-value"
    assert credentials.remove("GEMINI_CLI")
    assert not credentials.is_configured("GEMINI_CLI")
    with database.connect() as connection:
        event_details = [row[0] for row in connection.execute("SELECT detail FROM app_events")]
    assert "secret-value" not in str(event_details)


def test_gemini_cli_health_is_ready_with_real_adapter_contract(tmp_path):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    registry = ProviderRegistry(database)
    registry.ensure_defaults()
    adapter = GeminiProviderAdapter(GeminiClientStub())
    health = ProviderHealthService(database, registry, {"GEMINI_CLI": adapter})
    provisioning = ProviderProvisioningService(database, registry, health)

    result = health.check_provider("GEMINI_CLI")
    discovered = health.discover_capabilities("GEMINI_CLI")

    assert result.health_status == "READY"
    assert result.access_status == "ACCESS_AVAILABLE"
    assert result.capability_status == "SUPPORTED"
    assert discovered["evidence"]["adapter_schema_version"] == "1.0"
    assert provisioning.credentials is not None
