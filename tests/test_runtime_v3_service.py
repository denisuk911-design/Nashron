from core.agent_directory import ChatAgent
from core.runtime_v3_service import RuntimeV3GoalService


def test_runtime_v3_goal_service_returns_user_friendly_projection(tmp_path):
    service = RuntimeV3GoalService(tmp_path)
    agents = [
        ChatAgent("roman", "agent-roman", "Roman", "CODEX_CLI", ["DESIGN_ENGINEER"], "roman_2050", "", None),
        ChatAgent("petr", "agent-petr", "Petr", "GEMINI_CLI", ["QA_ENGINEER"], "petr_2050", "", None),
    ]

    result = service.run_goal("org", "Подготовьте техническую спецификацию преобразователя 24 В -> 12 В, 5 А и подберите подходящий контроллер.", agents)

    assert result.ok
    assert "Цель выполнена." in result.summary
    assert "Артефакты:" in result.summary
    assert "Источники/доказательства:" in result.summary
    assert "DRAFT" not in result.summary
    assert "goal-" not in result.summary
    assert result.state.artifacts


def test_runtime_v3_goal_service_keeps_social_chat_out_of_workflow(tmp_path):
    service = RuntimeV3GoalService(tmp_path)

    result = service.run_goal("org", "привет, как дела?", [])

    assert result.ok
    assert result.state.work_items == {}
    assert "План: 0 рабочих пункта." in result.summary
