from core.agent_directory import ChatAgent
from core.models import CodexResult
from core.runtime_v3_service import RuntimeV3GoalService


class FakeProviderClient:
    def __init__(self, result: CodexResult) -> None:
        self.result = result
        self.prompts: list[str] = []

    def generate(self, prompt: str, allow_full_access: bool = False) -> CodexResult:
        self.prompts.append(prompt)
        return self.result


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


def test_runtime_v3_goal_uses_provider_action_then_real_tool_observation(tmp_path):
    provider = FakeProviderClient(
        CodexResult(
            True,
            '{"action":"filesystem.write","path":"v3_provider_output/spec.md","content":"# Specification\\ncontroller: verified"}',
            0,
            0.1,
        )
    )
    service = RuntimeV3GoalService(tmp_path, provider_clients={"CODEX_CLI": provider})
    agents = [ChatAgent("roman", "agent-roman", "Roman", "CODEX_CLI", ["DESIGN_ENGINEER"], "roman_2050", "", None)]

    result = service.run_goal("org", "Create one file as a simple note", agents)

    assert result.ok
    assert len(provider.prompts) == 1
    assert len(result.state.actions) == 1
    assert len(result.state.observations) == 1
    assert len(result.state.artifacts) == 1
    observation = next(iter(result.state.observations.values()))
    assert observation.status.value == "OK"
    assert observation.summary == "wrote spec.md"


def test_runtime_v3_provider_failure_blocks_work_without_artifact(tmp_path):
    provider = FakeProviderClient(CodexResult(False, "", 1, 0.1, "provider timeout", timed_out=True))
    service = RuntimeV3GoalService(tmp_path, provider_clients={"CODEX_CLI": provider})
    agents = [ChatAgent("roman", "agent-roman", "Roman", "CODEX_CLI", ["DESIGN_ENGINEER"], "roman_2050", "", None)]

    result = service.run_goal("org", "Create one file as a simple note", agents)

    assert not result.ok
    assert result.state.artifacts == {}
    assert result.state.actions == {}
    assert any(item.status.value == "BLOCKED" for item in result.state.work_items.values())
    assert any(item.evidence_type == "PROVIDER_FAILURE" and not item.passed for item in result.state.evidence.values())


def test_runtime_v3_goal_service_keeps_social_chat_out_of_workflow(tmp_path):
    service = RuntimeV3GoalService(tmp_path)

    result = service.run_goal("org", "привет, как дела?", [])

    assert result.ok
    assert result.state.work_items == {}
    assert "План: 0 рабочих пункта." in result.summary
