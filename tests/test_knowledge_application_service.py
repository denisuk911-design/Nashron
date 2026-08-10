from core.config_repository import ConfigurationRepository
from core.database import Database
from core.knowledge_application_service import KnowledgeApplicationService
from core.management_service import ManagementService


def _database(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    ManagementService(db, ConfigurationRepository(tmp_path / "management")).ensure_foundations()
    db.ensure_project("project-default", "Default Project")
    return db


def _run(db):
    task_id = db.create_task("project-default", "task", None, "1.0")
    run_id = db.create_agent_run(
        task_id=task_id,
        agent_id="agent-roman",
        agent_key="roman",
        logical_role="DESIGN_ENGINEER",
        provider="CODEX_CLI",
        prompt_hash=None,
        started_at="2026-01-01T00:00:00",
    )
    return task_id, run_id


def test_structured_response_records_applied_supplied_knowledge_and_standard(tmp_path):
    db = _database(tmp_path)
    task_id, run_id = _run(db)
    knowledge_id = db.create_knowledge_card(title="ERC rule", status="ACTIVE")
    standard_id = db.create_standard_card(code="STD-ERC", title="ERC gate", status="ACTIVE")
    db.record_knowledge_usage(
        knowledge_id=knowledge_id,
        role="DESIGN_ENGINEER",
        usage_type="SUPPLIED",
        task_id=task_id,
        run_id=run_id,
    )
    db.record_standard_usage(
        standard_id=standard_id,
        role="DESIGN_ENGINEER",
        usage_type="SUPPLIED",
        task_id=task_id,
        run_id=run_id,
    )

    result = KnowledgeApplicationService(db).import_from_structured_response(
        envelope={
            "task_id": task_id,
            "run_id": run_id,
            "role": "DESIGN_ENGINEER",
            "knowledge_used": [{"knowledge_id": knowledge_id, "outcome": "APPLIED", "reason": "used for ERC gate"}],
            "standards_used": [{"standard_id": standard_id, "outcome": "APPLIED", "reason": "checked release gate"}],
        },
        task_id=task_id,
        run_id=run_id,
        actor="roman",
    )

    knowledge_usage = db.list_knowledge_usage()
    standard_usage = db.list_standard_usage()

    assert result.knowledge_recorded == 1
    assert result.standards_recorded == 1
    assert {row["usage_type"] for row in knowledge_usage} == {"SUPPLIED", "APPLIED"}
    assert {row["usage_type"] for row in standard_usage} == {"SUPPLIED", "APPLIED"}


def test_unreferenced_supplied_cards_are_recorded_as_ignored(tmp_path):
    db = _database(tmp_path)
    task_id, run_id = _run(db)
    knowledge_id = db.create_knowledge_card(title="Unused rule", status="ACTIVE")
    standard_id = db.create_standard_card(code="STD-UNUSED", title="Unused gate", status="ACTIVE")
    db.record_knowledge_usage(
        knowledge_id=knowledge_id,
        role="DESIGN_ENGINEER",
        usage_type="SUPPLIED",
        task_id=task_id,
        run_id=run_id,
    )
    db.record_standard_usage(
        standard_id=standard_id,
        role="DESIGN_ENGINEER",
        usage_type="SUPPLIED",
        task_id=task_id,
        run_id=run_id,
    )

    KnowledgeApplicationService(db).import_from_structured_response(
        envelope={"task_id": task_id, "run_id": run_id, "role": "DESIGN_ENGINEER"},
        task_id=task_id,
        run_id=run_id,
        actor="roman",
    )

    assert {row["usage_type"] for row in db.list_knowledge_usage()} == {"SUPPLIED", "IGNORED"}
    assert {row["usage_type"] for row in db.list_standard_usage()} == {"SUPPLIED", "IGNORED"}


def test_invented_usage_ids_are_rejected(tmp_path):
    db = _database(tmp_path)
    task_id, run_id = _run(db)
    knowledge_id = db.create_knowledge_card(title="Real rule", status="ACTIVE")
    db.record_knowledge_usage(
        knowledge_id=knowledge_id,
        role="DESIGN_ENGINEER",
        usage_type="SUPPLIED",
        task_id=task_id,
        run_id=run_id,
    )

    result = KnowledgeApplicationService(db).import_from_structured_response(
        envelope={
            "task_id": task_id,
            "run_id": run_id,
            "role": "DESIGN_ENGINEER",
            "knowledge_used": [{"knowledge_id": "KNOW-FAKE", "outcome": "APPLIED"}],
        },
        task_id=task_id,
        run_id=run_id,
        actor="roman",
    )

    assert result.rejected == 1
    assert {row["usage_type"] for row in db.list_knowledge_usage()} == {"SUPPLIED", "IGNORED"}


def test_standard_finding_records_misapplied_for_supplied_standard(tmp_path):
    db = _database(tmp_path)
    task_id, run_id = _run(db)
    standard_id = db.create_standard_card(code="STD-CLEARANCE", title="Clearance gate", status="ACTIVE")
    db.record_standard_usage(
        standard_id=standard_id,
        role="QA_ENGINEER",
        usage_type="SUPPLIED",
        task_id=task_id,
        run_id=run_id,
    )
    finding_id = db.create_finding(
        task_id=task_id,
        description="Clearance is below the required minimum.",
        severity="HIGH",
        confidence="HIGH",
        reviewer_run_id=run_id,
        standard_id=standard_id,
        finding_type="STANDARD_VIOLATION",
    )

    recorded = KnowledgeApplicationService(db).record_standard_misapplications_from_findings(
        finding_ids=[finding_id],
        run_id=run_id,
        task_id=task_id,
        role="QA_ENGINEER",
        actor="petr",
    )

    rows = db.list_standard_usage()
    misapplied = [row for row in rows if row["usage_type"] == "MISAPPLIED"]
    assert recorded == 1
    assert len(misapplied) == 1
    assert misapplied[0]["standard_id"] == standard_id
    assert "Clearance is below" in misapplied[0]["evidence"]


def test_standard_finding_does_not_record_misapplied_when_standard_was_not_supplied(tmp_path):
    db = _database(tmp_path)
    task_id, run_id = _run(db)
    standard_id = db.create_standard_card(code="STD-NOT-SUPPLIED", title="Not supplied", status="ACTIVE")
    finding_id = db.create_finding(
        task_id=task_id,
        description="Standard violation exists, but the standard was not supplied to this run.",
        severity="HIGH",
        confidence="HIGH",
        reviewer_run_id=run_id,
        standard_id=standard_id,
        finding_type="STANDARD_VIOLATION",
    )

    recorded = KnowledgeApplicationService(db).record_standard_misapplications_from_findings(
        finding_ids=[finding_id],
        run_id=run_id,
        task_id=task_id,
        role="QA_ENGINEER",
        actor="petr",
    )

    assert recorded == 0
    assert db.list_standard_usage() == []
