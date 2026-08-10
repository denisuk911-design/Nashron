import json

from core.config_repository import ConfigurationRepository
from core.database import Database
from core.identity_service import IdentityService
from core.knowledge_service import KnowledgeService
from core.management_service import ManagementService
from core.prompt_builder import PromptBuilder


def _database(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    ManagementService(db, ConfigurationRepository(tmp_path / "management")).ensure_foundations()
    return db


def test_knowledge_card_lifecycle_and_retrieval(tmp_path):
    db = _database(tmp_path)
    service = KnowledgeService(db)
    card_id = service.create_card(
        title="INA228 current monitor",
        summary="INA228 needs shunt calibration before current readings are useful.",
        source_authority="OFFICIAL",
        role_ids=["DESIGN_ENGINEER"],
        tags=["INA228", "current"],
    )
    service.update_status(card_id, "ACTIVE", reason="source checked")

    cards = service.relevant_active_cards("INA228 ток датчик", "DESIGN_ENGINEER")
    events = service.list_events(card_id)

    assert cards[0].knowledge_id == card_id
    assert [event.event_type for event in events] == ["STATUS_CHANGED", "CREATED"]


def test_draft_knowledge_is_not_retrieved(tmp_path):
    db = _database(tmp_path)
    service = KnowledgeService(db)
    service.create_card(title="Draft rule", summary="Do not use yet.", tags=["INA228"])

    assert service.relevant_active_cards("INA228", "DESIGN_ENGINEER") == []


def test_prompt_builder_supplies_active_knowledge_and_records_usage(tmp_path):
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
    knowledge = KnowledgeService(db)
    card_id = knowledge.create_card(
        title="KiCad ERC baseline",
        summary="ERC findings must be resolved or explicitly accepted before release.",
        source_authority="INTERNAL_VERIFIED",
        role_ids=["DESIGN_ENGINEER"],
        tags=["KiCad", "ERC"],
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
    builder = PromptBuilder(prompt_path, IdentityService(identity_path), timeline_path, db, knowledge_service=knowledge)

    prompt = builder.build(conversation_id, "KiCad ERC проверить", task_id=task_id, run_id=run_id)
    usage = db.list_knowledge_usage()

    assert "KiCad ERC baseline" in prompt
    assert usage[0]["knowledge_id"] == card_id
    assert usage[0]["usage_type"] == "SUPPLIED"


def test_invalid_knowledge_status_is_rejected(tmp_path):
    service = KnowledgeService(_database(tmp_path))
    card_id = service.create_card(title="Safe source")

    try:
        service.update_status(card_id, "APPROVED_BY_AGENT")
    except ValueError as exc:
        assert "Недопустимый статус" in str(exc)
    else:
        raise AssertionError("invalid knowledge status accepted")


def test_knowledge_usage_counts_are_grouped_by_card(tmp_path):
    db = _database(tmp_path)
    service = KnowledgeService(db)
    card_id = service.create_card(title="Counted rule", status="ACTIVE")
    db.record_knowledge_usage(knowledge_id=card_id, role="DESIGN_ENGINEER", usage_type="SUPPLIED")
    db.record_knowledge_usage(knowledge_id=card_id, role="DESIGN_ENGINEER", usage_type="APPLIED")
    db.record_knowledge_usage(knowledge_id=card_id, role="DESIGN_ENGINEER", usage_type="IGNORED")
    db.record_knowledge_usage(knowledge_id=card_id, role="DESIGN_ENGINEER", usage_type="MISAPPLIED")

    counts = service.usage_counts_by_card()[card_id]

    assert counts.supplied == 1
    assert counts.applied == 1
    assert counts.ignored == 1
    assert counts.misapplied == 1
