import os

from PySide6.QtWidgets import QApplication

from core.artifact_service import ArtifactService
from core.config_repository import ConfigurationRepository
from core.database import Database
from core.management_models import AgentProfile
from core.management_service import ManagementService
from core.provider_service import ProviderHealthService, ProviderProvisioningService, ProviderRegistry
from core.universal_platform_service import UniversalPlatformService
from gui.director_console import AddEmployeeWizard, DirectorConsoleDialog, EditEmployeeDialog, OrganizationActivationWizard


def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def make_service(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    service = ManagementService(db, ConfigurationRepository(tmp_path / "management"))
    service.ensure_foundations()
    registry = ProviderRegistry(db)
    registry.ensure_defaults()
    health = ProviderHealthService(db, registry, {})
    provisioning = ProviderProvisioningService(db, registry, health)
    provisioning.ensure_assignments_for_existing_agents()
    return service, registry, health, provisioning


def test_director_console_renders_clean_employee_list(tmp_path):
    qapp()
    service, registry, health, provisioning = make_service(tmp_path)

    dialog = DirectorConsoleDialog(service, registry, health, provisioning)

    assert dialog.tabs.count() == 16
    assert dialog.tabs.tabText(1) == "Проверка RC"
    assert dialog.tabs.tabText(2) == "Организация"
    assert "Supervisor" in [dialog.tabs.tabText(index) for index in range(dialog.tabs.count())]
    assert dialog.employee_tab.table.rowCount() == 0
    assert dialog.learning_tab.experience_table.rowCount() == 0
    assert dialog.learning_tab.queue_table.rowCount() == 0
    assert dialog.director_plans_tab.table.rowCount() == 0


def test_director_console_renders_artifact_registry(tmp_path):
    qapp()
    service, registry, health, provisioning = make_service(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    service.database.ensure_project("project-default", "Default Project")
    task_id = service.database.create_task("project-default", "Artifact task", None, "1.0")
    service.database.upsert_artifact(
        task_id=task_id,
        project_id="project-default",
        relative_path="Documents/missing.md",
        status="MISSING",
        validation_status="NOT_FOUND",
    )
    service.database.create_finding(
        task_id=task_id,
        description="Missing artifact blocks review.",
        severity="HIGH",
        confidence="HIGH",
        affected_artifact="Documents/missing.md",
        required_action="Create the file or retract the claim.",
    )
    artifact_service = ArtifactService(service.database, workspace)

    dialog = DirectorConsoleDialog(
        service,
        registry,
        health,
        provisioning,
        artifact_service=artifact_service,
    )

    assert dialog.artifacts_tab.table.rowCount() == 1
    assert dialog.artifacts_tab.table.item(0, 0).text() == "Documents/missing.md"
    assert dialog.artifacts_tab.table.item(0, 2).text() == "NOT_FOUND"
    assert dialog.artifacts_tab.table.item(0, 3).text() == "1"
    assert "Missing artifact blocks review." in dialog.artifacts_tab.detail.toPlainText()


def test_add_employee_wizard_generates_stable_id(tmp_path):
    qapp()
    service, _registry, health, provisioning = make_service(tmp_path)
    wizard = AddEmployeeWizard(service, health, provisioning)

    wizard.identity.display_name.setText("Деловод")
    wizard.identity.generate_id()

    assert wizard.identity.agent_id.text().startswith("agent-")


def test_edit_employee_dialog_round_trips_names_and_communication_profile(tmp_path):
    qapp()
    service, _registry, _health, _provisioning = make_service(tmp_path)
    profile = AgentProfile(
        agent_id="agent-profile-roundtrip",
        display_name="Дмитрий Шевченко",
        description="Profile persistence fixture",
        lifecycle_state="ACTIVE",
        provider_id="CODEX_CLI",
        preferred_name="Дмитрий",
        informal_name="Дмитян",
        communication_profile={
            "directness": 5,
            "warmth": 2,
            "formality": 4,
            "humor": 0,
            "assertiveness": 5,
            "verbosity": 1,
            "initiative": 4,
            "emotionality": 5,
            "explanation_style": "examples",
            "disagreement_style": "direct",
        },
    )
    service.create_agent(profile, ["DESIGN_ENGINEER"], ["CHAT"], reason="dialog fixture")

    dialog = EditEmployeeDialog(service, profile.agent_id, avatar_dir=tmp_path)

    assert dialog.preferred_name.text() == "Дмитрий"
    assert dialog.informal_name.text() == "Дмитян"
    assert dialog.communication_controls["directness"].value() == 5
    assert dialog.communication_controls["warmth"].value() == 2
    assert dialog.communication_controls["formality"].value() == 4

    dialog.preferred_name.setText("Дима")
    dialog.communication_controls["directness"].setValue(3)
    dialog.communication_controls["warmth"].setValue(4)
    dialog.communication_controls["formality"].setValue(2)
    dialog.save()

    row = service.database.get_agent_profile(profile.agent_id)
    saved = service._communication_profile_from_row(row)
    assert row["preferred_name"] == "Дима"
    assert row["informal_name"] == "Дмитян"
    assert saved["directness"] == 3
    assert saved["warmth"] == 4
    assert saved["formality"] == 2
    assert saved["explanation_style"] == "examples"
    assert saved["disagreement_style"] == "direct"


def test_organization_catalog_renders_presets_and_empty_state(tmp_path):
    qapp()
    service, registry, health, provisioning = make_service(tmp_path)
    universal = UniversalPlatformService(service.database, management_service=service, conversation_id=service.database.ensure_single_conversation())
    universal.seed_demo_fixtures()
    dialog = DirectorConsoleDialog(service, registry, health, provisioning, universal_platform_service=universal)

    assert dialog.universal_tab.templates.count() >= 21
    assert dialog.universal_tab.organization_dashboard.toPlainText()


def test_organization_activation_wizard_follows_interface_language(tmp_path):
    qapp()
    service, _registry, _health, _provisioning = make_service(tmp_path)
    universal = UniversalPlatformService(service.database, management_service=service)
    universal.seed_management_library()
    template = next(item for item in universal.list_templates() if item.name == "SOLO_PROFESSIONAL")

    expected_titles = {
        "ru": "Создать организацию",
        "uk": "Створити організацію",
        "en": "Create organization",
    }
    for language, expected in expected_titles.items():
        wizard = OrganizationActivationWizard(universal, template, language)
        assert wizard.windowTitle() == expected
        assert wizard._copy["organization_name"]
        assert wizard._copy["confirm"]
        wizard.close()
