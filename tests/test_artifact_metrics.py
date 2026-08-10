from core.config_repository import ConfigurationRepository
from core.database import Database
from core.management_service import ManagementService
from core.product_metrics_service import ProductMetricsService


def test_artifact_metric_counts_verified_and_missing_artifacts(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    ManagementService(db, ConfigurationRepository(tmp_path / "management")).ensure_foundations()
    db.ensure_project("project-default", "Default Project")
    task_id = db.create_task("project-default", "Artifacts", None, "1.0")
    db.upsert_artifact(
        task_id=task_id,
        project_id="project-default",
        relative_path="Documents/report.md",
        sha256="abc",
        size=10,
        status="OBSERVED",
        validation_status="VERIFIED",
    )
    db.upsert_artifact(
        task_id=task_id,
        project_id="project-default",
        relative_path="Documents/missing.md",
        status="MISSING",
        validation_status="NOT_FOUND",
    )

    metrics = {row.name: row for row in ProductMetricsService(db).metrics()}

    assert metrics["Артефакты подтверждены"].value == "1 / 2"
    assert "MISSING: 1" in metrics["Артефакты подтверждены"].detail
