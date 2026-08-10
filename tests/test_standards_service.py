import json

from core.config_repository import ConfigurationRepository
from core.database import Database
from core.identity_service import IdentityService
from core.management_service import ManagementService
from core.prompt_builder import PromptBuilder
from core.standards_service import StandardsService


def _database(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    ManagementService(db, ConfigurationRepository(tmp_path / "management")).ensure_foundations()
    return db


def test_standard_card_lifecycle_and_retrieval(tmp_path):
    db = _database(tmp_path)
    service = StandardsService(db)
    standard_id = service.create_card(
        code="PCB-ERC-001",
        title="ERC before release",
        requirement="ERC findings must be resolved or explicitly accepted before release.",
        authority="INTERNAL",
        mandatory_level="MANDATORY",
        role_ids=["DESIGN_ENGINEER"],
        tags=["KiCad", "ERC"],
    )
    service.update_status(standard_id, "ACTIVE", reason="owner approved")

    cards = service.relevant_active_cards("KiCad ERC проверить", "DESIGN_ENGINEER")
    events = service.list_events(standard_id)

    assert cards[0].standard_id == standard_id
    assert [event.event_type for event in events] == ["STATUS_CHANGED", "CREATED"]


def test_draft_standard_is_not_retrieved(tmp_path):
    db = _database(tmp_path)
    service = StandardsService(db)
    service.create_card(code="DRAFT-1", title="Draft", requirement="Do not use yet.", tags=["ERC"])

    assert service.relevant_active_cards("ERC", "DESIGN_ENGINEER") == []


def test_prompt_builder_supplies_active_standards_and_records_usage(tmp_path):
    prompt_path = tmp_path / "roman_system.md"
    prompt_path.write_text("System", encoding="utf-8")
    identity_path = tmp_path / "identity.json"
    identity_path.write_text(
        json.dumps({"full_name": "Роман Неслышев", "current_year": 2050, "identity_locked": True}),
        encoding="utf-8",
    )
    timeline_path = tmp_path / "timeline.json"
    timeline_path.write_text(json.dumps({"events": []}), encoding="utf-8")
    db = _database(tmp_path)
    standards = StandardsService(db)
    standard_id = standards.create_card(
        code="PCB-DRC-001",
        title="DRC gate",
        requirement="DRC must be clean before board handoff.",
        authority="INTERNAL",
        mandatory_level="MANDATORY",
        role_ids=["DESIGN_ENGINEER"],
        tags=["KiCad", "DRC"],
        status="ACTIVE",
    )
    conversation_id = db.create_conversation()
    db.ensure_project("project-default", "Default")
    task_id = db.create_task("project-default", "KiCad task", None, "1.0")
    run_id = db.create_agent_run(
        task_id=task_id,
        agent_id="agent-roman",
        agent_key="roman",
        logical_role="DESIGN_ENGINEER",
        provider="CODEX_CLI",
        prompt_hash=None,
        started_at="2026-01-01T00:00:00",
    )
    builder = PromptBuilder(prompt_path, IdentityService(identity_path), timeline_path, db, standards_service=standards)

    prompt = builder.build(conversation_id, "KiCad DRC проверить", task_id=task_id, run_id=run_id)
    usage = db.list_standard_usage()

    assert "PCB-DRC-001" in prompt
    assert usage[0]["standard_id"] == standard_id
    assert usage[0]["usage_type"] == "SUPPLIED"


def test_invalid_standard_status_is_rejected(tmp_path):
    service = StandardsService(_database(tmp_path))
    standard_id = service.create_card(code="STD-1", title="Safe standard")

    try:
        service.update_status(standard_id, "APPROVED_BY_AGENT")
    except ValueError as exc:
        assert "Недопустимый статус" in str(exc)
    else:
        raise AssertionError("invalid standard status accepted")


def test_standard_usage_counts_are_grouped_by_card(tmp_path):
    db = _database(tmp_path)
    service = StandardsService(db)
    standard_id = service.create_card(code="STD-COUNT", title="Counted standard", status="ACTIVE")
    db.record_standard_usage(standard_id=standard_id, role="DESIGN_ENGINEER", usage_type="SUPPLIED")
    db.record_standard_usage(standard_id=standard_id, role="DESIGN_ENGINEER", usage_type="APPLIED")
    db.record_standard_usage(standard_id=standard_id, role="DESIGN_ENGINEER", usage_type="IGNORED")
    db.record_standard_usage(standard_id=standard_id, role="DESIGN_ENGINEER", usage_type="MISAPPLIED")

    counts = service.usage_counts_by_card()[standard_id]

    assert counts.supplied == 1
    assert counts.applied == 1
    assert counts.ignored == 1
    assert counts.misapplied == 1
