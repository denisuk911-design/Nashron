from core.database import Database
from core.context_snapshot_service import ContextSnapshotService
from core.thread_question_service import ThreadQuestionService


def test_records_and_answers_assigned_thread_question(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    conversation_id = db.create_conversation()
    service = ThreadQuestionService(db, conversation_id)
    question_message_id = db.add_message(conversation_id, "user", "Шушанна, какие ограничения?")

    question_id = service.record_owner_question(
        message_id=question_message_id,
        text="Шушанна, какие ограничения?",
        assigned_agent_keys=["shushan"],
    )

    open_questions = service.open_questions()
    assert question_id is not None
    assert [question.id for question in open_questions] == [question_id]
    assert open_questions[0].assigned_agent_keys == ["shushan"]

    wrong_answer_id = db.add_message(conversation_id, "roman", "Не моя задача.")
    assert service.mark_answered_by_agent(agent_key="roman", answer_message_id=wrong_answer_id) == []
    assert len(service.open_questions()) == 1

    answer_id = db.add_message(conversation_id, "shushan", "Ограничения сняты.")
    assert service.mark_answered_by_agent(agent_key="shushan", answer_message_id=answer_id) == [question_id]
    assert service.open_questions() == []

    row = db.list_thread_questions(conversation_id=conversation_id)[0]
    assert row["status"] == "ANSWERED"
    assert row["answer_message_id"] == answer_id
    assert row["answered_by_agent_key"] == "shushan"

    assert service.accept_answer(question_id)
    assert db.list_thread_questions(conversation_id=conversation_id)[0]["status"] == "ACCEPTED"

    assert service.reopen(question_id)
    assert service.open_questions()[0].id == question_id


def test_context_snapshot_uses_persisted_open_questions(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    conversation_id = db.create_conversation()
    question_message_id = db.add_message(conversation_id, "user", "Шушанна, какие ограничения?")
    ThreadQuestionService(db, conversation_id).record_owner_question(
        message_id=question_message_id,
        text="Шушанна, какие ограничения?",
        assigned_agent_keys=["shushan"],
    )

    snapshot = ContextSnapshotService(db).build(
        conversation_id=conversation_id,
        user_message="продолжай",
        agent_key="shushan",
    )

    assert any("Шушанна, какие ограничения?" in line for line in snapshot.unresolved_questions)
    assert any("shushan" in line for line in snapshot.unresolved_questions)
