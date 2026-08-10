from core.config_repository import ConfigurationRepository
from core.database import Database
from core.management_service import ManagementService
from core.product_metrics_service import ProductMetricsService


def _database(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    ManagementService(db, ConfigurationRepository(tmp_path / "management")).ensure_foundations()
    db.ensure_project("project-default", "Default Project")
    return db


def test_metrics_are_computed_from_routing_events_and_runs(tmp_path):
    db = _database(tmp_path)
    conversation_id = db.create_conversation()
    first = db.add_message(conversation_id, "user", "Роман, проверь")
    second = db.add_message(conversation_id, "user", "Роман и Петр, обсудите")
    db.record_routing_decision(
        message_id=first,
        thread_id="conversation-1",
        participation_mode="DIRECT",
        explicit_recipients=["roman"],
        inferred_recipients=[],
        selected_responders=["roman"],
        excluded_responders={"petr": "selected_other_employee"},
        interruption_policy=None,
        reason="explicit_name_or_alias",
        router_version="test",
    )
    db.record_routing_decision(
        message_id=second,
        thread_id="conversation-1",
        participation_mode="DIRECT",
        explicit_recipients=["roman", "petr"],
        inferred_recipients=[],
        selected_responders=["roman", "petr"],
        excluded_responders={},
        interruption_policy=None,
        reason="bad_test_route",
        router_version="test",
    )
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
    db.finish_agent_run(
        run_id=run_id,
        ok=True,
        cancelled=False,
        returncode=0,
        duration_seconds=1.0,
        error=None,
        raw_response="",
        parsed_response={"checks": ["checked by test"]},
        parse_errors=[],
        finished_at="2026-01-01T00:00:01",
    )
    db.log_event("duplicate_agent_message_suppressed", "roman")
    db.log_event("unsupported_claim_warning", "claim")
    db.log_event("response_latency_soft_warning", "roman")
    db.log_event("response_latency_timeout_cancelled", "roman")
    knowledge_id = db.create_knowledge_card(title="Evidence rule", status="ACTIVE")
    db.record_knowledge_usage(knowledge_id=knowledge_id, role="DESIGN_ENGINEER", usage_type="SUPPLIED", task_id=task_id, run_id=run_id)
    db.record_knowledge_usage(knowledge_id=knowledge_id, role="DESIGN_ENGINEER", usage_type="APPLIED", task_id=task_id, run_id=run_id)
    standard_id = db.create_standard_card(code="STD-1", title="Evidence standard", status="ACTIVE")
    db.record_standard_usage(standard_id=standard_id, role="DESIGN_ENGINEER", usage_type="SUPPLIED", task_id=task_id, run_id=run_id)
    db.record_standard_usage(standard_id=standard_id, role="DESIGN_ENGINEER", usage_type="APPLIED", task_id=task_id, run_id=run_id)
    db.create_finding(
        task_id=task_id,
        description="DRC clearance error",
        severity="HIGH",
        confidence="HIGH",
        repeat_key="drc-clearance",
    )
    db.create_finding(
        task_id=task_id,
        description="DRC clearance error",
        severity="MEDIUM",
        confidence="HIGH",
        repeat_key="drc-clearance",
    )
    db.upsert_artifact(
        task_id=task_id,
        project_id="project-default",
        relative_path="Documents/report.md",
        created_by_run_id=run_id,
        sha256="abc",
        size=10,
        status="OBSERVED",
        validation_status="VERIFIED",
    )
    db.upsert_artifact(
        task_id=task_id,
        project_id="project-default",
        relative_path="Documents/missing.md",
        created_by_run_id=run_id,
        status="MISSING",
        validation_status="NOT_FOUND",
    )

    metrics = {row.name: row for row in ProductMetricsService(db).metrics()}

    assert metrics["Точность одиночной маршрутизации"].value == "50%"
    assert metrics["Лишние ответчики"].value == "1"
    assert metrics["Дубли и повторные ответы"].value == "50%"
    assert metrics["Неподтвержденные заявления"].value == "100%"
    assert metrics["Запуски с evidence"].value == "100%"
    assert metrics["Долгие ответы"].value == "1"
    assert "автоостановок: 1" in metrics["Долгие ответы"].detail
    assert metrics["Карточки знаний использованы"].value == "1"
    assert metrics["Стандарты использованы"].value == "1"
    assert metrics["Открытые QA findings"].value == "2"
    assert "blocking HIGH/CRITICAL: 1" in metrics["Открытые QA findings"].detail
    assert "повторов: 1" in metrics["Открытые QA findings"].detail


def test_recent_routing_diagnostics_are_owner_readable(tmp_path):
    db = _database(tmp_path)
    conversation_id = db.create_conversation()
    message_id = db.add_message(conversation_id, "user", "Шушанна, проверь")
    db.record_routing_decision(
        message_id=message_id,
        thread_id="conversation-1",
        participation_mode="DIRECT",
        explicit_recipients=["shushan"],
        inferred_recipients=[],
        selected_responders=["shushan"],
        excluded_responders={"roman": "selected_other_employee"},
        interruption_policy=None,
        reason="explicit_name_or_alias",
        router_version="team-router-v1",
    )

    diagnostics = ProductMetricsService(db).recent_routing_diagnostics()

    assert diagnostics[0].participation_mode == "DIRECT"
    assert diagnostics[0].selected == "shushan"
    assert "roman: selected_other_employee" in diagnostics[0].excluded


def test_recent_thread_diagnostics_are_owner_readable(tmp_path):
    db = _database(tmp_path)
    conversation_id = db.create_conversation()
    db.upsert_conversation_thread(
        thread_id=f"conversation-{conversation_id}",
        conversation_id=conversation_id,
        active_addressee_agent_id="agent-shushan",
        active_task_id="TASK-1",
        active_topic="документы",
        last_user_message_id=None,
        expected_next_actor="shushan",
    )

    diagnostics = ProductMetricsService(db).recent_thread_diagnostics()

    assert diagnostics[0].owner == "agent-shushan"
    assert diagnostics[0].active_task_id == "TASK-1"
    assert diagnostics[0].topic == "документы"


def test_recent_question_diagnostics_are_owner_readable(tmp_path):
    db = _database(tmp_path)
    conversation_id = db.create_conversation()
    open_message_id = db.add_message(conversation_id, "user", "Шушанна, какие ограничения?")
    answered_message_id = db.add_message(conversation_id, "user", "Петр, что по аудиту?")
    answer_id = db.add_message(conversation_id, "petr", "Аудит ждет файлы.")
    db.create_thread_question(
        conversation_id=conversation_id,
        thread_id=f"conversation-{conversation_id}",
        question_message_id=open_message_id,
        question_text="Шушанна, какие ограничения?",
        assigned_agent_keys=["shushan"],
    )
    answered_id = db.create_thread_question(
        conversation_id=conversation_id,
        thread_id=f"conversation-{conversation_id}",
        question_message_id=answered_message_id,
        question_text="Петр, что по аудиту?",
        assigned_agent_keys=["petr"],
    )
    db.mark_thread_questions_answered(
        question_ids=[answered_id],
        answer_message_id=answer_id,
        answered_by_agent_key="petr",
    )

    diagnostics = ProductMetricsService(db).recent_question_diagnostics()

    assert diagnostics[0].status in {"OPEN", "ANSWERED"}
    open_row = next(row for row in diagnostics if row.status == "OPEN")
    answered_row = next(row for row in diagnostics if row.status == "ANSWERED")
    assert open_row.question_id
    assert open_row.assigned == "shushan"
    assert open_row.question == "Шушанна, какие ограничения?"
    assert open_row.answer_message_id == "нет"
    assert answered_row.assigned == "petr"
    assert answered_row.answer_message_id == str(answer_id)
    assert answered_row.answered_by == "petr"


def test_owner_can_accept_and_reopen_question_answer(tmp_path):
    db = _database(tmp_path)
    conversation_id = db.create_conversation()
    question_message_id = db.add_message(conversation_id, "user", "Петр, что по аудиту?")
    answer_id = db.add_message(conversation_id, "petr", "Аудит ждет файлы.")
    question_id = db.create_thread_question(
        conversation_id=conversation_id,
        thread_id=f"conversation-{conversation_id}",
        question_message_id=question_message_id,
        question_text="Петр, что по аудиту?",
        assigned_agent_keys=["petr"],
    )
    db.mark_thread_questions_answered(
        question_ids=[question_id],
        answer_message_id=answer_id,
        answered_by_agent_key="petr",
    )
    service = ProductMetricsService(db)

    assert service.accept_question_answer(question_id)
    assert db.list_thread_questions(conversation_id=conversation_id)[0]["status"] == "ACCEPTED"

    assert service.reopen_question(question_id)
    assert db.list_thread_questions(conversation_id=conversation_id)[0]["status"] == "OPEN"
def test_direct_address_delivery_metric_counts_explicit_recipient_matches(tmp_path):
    db = _database(tmp_path)
    conversation_id = db.create_conversation()
    delivered = db.add_message(conversation_id, "user", "Shushan, review.")
    missed = db.add_message(conversation_id, "user", "Shushan, review again.")
    db.record_routing_decision(
        message_id=delivered,
        thread_id="conversation-1",
        participation_mode="DIRECT",
        explicit_recipients=["shushan"],
        inferred_recipients=[],
        selected_responders=["shushan"],
        excluded_responders={"roman": "selected_other_employee"},
        interruption_policy=None,
        reason="explicit_name_or_alias",
        router_version="test",
    )
    db.record_routing_decision(
        message_id=missed,
        thread_id="conversation-1",
        participation_mode="DIRECT",
        explicit_recipients=["shushan"],
        inferred_recipients=[],
        selected_responders=["roman"],
        excluded_responders={"shushan": "selected_other_employee"},
        interruption_policy=None,
        reason="bad_route",
        router_version="test",
    )

    metrics = {row.name: row for row in ProductMetricsService(db).metrics()}

    assert metrics["Доставка прямых обращений"].value == "50%"
    assert "доставлены: 1 / 2" in metrics["Доставка прямых обращений"].detail
    assert "промахов: 1" in metrics["Доставка прямых обращений"].detail


def test_handoff_delivery_metric_counts_started_handoffs(tmp_path):
    db = _database(tmp_path)
    db.log_event("contextual_handoff_scheduled", "roman->shushan")
    db.log_event("contextual_handoff_scheduled", "petr->roman")
    db.log_event("contextual_handoff_started", "roman->shushan; run=RUN-1")

    metrics = {row.name: row for row in ProductMetricsService(db).metrics()}

    assert metrics["Доставка handoff"].value == "50%"
    assert "1 / 2" in metrics["Доставка handoff"].detail


def test_open_question_metric_counts_thread_questions(tmp_path):
    db = _database(tmp_path)
    conversation_id = db.create_conversation()
    open_message_id = db.add_message(conversation_id, "user", "Шушанна, какие ограничения?")
    answered_message_id = db.add_message(conversation_id, "user", "Петр, что по аудиту?")
    answer_id = db.add_message(conversation_id, "petr", "Аудит ждет файлы.")
    db.create_thread_question(
        conversation_id=conversation_id,
        thread_id=f"conversation-{conversation_id}",
        question_message_id=open_message_id,
        question_text="Шушанна, какие ограничения?",
        assigned_agent_keys=["shushan"],
    )
    answered_id = db.create_thread_question(
        conversation_id=conversation_id,
        thread_id=f"conversation-{conversation_id}",
        question_message_id=answered_message_id,
        question_text="Петр, что по аудиту?",
        assigned_agent_keys=["petr"],
    )
    db.mark_thread_questions_answered(
        question_ids=[answered_id],
        answer_message_id=answer_id,
        answered_by_agent_key="petr",
    )

    metrics = {row.name: row for row in ProductMetricsService(db).metrics()}

    assert metrics["Открытые вопросы"].value == "1"
    assert "Зафиксировано: 2" in metrics["Открытые вопросы"].detail
    assert "ожидают принятия: 1" in metrics["Открытые вопросы"].detail
    assert "принято владельцем: 0" in metrics["Открытые вопросы"].detail
