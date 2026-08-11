from core.agent_directory import ChatAgent
from core.team_routing import ManualRouting, ParticipationMode, TeamRouter


def _agents():
    return [
        ChatAgent("roman", "agent-roman", "Roman", "CODEX_CLI", ["DESIGN_ENGINEER"], "roman_2050", "", None),
        ChatAgent("petr", "agent-petr", "Petr", "GEMINI_CLI", ["QA_ENGINEER"], "petr_2050", "", None),
        ChatAgent(
            "shushan",
            "agent-shushan",
            "Шушанна",
            "GEMINI_CLI",
            ["DOCUMENT_CONTROL_OFFICER"],
            "document_control",
            "",
            None,
        ),
    ]


def test_direct_address_invokes_only_named_employee():
    decision = TeamRouter().decide("Шушанна, проверь ограничения.", _agents())

    assert decision.participation_mode == ParticipationMode.DIRECT
    assert decision.selected == ["shushan"]
    assert decision.excluded["roman"] == "selected_other_employee"
    assert decision.excluded["petr"] == "selected_other_employee"


def test_name_at_end_is_still_direct_address():
    decision = TeamRouter().decide("Что скажешь, Шушанна?", _agents())

    assert decision.selected == ["shushan"]


def test_two_named_employees_create_team_discussion_subset():
    decision = TeamRouter().decide("Роман и Петр, обсудите решение.", _agents())

    assert decision.participation_mode == ParticipationMode.TEAM_DISCUSSION
    assert decision.selected == ["roman", "petr"]
    assert "shushan" in decision.excluded


def test_team_call_selects_all_active_chat_employees():
    decision = TeamRouter().decide("Команда, какие риски в документации?", _agents())

    assert decision.participation_mode == ParticipationMode.TEAM_DISCUSSION
    assert decision.selected == ["roman", "petr", "shushan"]


def test_information_without_question_routes_to_silence():
    decision = TeamRouter().decide("Для сведения: проект переносим на другой компьютер.", _agents())

    assert decision.participation_mode == ParticipationMode.BROADCAST
    assert decision.selected == []


def test_continuation_uses_active_owner():
    decision = TeamRouter().decide("Проверь еще раз.", _agents(), active_owner=["shushan"])

    assert decision.participation_mode == ParticipationMode.CONTINUATION
    assert decision.selected == ["shushan"]


def test_auto_general_message_always_has_a_conversational_owner():
    decision = TeamRouter().decide("Привет, как дела?", _agents())

    assert len(decision.selected) == 1
    assert decision.reason == "default_conversational_owner"


def test_manual_recipient_is_enforced():
    decision = TeamRouter().decide(
        "Кто ответит?",
        _agents(),
        manual=ManualRouting(recipient_key="petr", only_selected=True),
    )

    assert decision.selected == ["petr"]
    assert decision.reason == "manual_recipient"


def test_manual_no_response_is_enforced():
    decision = TeamRouter().decide("Запомните новый стандарт.", _agents(), manual=ManualRouting(no_response=True))

    assert decision.selected == []
    assert decision.reason == "manual_no_response"
