import pytest

from core.config_repository import ConfigurationRepository
from core.database import Database
from core.director_service import DirectorService
from core.management_service import ManagementService
from core.universal_platform_service import UniversalPlatformService


def _team(tmp_path, template_name="SOFTWARE_PRODUCT_TEAM"):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    management = ManagementService(database, ConfigurationRepository(tmp_path / "management"))
    management.ensure_foundations()
    universal = UniversalPlatformService(database, management_service=management)
    universal.seed_management_library()
    template = next(item for item in universal.list_templates() if item.name == template_name)
    activation = universal.activate_template(template.template_id, "Product team", team_size="STANDARD")
    return database, activation.organization.organization_id


def test_director_creates_persisted_specialist_and_review_assignments(tmp_path):
    database, organization_id = _team(tmp_path)
    service = DirectorService(database)

    plan = service.create_plan(organization_id, "Создать небольшой менеджер заметок")

    assert plan.director_agent_id
    assert plan.assignments
    assert all(item.agent_id != plan.director_agent_id for item in plan.assignments)
    assert any(item.role_id == "QA_ENGINEER" for item in plan.assignments)
    assert any(item.review_required for item in plan.assignments if item.role_id != "QA_ENGINEER")
    assert plan.status == "READY"
    assert service.get_plan(plan.plan_id) == plan


def test_director_reports_missing_staff_instead_of_doing_everything(tmp_path):
    database, organization_id = _team(tmp_path)
    service = DirectorService(database)
    with database.connect() as conn:
        conn.execute(
            "UPDATE organization_members SET status = 'ARCHIVED' WHERE organization_id = ? AND role_id != 'PROJECT_MANAGER'",
            (organization_id,),
        )

    plan = service.create_plan(organization_id, "Подготовить проект")

    assert plan.status == "NEEDS_STAFFING"
    assert "SPECIALIST" in plan.missing_roles
    assert plan.assignments == ()


def test_director_requires_owner_for_installation_or_destructive_goal(tmp_path):
    _database, organization_id = _team(tmp_path)
    service = DirectorService(_database)

    plan = service.create_plan(organization_id, "Установить платную программу и удалить старые данные")

    assert plan.owner_approval_required is True
    assert plan.status == "AWAITING_OWNER_APPROVAL"


def test_plan_requires_explicit_director_assignment(tmp_path):
    database, organization_id = _team(tmp_path)
    with database.connect() as conn:
        conn.execute(
            "UPDATE organization_members SET role_id = 'CUSTOM_ROLE' WHERE organization_id = ? AND role_id = 'PROJECT_MANAGER'",
            (organization_id,),
        )

    with pytest.raises(ValueError, match="director_not_assigned"):
        DirectorService(database).create_plan(organization_id, "Сделать продукт")
