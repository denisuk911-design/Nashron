from pathlib import Path

from gui.main_window import MainWindow
from core.agent_directory import ChatAgent, chat_display_name, mention_tokens
from core.autonomy import parse_autonomy_request
from core.codex_client import CodexClient
from core.gemini_client import GeminiClient
from core.runtime_v3_service import RuntimeV3GoalResult
from core.team_routing import ParticipationMode, TeamRouter
from runtime_v3.models import RuntimeState


def test_autonomous_done_marker_can_be_inline():
    content = "Правило принято. AUTO_DONE"

    assert MainWindow._signals_autonomous_done(content)
    assert MainWindow._strip_autonomous_done(content) == "Правило принято."


def test_repetition_signature_detects_similar_text():
    left = MainWindow._content_signature("Принял, работаем по схеме skill-first, проверка, исполнение, улучшение.")
    right = MainWindow._content_signature("Понял, схема skill-first, проверка, исполнение, улучшение принята.")

    assert MainWindow._signature_similarity(left, right) >= 0.70


def test_exchange_repetition_detector_stops_second_similar_answer():
    window = MainWindow.__new__(MainWindow)
    window.exchange_fingerprints = []

    first = "Фиксирую опыт в правило, добавляю чек-лист и применяю его на следующих задачах."
    second = "Добавляю опыт в правило и чек-лист, потом применяю это на следующих задачах."

    assert not MainWindow._is_repeated_exchange_content(window, first)
    assert MainWindow._is_repeated_exchange_content(window, second)


def test_dynamic_employee_mentions_include_name_cases():
    agent = ChatAgent(
        key="employee-8556d8",
        agent_id="agent-employee-8556d8",
        display_name="Шушанна",
        provider_id="GEMINI_CLI",
        roles=["DOCUMENT_CONTROL_OFFICER"],
        persona_id="document_control",
        description="",
        avatar_path=None,
    )

    tokens = mention_tokens(agent)

    assert "шушанна" in tokens
    assert "шушанне" in tokens
    assert "шушанну" in tokens


def test_chat_display_name_replaces_role_placeholder_with_short_human_name():
    assert chat_display_name(
        display_name="Инженер",
        full_name="Олена Коваль",
        preferred_name="",
        primary_role="DESIGN_ENGINEER",
    ) == "Олена"
    assert chat_display_name(
        display_name="Engineer",
        full_name="Alex Brown",
        preferred_name="Sasha",
        primary_role="DESIGN_ENGINEER",
    ) == "Sasha"


def test_followup_routes_to_last_addressed_employee():
    class FakeDatabase:
        def log_event(self, *_args):
            pass

    window = MainWindow.__new__(MainWindow)
    window.database = FakeDatabase()
    window.team_router = TeamRouter()
    window.last_addressed_agent_keys = ["employee-8556d8"]
    window._chat_agents = lambda: [
        ChatAgent("petr", "agent-petr", "Petr", "GEMINI_CLI", ["QA_ENGINEER"], "petr_2050", "", None),
        ChatAgent("roman", "agent-roman", "Roman", "CODEX_CLI", ["DESIGN_ENGINEER"], "roman_2050", "", None),
        ChatAgent("employee-8556d8", "agent-employee-8556d8", "Шушанна", "GEMINI_CLI", ["DOCUMENT_CONTROL_OFFICER"], "document_control", "", None),
    ]

    assert MainWindow._route_agents(window, "попробуй еще раз") == ["employee-8556d8"]
    assert MainWindow._route_agents(window, "Шушанне нужно создать документ") == ["employee-8556d8"]


def test_direct_address_ignores_same_named_employee_in_another_organization(monkeypatch):
    class FakeDatabase:
        def log_event(self, *_args):
            pass

    local_agent = ChatAgent(
        "employee-local",
        "agent-employee-local",
        "Диана Вебер",
        "GEMINI_CLI",
        ["CUSTOM_ANALYST"],
        "local-diana",
        "",
        None,
    )
    foreign_agent = ChatAgent(
        "employee-foreign",
        "agent-employee-foreign",
        "Диана Вебер",
        "CODEX_CLI",
        ["CUSTOM_ANALYST"],
        "foreign-diana",
        "",
        None,
    )
    requested_organizations = []

    def fake_list_chat_agents(_database, *, active_only=True, include_without_chat=False, organization_id=None):
        requested_organizations.append(organization_id)
        return [local_agent] if organization_id == "organization-local" else [local_agent, foreign_agent]

    monkeypatch.setattr("gui.main_window.list_chat_agents", fake_list_chat_agents)
    window = MainWindow.__new__(MainWindow)
    window.database = FakeDatabase()
    window.team_router = TeamRouter()
    window.active_organization_id = "organization-local"
    window.last_addressed_agent_keys = []
    window._chat_agents = lambda: [local_agent]

    assert MainWindow._route_agents(window, "Диана Вебер, как дела?") == ["employee-local"]
    assert requested_organizations == ["organization-local"]


