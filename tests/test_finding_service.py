from core.config_repository import ConfigurationRepository
from core.database import Database
from core.finding_service import FindingService
from core.management_service import ManagementService


def _database(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    ManagementService(db, ConfigurationRepository(tmp_path / "management")).ensure_foundations()
    db.ensure_project("project-default", "Default")
    return db


def test_finding_lifecycle_is_audited(tmp_path):
    db = _database(tmp_path)
    task_id = db.create_task("project-default", "Review board", None, "1.0")
    service = FindingService(db)

    finding_id = service.create_finding(
        task_id=task_id,
        description="DRC has unresolved clearance error.",
        severity="HIGH",
        confidence="HIGH",
        affected_artifact="board.kicad_pcb",
        location="J1",
        standard_id="STD-DRC",
    )
    service.update_status(finding_id, "RESOLVED", resolution="Clearance fixed and rechecked.")

    finding = service.list_findings()[0]
    events = service.list_events(finding_id)

    assert finding.status == "RESOLVED"
    assert finding.standard_id == "STD-DRC"
    assert "std-drc" in finding.repeat_key
    assert [event.event_type for event in events] == ["STATUS_CHANGED", "CREATED"]


def test_high_open_finding_blocks_task_completion(tmp_path):
    db = _database(tmp_path)
    task_id = db.create_task("project-default", "Board", None, "1.0")
    service = FindingService(db)
    finding_id = service.create_finding(task_id=task_id, description="ERC error remains.", severity="HIGH")

    assert db.task_has_blocking_findings(task_id)

    service.update_status(finding_id, "RESOLVED", resolution="Fixed.")

    assert not db.task_has_blocking_findings(task_id)


def test_invalid_finding_status_is_rejected(tmp_path):
    db = _database(tmp_path)
    task_id = db.create_task("project-default", "Review", None, "1.0")
    service = FindingService(db)
    finding_id = service.create_finding(task_id=task_id, description="Bad silk label.")

    try:
        service.update_status(finding_id, "CLOSED_BY_AGENT")
    except ValueError as exc:
        assert "Недопустимый статус" in str(exc)
    else:
        raise AssertionError("invalid finding status accepted")


def test_structured_response_findings_are_imported(tmp_path):
    db = _database(tmp_path)
    task_id = db.create_task("project-default", "Review", None, "1.0")
    service = FindingService(db)
    envelope = {
        "task_id": task_id,
        "run_id": "RUN-QA-1",
        "findings": [
            {
                "description": "J1 clearance is below the project rule.",
                "severity": "high",
                "confidence": "HIGH",
                "affected_artifact": "board.kicad_pcb",
                "location": "J1",
                "evidence": {"check": "DRC", "observed": "0.10 mm"},
                "impact": "Assembly risk.",
                "required_action": "Increase clearance and re-run DRC.",
                "standard_id": "STD-DRC",
                "finding_type": "STANDARD_VIOLATION",
            },
            {"summary": ""},
            123,
        ],
    }

    created = service.import_from_structured_response(envelope=envelope, actor="petr")

    assert len(created) == 1
    finding = service.list_findings(task_id=task_id)[0]
    assert finding.reviewer_run_id == "RUN-QA-1"
    assert finding.severity == "HIGH"
    assert finding.confidence == "HIGH"
    assert finding.affected_artifact == "board.kicad_pcb"
    assert finding.location == "J1"
    assert finding.standard_id == "STD-DRC"
    assert finding.finding_type == "STANDARD_VIOLATION"
    assert "DRC" in finding.evidence


def test_structured_response_finding_import_is_idempotent_for_run(tmp_path):
    db = _database(tmp_path)
    task_id = db.create_task("project-default", "Review", None, "1.0")
    service = FindingService(db)
    envelope = {
        "task_id": task_id,
        "run_id": "RUN-QA-1",
        "findings": [
            {
                "description": "Missing pull-up resistor on SDA.",
                "severity": "HIGH",
                "affected_artifact": "schematic.kicad_sch",
                "location": "U1 SDA",
            }
        ],
    }

    first = service.import_from_structured_response(envelope=envelope, actor="petr")
    second = service.import_from_structured_response(envelope=envelope, actor="petr")

    assert len(first) == 1
    assert second == []
    assert len(service.list_findings(task_id=task_id)) == 1
