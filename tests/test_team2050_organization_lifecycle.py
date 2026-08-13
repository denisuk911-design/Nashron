from core.agent_directory import list_chat_agents
from core.config_repository import ConfigurationRepository
from core.database import Database
from core.management_models import AgentProfile
from core.management_service import ManagementService
from core.universal_platform_service import UniversalPlatformService


def test_each_organization_gets_an_isolated_conversation(tmp_path):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    service = UniversalPlatformService(database)

    first = service.create_organization("Alpha Team")
    second = service.create_organization("Beta Team")
    first_conversation = database.ensure_organization_conversation(first.organization_id)
    second_conversation = database.ensure_organization_conversation(second.organization_id)

    assert first_conversation != second_conversation
    database.add_message(first_conversation, "user", "Alpha-only context")
    assert [item.content for item in database.list_messages(second_conversation)] == []


def test_shared_legacy_workspace_conversations_are_split(tmp_path):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    shared = database.create_conversation("Legacy chat")
    first = database.create_organization({"id": "ORG-A", "name": "Alpha"})
    second = database.create_organization({"id": "ORG-B", "name": "Beta"})
    for organization_id in (first, second):
        database.create_organization_workspace({"organization_id": organization_id, "conversation_id": shared})

    database.ensure_organization_conversations()
    first_conversation = int(database.get_organization_workspace(first)["conversation_id"])
    second_conversation = int(database.get_organization_workspace(second)["conversation_id"])

    assert first_conversation == shared
    assert second_conversation != shared
    assert second_conversation != first_conversation


def test_organization_members_are_the_only_routable_agents(tmp_path):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    management = ManagementService(database, ConfigurationRepository(tmp_path / "management"))
    management.ensure_foundations()
    service = UniversalPlatformService(database, management_service=management)
    alpha = service.create_organization("Alpha Team")
    beta = service.create_organization("Beta Team")

    for agent_id, name in (("agent-alpha", "Alpha worker"), ("agent-beta", "Beta worker")):
        management.create_agent(
            AgentProfile(agent_id, name, "worker", "ACTIVE", "CODEX_CLI"),
            ["DESIGN_ENGINEER"],
            ["CHAT"],
            reason="test",
        )
    database.create_organization_member({"organization_id": alpha.organization_id, "agent_id": "agent-alpha", "position": "Alpha"})
    database.create_organization_member({"organization_id": beta.organization_id, "agent_id": "agent-beta", "position": "Beta"})

    assert {agent.key for agent in list_chat_agents(database, organization_id=alpha.organization_id)} == {"alpha"}
    assert {agent.key for agent in list_chat_agents(database, organization_id=beta.organization_id)} == {"beta"}


def test_archive_restore_and_delete_empty_organization(tmp_path):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    service = UniversalPlatformService(database)
    organization = service.create_organization("Temporary Team")
    conversation_id = database.ensure_organization_conversation(organization.organization_id)
    database.add_message(conversation_id, "user", "Temporary context")

    service.archive_organization(organization.organization_id)
    assert database.list_organizations("ARCHIVED")[0]["id"] == organization.organization_id
    service.restore_organization(organization.organization_id)
    assert database.list_organizations("ACTIVE")[0]["id"] == organization.organization_id
    service.delete_organization(organization.organization_id)
    assert not database.list_organizations()
    assert not database.list_messages(conversation_id)
    assert all(item.id != conversation_id for item in database.list_conversations())
    with database.connect() as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
