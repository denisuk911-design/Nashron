import json

import pytest

from core.agent_router import AgentRouter
from core.database import Database
from core.models import CodexResult
from core.structured_response import parse_agent_response
from core.task_orchestrator import TaskOrchestrator
from core.task_state_service import TaskStateError, TaskStateService, TaskTransitionRequest


def make_database(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    db.ensure_project("project-default", "Default Project")
    return db


def test_phase1_migration_preserves_message_history(tmp_path):
    db_path = tmp_path / "roman.sqlite3"
    db = Database(db_path)
    db.initialize()
    conversation_id = db.create_conversation("legacy")
    db.add_message(conversation_id, "user", "hello")

    reopened = Database(db_path)
    reopened.initialize()

    assert reopened.list_messages(conversation_id)[0].content == "hello"
    assert reopened.connect().execute("SELECT name FROM sqlite_master WHERE name = 'tasks'").fetchone() is not None


def test_valid_task_state_transition(tmp_path):
    db = make_database(tmp_path)
    service = TaskStateService(db)
    task_id = service.create_task("project-default", "Design board", None)

    service.transition(
        TaskTransitionRequest(
            task_id=task_id,
            next_state="REQUIREMENTS_DRAFT",
            actor="owner",
            logical_role="PROJECT_MANAGER",
            reason="requirements captured",
        )
    )

    assert service.get_state(task_id) == "REQUIREMENTS_DRAFT"
    assert len(db.list_task_transitions(task_id)) == 1


def test_invalid_task_state_transition_fails_closed(tmp_path):
    db = make_database(tmp_path)
    service = TaskStateService(db)
    task_id = service.create_task("project-default", "Design board", None)

    with pytest.raises(TaskStateError):
        service.transition(
            TaskTransitionRequest(
                task_id=task_id,
                next_state="COMPLETED",
                actor="agent-design",
                logical_role="DESIGN_ENGINEER",
                reason="self approved",
            )
        )

    assert service.get_state(task_id) == "NEW"


def test_design_engineer_cannot_complete_even_from_owner_review(tmp_path):
    db = make_database(tmp_path)
    service = TaskStateService(db)
    task_id = service.create_task("project-default", "Design board", None)
    with db.connect() as conn:
        conn.execute("UPDATE tasks SET state = 'OWNER_REVIEW' WHERE id = ?", (task_id,))

    with pytest.raises(TaskStateError):
        service.transition(
            TaskTransitionRequest(
                task_id=task_id,
                next_state="COMPLETED",
                actor="agent-design",
                logical_role="DESIGN_ENGINEER",
                reason="not allowed",
            )
        )


def test_structured_response_parser_preserves_human_text():
    content = """Short answer.

```json
{"schema_version":"1.0","agent_id":"agent-roman","role":"DESIGN_ENGINEER","task_id":"TASK-1","run_id":"RUN-1","action":"MESSAGE","summary":"done","files_read":[],"files_created":[],"files_modified":[],"files_deleted":[],"checks":[],"findings":[],"risks":[]}
```"""

    parsed = parse_agent_response(content)

    assert parsed.human_text == "Short answer."
    assert parsed.has_valid_envelope
    assert parsed.envelope["role"] == "DESIGN_ENGINEER"


def test_structured_response_parser_accepts_json_from_first_character():
    content = '{"schema_version":"1.0","agent_id":"agent-shushan","role":"DOCUMENT_CONTROL_OFFICER","task_id":"TASK-1","run_id":"RUN-1","action":"MESSAGE","summary":"Updated document standard notes.","files_read":[],"files_created":[],"files_modified":["docs/SKILL_GOST.md"],"files_deleted":[],"checks":[],"findings":[],"risks":[]}'

    parsed = parse_agent_response(content)

    assert parsed.human_text == ""
    assert parsed.has_valid_envelope
    assert parsed.envelope["summary"] == "Updated document standard notes."


def test_structured_response_parser_extracts_embedded_schema_json():
    content = 'json\n{"schema_version":"1.0","agent_id":"agent-shushan","role":"DOCUMENT_CONTROL_OFFICER","task_id":"TASK-1","run_id":"RUN-1","action":"MESSAGE","summary":"Updated document standard notes.","files_read":[],"files_created":[],"files_modified":["docs/SKILL_GOST.md"],"files_deleted":[],"checks":[],"findings":[],"risks":[]}'

    parsed = parse_agent_response(content)

    assert parsed.human_text == ""
    assert parsed.has_valid_envelope
    assert parsed.envelope["summary"] == "Updated document standard notes."


def test_malformed_structured_response_fails_safely():
    parsed = parse_agent_response("Text\n```json\n{bad}\n```")

    assert parsed.envelope is None
    assert parsed.malformed_structured is not None
    assert parsed.errors


def test_missing_structured_response_is_preserved_for_display():
    parsed = parse_agent_response("Only human text")

    assert parsed.human_text == "Only human text"
    assert parsed.envelope is None
    assert parsed.errors == ["missing_structured_response"]


def test_unclosed_structured_response_is_removed_from_human_text():
    parsed = parse_agent_response('Human text\n```json\n{"schema_version":"1.0"')

    assert parsed.human_text == "Human text"
    assert parsed.envelope is None
    assert parsed.malformed_structured is not None


def test_orchestrator_records_cancelled_run_not_successful(tmp_path):
    db = make_database(tmp_path)
    orchestrator = TaskOrchestrator(db, TaskStateService(db), AgentRouter())
    task_id = orchestrator.start_user_task("task", None)
    run = orchestrator.start_run("roman")

    orchestrator.finish_run(
        run.run_id,
        CodexResult(False, "", None, 0.1, "cancelled", cancelled=True),
        "",
    )

    row = db.get_agent_run(run.run_id)
    assert task_id == run.task_id
    assert row["ok"] == 0
    assert row["cancelled"] == 1
    assert row["recovery_state"] == "CANCELLED"
    assert json.loads(row["parse_errors"]) == ["missing_structured_response"]