def test_direct_work_task_for_dynamic_employee_is_not_auto_expanded():
    class FakeDatabase:
        def log_event(self, *_args):
            pass

    window = MainWindow.__new__(MainWindow)
    window.database = FakeDatabase()
    window.team_router = TeamRouter()
    window.last_addressed_agent_keys = []
    window._chat_agents = lambda: [
        ChatAgent("roman", "agent-roman", "Roman", "CODEX_CLI", ["DESIGN_ENGINEER"], "roman_2050", "", None),
        ChatAgent("petr", "agent-petr", "Petr", "GEMINI_CLI", ["QA_ENGINEER"], "petr_2050", "", None),
        ChatAgent("employee-8556d8", "agent-employee-8556d8", "Шушанна", "GEMINI_CLI", ["DOCUMENT_CONTROL_OFFICER"], "document_control", "", None),
    ]

    text = "Шушанна, создай документ"
    agent_keys = MainWindow._route_agents(window, text)
    autonomy = parse_autonomy_request(text)

    assert not autonomy.enabled
    assert agent_keys == ["employee-8556d8"]
    assert MainWindow._autonomous_initial_agents(window, agent_keys, autonomy) == ["employee-8556d8"]


def test_explicit_autonomous_goal_with_one_named_employee_stays_pinned():
    class FakeDatabase:
        def log_event(self, *_args):
            pass

    window = MainWindow.__new__(MainWindow)
    window.database = FakeDatabase()
    window.team_router = TeamRouter()
    window.last_addressed_agent_keys = []
    window._chat_agents = lambda: [
        ChatAgent("roman", "agent-roman", "Roman", "CODEX_CLI", ["DESIGN_ENGINEER"], "roman_2050", "", None),
        ChatAgent("petr", "agent-petr", "Petr", "GEMINI_CLI", ["QA_ENGINEER"], "petr_2050", "", None),
        ChatAgent("employee-8556d8", "agent-employee-8556d8", "Шушанна", "GEMINI_CLI", ["DOCUMENT_CONTROL_OFFICER"], "document_control", "", None),
    ]

    text = "Цель: Шушанна, создай документ и остановись"
    agent_keys = MainWindow._route_agents(window, text)
    autonomy = parse_autonomy_request(text)

    assert autonomy.enabled
    assert window.last_routing_decision.participation_mode == ParticipationMode.DIRECT
    assert MainWindow._autonomous_initial_agents(window, agent_keys, autonomy) == ["employee-8556d8"]


def test_manual_goal_mode_forces_autonomous_goal():
    class FakeChat:
        def goal_mode_requested(self):
            return True

    window = MainWindow.__new__(MainWindow)
    window.chat = FakeChat()

    autonomy = MainWindow._autonomy_from_text(window, "Создайте документ и проверьте его")

    assert autonomy.enabled
    assert autonomy.complete_on_goal
    assert autonomy.goal == "Создайте документ и проверьте его"


