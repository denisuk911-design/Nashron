from core.config_repository import ConfigurationRepository
from core.database import Database
from core.management_models import AgentProfile, OWNER_ROLE
from core.management_service import ManagementService
from core.models import CodexResult
from core.provider_result import normalize_provider_result


def _service(tmp_path, *, seed_legacy=False):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    service = ManagementService(database, ConfigurationRepository(tmp_path / "management"))
    service.ensure_foundations(seed_legacy=seed_legacy)
    return database, service


def test_clean_foundations_do_not_create_organization_or_employee(tmp_path):
    database, service = _service(tmp_path)

    assert database.list_organizations() == []
    assert database.list_agent_profiles() == []
    assert database.list_professions() == []
    assert service.list_roles()


def test_hard_delete_preserves_shared_history_with_deleted_author(tmp_path):
    database, service = _service(tmp_path)
    profile = AgentProfile(
        agent_id=service.generate_agent_id("Temporary reviewer"),
        display_name="Temporary reviewer",
        description="test",
        lifecycle_state="ACTIVE",
        provider_id="CODEX_CLI",
    )
    service.create_agent(profile, ["DOCUMENT_CONTROL_OFFICER"], ["CHAT"])
    conversation_id = database.create_conversation("history")
    database.add_message(conversation_id, profile.agent_id.removeprefix("agent-"), "Проверка завершена")

    service.delete_agent(profile.agent_id, OWNER_ROLE, confirmed=True)

    assert database.get_agent_profile(profile.agent_id) is None
    history = database.list_messages(conversation_id)
    assert history[0].role.startswith("deleted:")
    assert "Temporary reviewer" in history[0].role


def test_provider_none_is_normalized_to_failure_result():
    result = normalize_provider_result(None)

    assert isinstance(result, CodexResult)
    assert result.ok is False
    assert result.returncode is None
    assert result.error == "provider_returned_none"
