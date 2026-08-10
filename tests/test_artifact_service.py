from core.artifact_service import ArtifactService
from core.config_repository import ConfigurationRepository
from core.database import Database
from core.management_service import ManagementService


def _database(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    ManagementService(db, ConfigurationRepository(tmp_path / "management")).ensure_foundations()
    db.ensure_project("project-default", "Default")
    return db


def test_structured_response_artifacts_are_verified_against_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    report = workspace / "Documents" / "report.md"
    report.parent.mkdir()
    report.write_text("real artifact", encoding="utf-8")
    db = _database(tmp_path)
    task_id = db.create_task("project-default", "Create report", None, "1.0")
    service = ArtifactService(db, workspace)
    envelope = {
        "task_id": task_id,
        "run_id": "RUN-1",
        "role": "DOCUMENT_CONTROL_OFFICER",
        "files_created": ["Documents/report.md", "Documents/missing.md"],
        "files_modified": [],
        "files_deleted": [],
    }

    registered = service.import_from_structured_response(envelope=envelope)
    artifacts = {artifact.relative_path: artifact for artifact in service.list_artifacts(task_id=task_id)}

    assert len(registered) == 2
    assert artifacts["Documents/report.md"].status == "OBSERVED"
    assert artifacts["Documents/report.md"].validation_status == "VERIFIED"
    assert artifacts["Documents/report.md"].sha256
    assert artifacts["Documents/report.md"].size == len("real artifact")
    assert artifacts["Documents/missing.md"].status == "MISSING"
    assert artifacts["Documents/missing.md"].validation_status == "NOT_FOUND"


def test_deleted_artifact_claim_is_checked_against_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    db = _database(tmp_path)
    task_id = db.create_task("project-default", "Delete old file", None, "1.0")
    service = ArtifactService(db, workspace)

    service.import_from_structured_response(
        envelope={
            "task_id": task_id,
            "run_id": "RUN-DEL",
            "role": "DESIGN_ENGINEER",
            "files_deleted": ["Documents/old.md"],
        }
    )

    artifact = service.list_artifacts(task_id=task_id)[0]

    assert artifact.status == "DELETED"
    assert artifact.validation_status == "VERIFIED_ABSENT"
    assert artifact.deleted


def test_artifact_import_reuses_same_artifact_for_same_task_path(tmp_path):
    workspace = tmp_path / "workspace"
    target = workspace / "Code" / "module.py"
    target.parent.mkdir(parents=True)
    target.write_text("print(1)\n", encoding="utf-8")
    db = _database(tmp_path)
    task_id = db.create_task("project-default", "Edit code", None, "1.0")
    service = ArtifactService(db, workspace)
    envelope = {
        "task_id": task_id,
        "run_id": "RUN-1",
        "role": "DESIGN_ENGINEER",
        "files_modified": ["Code/module.py"],
    }

    first = service.import_from_structured_response(envelope=envelope)
    target.write_text("print(2)\n", encoding="utf-8")
    second = service.import_from_structured_response(envelope={**envelope, "run_id": "RUN-2"})

    artifacts = service.list_artifacts(task_id=task_id)

    assert first == second
    assert len(artifacts) == 1
    assert artifacts[0].created_by_run_id == "RUN-2"
    assert artifacts[0].status == "OBSERVED"


def test_artifact_service_finds_related_qa_findings(tmp_path):
    workspace = tmp_path / "workspace"
    artifact_path = workspace / "Documents" / "report.md"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("content", encoding="utf-8")
    db = _database(tmp_path)
    task_id = db.create_task("project-default", "Review report", None, "1.0")
    service = ArtifactService(db, workspace)
    service.import_from_structured_response(
        envelope={
            "task_id": task_id,
            "run_id": "RUN-1",
            "role": "DOCUMENT_CONTROL_OFFICER",
            "files_created": ["Documents/report.md"],
        }
    )
    db.create_finding(
        task_id=task_id,
        description="Report misses source reference.",
        severity="HIGH",
        confidence="HIGH",
        affected_artifact="Documents/report.md",
        required_action="Add source reference.",
    )
    db.create_finding(
        task_id=task_id,
        description="Filename-only finding also applies.",
        severity="LOW",
        confidence="MEDIUM",
        affected_artifact="report.md",
    )

    artifact = service.list_artifacts(task_id=task_id)[0]
    related = service.related_findings(artifact)
    links = service.list_finding_links(artifact_id=artifact.artifact_id)
    again = service.reconcile_finding_links(task_id=task_id)

    assert {finding.description for finding in related} == {
        "Filename-only finding also applies.",
        "Report misses source reference.",
    }
    assert len(links) == 2
    assert {link.match_type for link in links} == {"EXACT_PATH", "FILENAME"}
    assert sorted(again) == sorted(link.link_id for link in links)
    assert len(db.list_artifact_finding_links(artifact_id=artifact.artifact_id)) == 2
    assert len(db.list_artifact_finding_link_events()) == 2