def test_runtime_v3_goal_mode_runs_service_and_records_result(tmp_path):
    events = []

    class FakeChat:
        def __init__(self):
            self.messages = []
            self.statuses = []
            self.busy = []
            self.typing = []
            self.bound = []

        def goal_mode_requested(self):
            return True

        def set_goal_status(self, *args):
            self.statuses.append(args)

        def set_busy(self, value):
            self.busy.append(value)

        def start_agent_typing(self, *args):
            self.typing.append(("start", args))

        def stop_agent_typing(self, *args):
            self.typing.append(("stop", args))

        def add_message(self, role, text):
            item = object()
            self.messages.append((role, text, item))
            return item

        def bind_message_id(self, item, message_id):
            self.bound.append((item, message_id))

    class FakeDatabase:
        def add_message(self, conversation_id, role, text):
            events.append(("message", conversation_id, role, text))
            return len(events)

        def log_event(self, *args):
            events.append(("event", *args))

    class FakeSound:
        def play_receive(self):
            events.append(("receive",))

    class FakeService:
        def run_goal(self, organization_id, objective, agents):
            events.append(("run_goal", organization_id, objective, list(agents)))
            return RuntimeV3GoalResult(True, "Цель выполнена.\nАртефакты: 1.", RuntimeState(organization_id), tmp_path)

    window = MainWindow.__new__(MainWindow)
    window.settings = {"developer_mode": True, "runtime_engine": "HYBRID_V3_EXPERIMENTAL"}
    window.chat = FakeChat()
    window.database = FakeDatabase()
    window.chat_sound_service = FakeSound()
    window.runtime_v3_goal_service = FakeService()
    window.active_organization_id = "organization-test"
    window.conversation_id = "conversation-test"
    window.show_work_view = lambda: events.append(("show_work",))
    window.logger = type("Logger", (), {"exception": lambda *_args: None})()
    window._chat_agents = lambda: [
        ChatAgent("roman", "agent-roman", "Roman", "CODEX_CLI", ["DESIGN_ENGINEER"], "roman_2050", "", None),
    ]

    handled = MainWindow._try_start_runtime_v3_goal(window, "Цель: создать спецификацию", 7)

    assert handled
    assert events[0][0] == "show_work"
    assert any(event[0] == "run_goal" for event in events)
    run_event = next(event for event in events if event[0] == "run_goal")
    assert run_event[1:3] == ("organization-test", "Цель: создать спецификацию")
    assert ("event", "runtime_v3_goal_completed", "message_id=7; artifacts=0; evidence=0") in events
    assert any(event[:3] == ("message", "conversation-test", "runtime_v3") for event in events)
    assert ("receive",) in events
    assert window.chat.busy == [True, False]
    assert window.chat.statuses[0] == (True, "Цель: создать спецификацию", 0)
    assert window.chat.statuses[-1] == (False,)


def test_runtime_v3_goal_mode_requires_goal_service():
    class FakeChat:
        def goal_mode_requested(self):
            return True

    window = MainWindow.__new__(MainWindow)
    window.settings = {"developer_mode": False, "runtime_engine": "HYBRID_V3_EXPERIMENTAL"}
    window.chat = FakeChat()
    window.active_organization_id = "organization-test"
    window.runtime_v3_goal_service = None

    assert not MainWindow._try_start_runtime_v3_goal(window, "Цель: создать спецификацию", 7)


def test_goal_turn_limit_has_safe_minimum():
    window = MainWindow.__new__(MainWindow)
    window.settings = {"goal_turn_limit": 3}

    assert MainWindow._goal_turn_limit(window) == 20


def test_message_sent_while_stop_is_finishing_is_queued_for_a_new_run():
    class FakeDatabase:
        def __init__(self):
            self.events = []

        def log_event(self, *args):
            self.events.append(args)

    class FakeWorker:
        agent_key = "roman"

        def isRunning(self):
            return True

    database = FakeDatabase()
    window = MainWindow.__new__(MainWindow)
    window.database = database
    window.worker = FakeWorker()
    window.cancellation_in_progress = True
    window.interrupting_current_run = False
    window.current_agent_key = "roman"
    window.queued_user_message = None
    window._clear_dead_worker = lambda: None
    window._add_user_message = lambda text: 42

    MainWindow.send_message(window, "Петр, проверь после отмены")

    assert window.queued_user_message == ("Петр, проверь после отмены", 42)
    assert database.events == [("message_queued_during_cancellation", "roman")]
def test_contextual_handoff_can_target_dynamic_employee():
    class FakeDatabase:
        def __init__(self):
            self.events = []

        def log_event(self, *args):
            self.events.append(args)

    database = FakeDatabase()
    window = MainWindow.__new__(MainWindow)
    window.database = database
    window.team_router = TeamRouter()
    window.autonomous_active = False
    window.exchange_turn = 1
    window.exchange_turn_limit = 3
    window.exchange_responded_agent_keys = {"roman"}
    window.pending_agent_keys = []
    window.autonomous_goal = ""
    window.pending_user_message = "Prepare documentation."
    window._chat_agents = lambda: [
        ChatAgent("roman", "agent-roman", "Roman", "CODEX_CLI", ["DESIGN_ENGINEER"], "roman_2050", "", None),
        ChatAgent("shushan", "agent-shushan", "Shushan", "GEMINI_CLI", ["DOCUMENT_CONTROL_OFFICER"], "document_control", "", None),
    ]

    MainWindow._schedule_contextual_next_turn(window, "roman", "Shushan, review the document before release.")

    assert window.pending_agent_keys == ["shushan"]
    assert database.events == [("contextual_handoff_scheduled", "roman->shushan")]


