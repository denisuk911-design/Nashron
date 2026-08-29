from core.database import Database
from core.management_models import AgentProfile
from core.universal_platform_service import UniversalPlatformService


def test_u1_creates_profession_organization_template_and_instances(tmp_path):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    service = UniversalPlatformService(database)

    profession = service.create_profession(
        "Specialist по восстановлению мотоциклов",
        "Восстанавливает старые мотоциклы.",
        responsibilities=["осмотр", "ремонт"],
        required_capabilities=["FILE_READ"],
    )
    assert profession.name.startswith("Specialist")

    workflow = service.create_workflow(
        "Generic two-step workflow",
        [
            {"responsibility": "Creator", "operation": "CREATE", "expected_outputs": ["artifact"]},
            {"responsibility": "Reviewer", "operation": "REVIEW", "expected_outputs": ["findings"]},
        ],
    )
    template = service.create_template(
        "Custom Workshop",
        "User-created organization",
        [{"profession_id": profession.profession_id, "role": "Creator", "position": "Lead"}],
        workflow.workflow_id,
    )
    organization = service.instantiate_template(template.template_id, "My Workshop")

    assert organization.name == "My Workshop"
    members = database.list_organization_members(organization.organization_id)
    assert len(members) == 1
    assert members[0]["profession_id"] == profession.profession_id


def test_u1_fixtures_share_generic_core(tmp_path):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    service = UniversalPlatformService(database)
    service.seed_demo_fixtures()

    templates = {item.name: item for item in service.list_templates()}
    assert "SOFTWARE_PRODUCT_TEAM" in templates
    assert "CULINARY_PRODUCT_TEAM" in templates
    assert templates["SOFTWARE_PRODUCT_TEAM"].workflow_id
    assert templates["CULINARY_PRODUCT_TEAM"].workflow_id
    assert len(service.list_professions()) >= 8
    assert len(database.list_workflows()) >= 2

    source = service.add_learning_source("Team handbook", "USER_INSTRUCTION", "chat://owner")
    assert source.processed_state == "NEW"
    database.create_agent_profile(
        AgentProfile("agent-roman", "Roman", "engineer", "ACTIVE", "CODEX_CLI"),
        actor="ORGANIZATION_OWNER",
        reason="test",
    )
    service.update_runtime_state("agent-roman", current_operation="CREATE", status="WORKING")
    assert database.get_agent_runtime_state("agent-roman")["status"] == "WORKING"


def test_u1_reassigns_membership_role_for_routing(tmp_path):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    service = UniversalPlatformService(database)
    organization = service.create_organization("Role reassignment")
    database.create_agent_profile(AgentProfile("agent-mira", "Mira", "", "ACTIVE", "UNAVAILABLE"), actor="owner", reason="test")
    database.create_organization_member({"organization_id": organization.organization_id, "agent_id": "agent-mira", "role_id": "CUSTOM_ROLE"})

    service.reassign_member_role(organization.organization_id, "agent-mira", "QA_ENGINEER")

    assert database.get_organization_member(organization.organization_id, "agent-mira")["role_id"] == "QA_ENGINEER"
