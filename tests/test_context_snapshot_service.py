from core.config_repository import ConfigurationRepository
from core.context_snapshot_service import ContextSnapshotService
from core.database import Database
from core.management_models import AgentProfile
from core.management_service import ManagementService


def _database_with_shushan(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    service = ManagementService(db, ConfigurationRepository(tmp_path / "management"))
    service.ensure_foundations()
    service.create_agent(
        AgentProfile(
            agent_id="agent-shushan",
            display_name="Шушан",
            description="Ведет документацию проекта",
            lifecycle_state="ACTIVE",
            provider_id="GEMINI_CLI",
            persona_id="document_control",
        ),
        ["DOCUMENT_CONTROL_OFFICER"],
        ["CHAT"],
        reason="test",
    )
    return db


def test_snapshot_selects_role_relevant_context_for_new_employee(tmp_path):
    db = _database_with_shushan(tmp_path)
    conversation_id = db.create_conversation()
    db.add_message(conversation_id, "user", "Документация должна идти по ГОСТ и иметь версию.")
    db.add_message(conversation_id, "roman", "unrelated pcb trace width chatter xxyyzz")
    db.add_message(conversation_id, "user", "Позже обсудим музыку.")

    snapshot = ContextSnapshotService(db).build(
        conversation_id=conversation_id,
        user_message="а ограничения?",
        agent_key="shushan",
        thread_owner_keys=["shushan"],
        immediate_limit=2,
    )

    prompt_text = "\n".join(snapshot.prompt_lines())
    assert "Документация" in prompt_text
    assert "ГОСТ" in prompt_text
    assert "xxyyzz" not in prompt_text


def test_snapshot_falls_back_to_recent_messages_when_no_relevance(tmp_path):
    db = _database_with_shushan(tmp_path)
    conversation_id = db.create_conversation()
    for index in range(4):
        db.add_message(conversation_id, "user", f"old-{index}")

    snapshot = ContextSnapshotService(db).build(
        conversation_id=conversation_id,
        user_message="new",
        agent_key="roman",
        immediate_limit=2,
    )

    text = "\n".join(snapshot.immediate_lines)
    assert "old-2" in text
    assert "old-3" in text
    assert "old-0" not in text
