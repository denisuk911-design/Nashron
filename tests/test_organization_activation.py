from core.config_repository import ConfigurationRepository
from core.database import Database
from core.management_service import ManagementService
from core.agent_directory import list_chat_agents
from core.universal_platform_service import UniversalPlatformService


def test_template_activation_creates_workspace_members_and_employees(tmp_path):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    management = ManagementService(database, ConfigurationRepository(tmp_path / "management"))
    management.ensure_foundations()
    service = UniversalPlatformService(database, management_service=management, conversation_id=database.ensure_single_conversation())
    service.seed_demo_fixtures()

    template = next(item for item in service.list_templates() if item.name == "SOLO_PROFESSIONAL")
    activation = service.activate_template(
        template.template_id,
        "Внутренняя рабочая группа",
        team_size="MINI",
        provider_assignments={"Assistant": "CODEX_CLI", "Researcher": "GEMINI_CLI", "Reviewer": "UNAVAILABLE"},
    )

    members = database.list_organization_members(activation.organization.organization_id)
    assert activation.status == "READY_WITH_UNASSIGNED"
    assert len(members) == 3
    assert len(activation.employee_ids) == 3
    assert database.get_organization_workspace(activation.organization.organization_id)["status"] == "READY_WITH_UNASSIGNED"
    assert database.get_active_organization_id() == activation.organization.organization_id
    assert {agent.display_name for agent in list_chat_agents(database)} >= {"Assistant", "Researcher", "Reviewer"}


def test_management_library_is_data_driven_and_domain_neutral(tmp_path):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    service = UniversalPlatformService(database)
    service.seed_demo_fixtures()

    models = {item.name for item in service.list_management_models()}
    templates = {item.name for item in service.list_templates()}
    assert {"FUNCTIONAL", "PROJECTIZED", "MATRIX", "FLAT", "CROSS_FUNCTIONAL"} <= models
    assert {"SOFTWARE_PRODUCT_TEAM", "CULINARY_PRODUCT_TEAM", "DOCUMENT_PRODUCTION_TEAM"} <= templates
    assert len(templates) >= 21
