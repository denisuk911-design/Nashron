import os

from PySide6.QtWidgets import QApplication

from core.artifact_service import ArtifactService
from core.config_repository import ConfigurationRepository
from core.database import Database
from core.management_service import ManagementService
from core.provider_service import ProviderHealthService, ProviderProvisioningService, ProviderRegistry
from core.universal_platform_service import UniversalPlatformService
from gui.director_console import AddEmployeeWizard, DirectorConsoleDialog


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


def test_director_console_renders_employee_list(tmp_path):
    qapp()
    service, registry, health, provisioning = make_service(tmp_path)

    dialog = DirectorConsoleDialog(service, registry, health, provisioning)

    assert dialog.tabs.count() == 13
    assert dialog.tabs.tabText(1) == "Организация"
    assert dialog.employee_tab.table.rowCount() >= 2


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


def test_organization_catalog_renders_presets_and_empty_state(tmp_path):
    qapp()
    service, registry, health, provisioning = make_service(tmp_path)
    universal = UniversalPlatformService(service.database, management_service=service, conversation_id=service.database.ensure_single_conversation())
    universal.seed_demo_fixtures()
    dialog = DirectorConsoleDialog(service, registry, health, provisioning, universal_platform_service=universal)

    assert dialog.universal_tab.templates.count() >= 21
    assert dialog.universal_tab.organization_dashboard.toPlainText()
