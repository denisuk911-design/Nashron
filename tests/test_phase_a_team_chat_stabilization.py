from types import SimpleNamespace

from core.agent_directory import ChatAgent, mention_tokens
from core.claim_evidence import ClaimEvidenceValidator, ClaimValidationResult
from core.database import Database
from core.response_cleaner import ResponseCleaner
from core.response_splitter import ResponseSplitter
from core.run_status import RunStatus
from core.structured_response import parse_agent_response
from core.team_routing import ParticipationMode, TeamRouter
from gui.main_window import MainWindow


def agents():
    return [
        ChatAgent("roman", "agent-roman", "Roman", "CODEX_CLI", ["DESIGN_ENGINEER"], "roman", "", None),
        ChatAgent("petr", "agent-petr", "Петр", "GEMINI_CLI", ["QA_ENGINEER"], "petr", "", None),
        ChatAgent("shushan", "agent-shushan", "Шушанна", "GEMINI_CLI", ["DOCUMENT_CONTROL_OFFICER"], "doc", "", None),
    ]


def test_production_routing_path_resolves_short_aliases_before_thread_owner():
    class FakeDatabase:
        def log_event(self, *_args):
            pass

    window = MainWindow.__new__(MainWindow)
    window.database = FakeDatabase()
    window.team_router = TeamRouter()
    window.last_addressed_agent_keys = ["roman"]
    window.exchange_responded_agent_keys = set()
    window._chat_agents = agents

    assert MainWindow._route_agents(window, "А Шуша?") == ["shushan"]
    assert MainWindow._route_agents(window, "Шушанна?") == ["shushan"]
    assert MainWindow._route_agents(window, "А Пётр?") == ["petr"]
    assert MainWindow._route_agents(window, "А Роман?") == ["roman"]

    window.exchange_responded_agent_keys = {"roman"}
    assert MainWindow._route_agents(window, "Остальные что?") == ["petr", "shushan"]

    window.last_addressed_agent_keys = ["shushan"]
    assert MainWindow._route_agents(window, "А ограничения?") == ["shushan"]
    assert MainWindow._route_agents(window, "Пётр, что думаешь?") == ["petr"]


def test_short_alias_is_available_without_hardcoding_shushanna_in_router():
    shushan = next(agent for agent in agents() if agent.key == "shushan")
    assert "шуша" in mention_tokens(shushan)
    assert "шуш" in mention_tokens(shushan)
    assert TeamRouter().decide("А Шуша?", agents(), active_owner=["roman"]).selected == ["shushan"]


def test_dynamic_employee_speaker_label_is_not_misclassified_as_roman():
    parts = ResponseSplitter.split(
        "Шушанна: Файл проверен.",
        "shushan",
        {"Шушанна": "shushan", "Роман": "roman", "Петр": "petr"},
    )

    assert parts == [ResponseSplitter.split("Файл проверен.", "shushan")[0]]


def test_main_window_creates_workers_only_for_routing_selection(monkeypatch):
    class FakeDatabase:
        def log_event(self, *_args):
            pass

    class Signal:
        def connect(self, _callback):
            pass

    created = []

    class FakeWorker:
        def __init__(self, _builder, _client, _conversation_id, _message, _allow_tools, **kwargs):
            self.agent_key = kwargs["agent_key"]
            self.run_id = kwargs["run_id"]
            self.conversation_id = _conversation_id
            self.delta_received = Signal()
            self.status_received = Signal()
            self.run_status_received = Signal()
            self.finished_with_result = Signal()
            created.append(self.agent_key)

        def start(self):
            pass

    class FakeChat:
        def reset_stream(self):
            pass

        def set_stream_role(self, _key):
            pass

        def set_busy(self, *_args):
            pass

        def append_roman_delta(self, *_args):
            pass

        def set_activity_status(self, *_args):
            pass

    monkeypatch.setattr("gui.main_window.GenerateWorker", FakeWorker)
    monkeypatch.setattr("gui.main_window.PromptBuilder", lambda *_args, **_kwargs: object())

    window = MainWindow.__new__(MainWindow)
    window.database = FakeDatabase()
    window.team_router = TeamRouter()
    window.last_addressed_agent_keys = ["roman"]
    window.exchange_responded_agent_keys = set()
    window._chat_agents = agents
    window.chat = FakeChat()
    window.pending_agent_keys = MainWindow._route_agents(window, "А Шуша?")
    assert window.pending_agent_keys == ["shushan"]
    window.authorized_worker_keys = set(window.pending_agent_keys)
    window.pending_user_message = "А Шуша?"
    window.autonomous_active = False
    window.autonomous_goal = ""
    window.autonomous_turn = 0
    window.autonomous_complete_on_goal = False
    window.exchange_turn = 0
    window.exchange_turn_limit = 1
    window.exchange_responded_agent_keys = set()
    window.current_agent_key = "roman"
    window.pending_contextual_handoffs = []
    window.last_peer_context = ""
    window.settings = {}
    window.conversation_id = 1
    window.paths = SimpleNamespace(system_prompt_path="unused", timeline_path="unused")
    window.identity_service = object()
    window.skill_service = object()
    window.knowledge_service = object()
    window.standards_service = object()
    window.thread_service = SimpleNamespace(prompt_lines=lambda: [])
    window.task_orchestrator = SimpleNamespace(
        start_run=lambda _agent_key: SimpleNamespace(run_id="RUN-1", task_id="TASK-1")
    )
    window._allow_local_tools_for_agent = lambda _agent_key: False
    window._client_for_agent = lambda _agent_key: object()
    window._mark_contextual_handoff_started = lambda *_args: None
    window._start_response_latency_timers = lambda *_args: None

    MainWindow._start_next_agent_run(window)

    assert window.last_routing_decision.selected == ["shushan"]
    assert created == ["shushan"]


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
