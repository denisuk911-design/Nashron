from core.agent_directory import ChatAgent
from core.conversation_thread_service import ConversationThreadService
from core.database import Database
from core.team_routing import TeamRouter


def _agents():
    return [
        ChatAgent("roman", "agent-roman", "Roman", "CODEX_CLI", ["DESIGN_ENGINEER"], "roman_2050", "", None),
        ChatAgent("shushan", "agent-shushan", "Шушанна", "GEMINI_CLI", ["DOCUMENT_CONTROL_OFFICER"], "doc", "", None),
    ]


def test_thread_owner_persists_direct_address(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    conversation_id = db.create_conversation()
    message_id = db.add_message(conversation_id, "user", "Шушанна, проверь ограничения")
    decision = TeamRouter().decide("Шушанна, проверь ограничения", _agents())

    service = ConversationThreadService(db, conversation_id)
    service.apply_routing_decision(decision, message_id=message_id, task_id="TASK-1", topic="проверка ограничений")

    restarted = ConversationThreadService(Database(tmp_path / "roman.sqlite3"), conversation_id)
    snapshot = restarted.snapshot()
    assert snapshot.active_addressee_agent_id == "agent-shushan"
    assert snapshot.owner_keys == ["shushan"]
    assert snapshot.active_task_id == "TASK-1"


def test_broadcast_does_not_clear_previous_thread_owner(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    conversation_id = db.create_conversation()
    service = ConversationThreadService(db, conversation_id)
    direct = TeamRouter().decide("Шушанна, проверь", _agents())
    broadcast = TeamRouter().decide("Для сведения: завтра меняем папку проекта.", _agents())

    service.apply_routing_decision(direct, message_id=None, task_id="TASK-1", topic="документы")
    service.apply_routing_decision(broadcast, message_id=None, task_id=None, topic="информация")

    snapshot = service.snapshot()
    assert snapshot.owner_keys == ["shushan"]
    assert snapshot.active_topic == "документы"


def test_team_discussion_records_expected_next_actors(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    conversation_id = db.create_conversation()
    decision = TeamRouter().decide("Роман и Шушанна, обсудите документ.", _agents())

    snapshot = ConversationThreadService(db, conversation_id).apply_routing_decision(
        decision,
        message_id=None,
        task_id="TASK-2",
        topic="обсуждение документа",
    )

    assert snapshot.active_addressee_agent_id is None
    assert snapshot.owner_keys == ["roman", "shushan"]