def test_contextual_handoff_without_named_employee_is_not_guessed():
    class FakeDatabase:
        def log_event(self, *_args):
            pass

    window = MainWindow.__new__(MainWindow)
    window.database = FakeDatabase()
    window.team_router = TeamRouter()
    window.autonomous_active = False
    window.exchange_turn = 1
    window.exchange_turn_limit = 3
    window.exchange_responded_agent_keys = {"roman"}
    window.pending_agent_keys = []
    window.autonomous_goal = ""
    window.pending_user_message = "Prepare documentation."
    window._chat_agents = lambda: [
        ChatAgent("roman", "agent-roman", "Roman", "CODEX_CLI", ["DESIGN_ENGINEER"], "roman_2050", "", None),
        ChatAgent("shushan", "agent-shushan", "Shushan", "GEMINI_CLI", ["DOCUMENT_CONTROL_OFFICER"], "document_control", "", None),
    ]

    MainWindow._schedule_contextual_next_turn(window, "roman", "Needs review before release.")

    assert window.pending_agent_keys == []


def test_contextual_handoff_started_is_recorded_once():
    class FakeDatabase:
        def __init__(self):
            self.events = []

        def log_event(self, *args):
            self.events.append(args)

    database = FakeDatabase()
    window = MainWindow.__new__(MainWindow)
    window.database = database
    window.pending_contextual_handoffs = [("roman", "shushan"), ("petr", "roman")]

    MainWindow._mark_contextual_handoff_started(window, "shushan", "RUN-1")

    assert window.pending_contextual_handoffs == [("petr", "roman")]
    assert database.events == [("contextual_handoff_started", "roman->shushan; run=RUN-1")]


def test_send_renders_and_clears_before_persistence_or_routing(monkeypatch):
    events = []
    callbacks = []

    class FakeChat:
        def reset_stream(self):
            events.append("reset")

        def add_message(self, role, text):
            events.append(("bubble", role, text))
            return object()

    class FakeSound:
        def play_send(self):
            events.append("sound")

    class FakeDatabase:
        def add_message(self, *_args):
            events.append("persisted")

    window = MainWindow.__new__(MainWindow)
    window.worker = None
    window.chat = FakeChat()
    window.chat_sound_service = FakeSound()
    window.database = FakeDatabase()
    window._clear_dead_worker = lambda: None
    window._identity_is_ready = lambda: True
    window._clear_composer_input = lambda: events.append("cleared")
    monkeypatch.setattr("gui.main_window.QTimer.singleShot", lambda _delay, callback: callbacks.append(callback))

    MainWindow.send_message(window, "Короткое сообщение")

    assert events == ["reset", ("bubble", "user", "Короткое сообщение"), "cleared", "sound"]
    assert len(callbacks) == 1
    assert "send_clicked" in window._active_send_trace.stages_ms
    assert "user_bubble_created" in window._active_send_trace.stages_ms
    assert window._active_send_trace.payload()["bubble_budget_ok"]


def test_each_parallel_agent_gets_an_isolated_cli_client(tmp_path):
    class Route:
        def __init__(self, provider):
            self.provider = provider

    class Router:
        def route(self, agent_key):
            return Route("GEMINI_CLI" if agent_key.endswith("gemini") else "CODEX_CLI")

    window = MainWindow.__new__(MainWindow)
    window.agent_router = Router()
    window.codex_client = CodexClient(executable="codex", workspace=tmp_path / "codex", timeout_seconds=91)
    window.gemini_client = GeminiClient(
        executable="gemini",
        workspace=tmp_path / "gemini",
        timeout_seconds=92,
        api_key="test-key",
        model="test-model",
    )

    codex_a = MainWindow._client_for_agent(window, "employee-a")
    codex_b = MainWindow._client_for_agent(window, "employee-b")
    gemini = MainWindow._client_for_agent(window, "employee-gemini")

    assert codex_a is not codex_b
    assert codex_a is not window.codex_client
    assert codex_a.workspace == Path(tmp_path / "codex" / "agents" / "employee-a")
    assert codex_b.workspace == Path(tmp_path / "codex" / "agents" / "employee-b")
    assert codex_a.timeout_seconds == 91
    assert gemini is not window.gemini_client
    assert gemini.workspace == Path(tmp_path / "gemini" / "agents" / "employee-gemini")
    assert gemini.timeout_seconds == 92
    assert gemini.api_key == "test-key"
    assert gemini.model == "test-model"
