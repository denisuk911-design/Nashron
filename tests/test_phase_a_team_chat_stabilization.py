from core.agent_directory import ChatAgent
from core.claim_evidence import ClaimEvidenceValidator, ClaimValidationResult
from core.database import Database
from core.response_cleaner import ResponseCleaner
from core.run_status import RunStatus
from core.structured_response import parse_agent_response
from core.team_routing import ParticipationMode, TeamRouter


def agents():
    return [
        ChatAgent("roman", "agent-roman", "Roman", "CODEX_CLI", ["DESIGN_ENGINEER"], "roman", "", None),
        ChatAgent("petr", "agent-petr", "Петр", "GEMINI_CLI", ["QA_ENGINEER"], "petr", "", None),
        ChatAgent("shushan", "agent-shushan", "Шушанна", "GEMINI_CLI", ["DOCUMENT_CONTROL_OFFICER"], "doc", "", None),
    ]


def test_direct_address_selects_only_the_named_employee():
    decision = TeamRouter().decide("Шушанна, проверь документ.", agents())

    assert decision.participation_mode == ParticipationMode.DIRECT
    assert decision.selected == ["shushan"]


def test_multi_direct_selects_only_the_two_named_employees():
    decision = TeamRouter().decide("Роман и Петр, проверьте каждый свою часть.", agents())

    assert decision.participation_mode == ParticipationMode.MULTI_DIRECT
    assert decision.selected == ["roman", "petr"]


def test_team_call_and_general_ping_select_all_active_employees():
    router = TeamRouter()

    team = router.decide("Команда, обсудите риски.", agents())
    ping = router.decide("Все тут?", agents())

    assert team.participation_mode == ParticipationMode.TEAM_CALL
    assert team.selected == ["roman", "petr", "shushan"]
    assert ping.participation_mode == ParticipationMode.GENERAL_TEAM_PING
    assert ping.selected == ["roman", "petr", "shushan"]


def test_info_only_does_not_invoke_employees():
    decision = TeamRouter().decide("Для сведения: проект переносим.", agents())

    assert decision.participation_mode == ParticipationMode.INFO_ONLY
    assert decision.selected == []


def test_continuation_keeps_the_previous_owner():
    decision = TeamRouter().decide("А по второму пункту?", agents(), active_owner=["shushan"])

    assert decision.participation_mode == ParticipationMode.CONTINUATION
    assert decision.selected == ["shushan"]


def test_blocked_or_no_chat_employee_is_not_replaced_by_roman():
    blocked = ChatAgent(
        "shushan",
        "agent-shushan",
        "Шушанна",
        "GEMINI_CLI",
        ["DOCUMENT_CONTROL_OFFICER"],
        "doc",
        "",
        None,
        "PAUSED",
    )
    decision = TeamRouter().decide("Шушанна, проверь.", [agents()[0], agents()[1]], blocked_agents=[blocked])

    assert decision.selected == []
    assert decision.reason == "addressed_employee_inactive_or_chat_denied"


def test_provider_filter_prevents_a_call_to_unready_employee():
    decision = TeamRouter().decide("Команда, что скажете?", agents(), eligible_keys={"roman"})

    assert decision.selected == ["roman"]
    assert "petr" in decision.excluded
    assert "shushan" in decision.excluded


def test_unsupported_claim_does_not_count_as_real_work():
    result = ClaimEvidenceValidator().validate("Я проверил файл.", {"checks": ["я так решил"]})

    assert result.result == ClaimValidationResult.CLAIM_UNSUPPORTED
    assert result.blocks_skill_update


def test_nested_structured_json_is_removed_from_user_visible_text():
    content = (
        "Файл проверен.\n\n"
        "```json\n"
        '{"schema_version":"1.0","agent_id":"agent-roman","role":"DESIGN_ENGINEER",'
        '"task_id":"TASK-1","run_id":"RUN-1","action":"MESSAGE","summary":"ok",'
        '"checks":[{"name":"ERC","result":"PASS","evidence_path":"reports/erc.txt"}],'
        '"files_read":["docs/a.md"]}\n'
        "```"
    )

    parsed = parse_agent_response(content)

    assert parsed.has_valid_envelope
    assert parsed.human_text == "Файл проверен."
    assert "evidence_path" not in parsed.human_text


def test_repeated_provider_block_is_collapsed():
    text = "Проверил файл.\nНашёл риск.\nПроверил файл.\nНашёл риск."

    assert ResponseCleaner.clean(text) == "Проверил файл. Нашёл риск."


def test_timed_out_run_is_not_recorded_as_success(tmp_path):
    db = Database(tmp_path / "team.sqlite3")
    db.initialize()
    db.ensure_project("project-default", "Team")
    task_id = db.create_task("project-default", "timeout", None, "1.0")
    run_id = db.create_agent_run(
        task_id=task_id,
        agent_id="agent-roman",
        agent_key="roman",
        logical_role="DESIGN_ENGINEER",
        provider="CODEX_CLI",
        prompt_hash=None,
        started_at="2026-08-10T12:00:00",
    )
    db.update_agent_run_status(run_id, RunStatus.WAITING_FOR_PROVIDER.value)
    db.finish_agent_run(
        run_id=run_id,
        ok=False,
        cancelled=False,
        returncode=None,
        duration_seconds=10,
        error="timeout",
        raw_response="",
        parsed_response=None,
        parse_errors=[],
        finished_at="2026-08-10T12:00:10",
        timed_out=True,
    )

    row = db.get_agent_run(run_id)
    assert row["status"] == RunStatus.TIMED_OUT.value
    assert row["recovery_state"] == RunStatus.TIMED_OUT.value
    assert row["ok"] == 0
