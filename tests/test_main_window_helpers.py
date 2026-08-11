from gui.main_window import MainWindow
from core.agent_directory import ChatAgent, mention_tokens
from core.autonomy import parse_autonomy_request
from core.team_routing import ParticipationMode, TeamRouter


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
