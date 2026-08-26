from core.agent_directory import ChatAgent
from core.provider_execution import ProviderExecutionResult
from core.runtime_v3_service import RuntimeV3GoalService
from runtime_v3.agent_runtime import ProviderAgentRuntime
from runtime_v3.engine import HybridWorkflowEngine
from runtime_v3.models import EmployeeBinding
from runtime_v3.models import load_state


class FakeProviderAdapter:
    def __init__(self, provider_id: str, content: str = "", error: str = "") -> None:
        self.provider_id = provider_id
        self.content = content
        self.error = error
        self.prompts: list[str] = []

    def execute(self, request) -> ProviderExecutionResult:
        self.prompts.append(request.prompt)
        return ProviderExecutionResult(
            request.run_id,
            request.employee_id,
            self.provider_id,
            request.work_item_id,
            "FAILED" if self.error else "SUCCEEDED",
            request.started_at,
            "2026-08-25T00:00:01+00:00",
            self.content,
            self.error,
        )


class GoldenProviderAdapter(FakeProviderAdapter):
    def execute(self, request) -> ProviderExecutionResult:
        if "controller research" in request.prompt.lower():
            self.content = (
                '{"action":"filesystem.write","path":"v3_provider_output/controller_research.md",'
                '"content":"# Controller research\\nCandidate: TI LM5146.\\n'
                'Source evidence: https://www.ti.com/lit/ds/symlink/lm5146.pdf"}'
            )
        else:
            self.content = (
                '{"action":"filesystem.write","path":"v3_provider_output/specification.md",'
                '"content":"# Technical specification\\nInput: 24 V.\\nOutput: 12 V, 5 A.\\nController: TI LM5146."}'
            )
        return super().execute(request)


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
    provider = FakeProviderAdapter(
        "CODEX_CLI",
        '{"action":"filesystem.write","path":"v3_provider_output/spec.md","content":"# Specification\\ncontroller: verified"}',
    )
    service = RuntimeV3GoalService(tmp_path, provider_adapters={"CODEX_CLI": provider})
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
    run = next(iter(result.state.provider_runs.values()))
    assert run.action_count == 1
    restored = load_state(result.workspace_root / "checkpoints" / "state.json")
    assert restored.provider_runs[run.run_id].provider_id == "CODEX_CLI"


def test_runtime_v3_golden_goal_uses_two_provider_items_then_rework_and_final_review(tmp_path):
    provider = GoldenProviderAdapter("CODEX_CLI")
    service = RuntimeV3GoalService(tmp_path, provider_adapters={"CODEX_CLI": provider})
    agents = [
        ChatAgent("engineer", "agent-engineer", "Engineer", "CODEX_CLI", ["DESIGN_ENGINEER"], "engineer", "", None),
        ChatAgent("researcher", "agent-researcher", "Researcher", "CODEX_CLI", ["RESEARCH_ASSISTANT"], "researcher", "", None),
        ChatAgent("reviewer", "agent-reviewer", "Reviewer", "CODEX_CLI", ["QA_ENGINEER"], "reviewer", "", None),
    ]

    result = service.run_goal("org", "Prepare technical specification for 24 V to 12 V 5 A converter and select a controller.", agents)

    assert result.ok
    assert len(result.state.work_items) == 3
    assert len(provider.prompts) == 2
    assert len(result.state.provider_runs) == 2
    assert all(run.status == "SUCCEEDED" and run.action_count == 1 for run in result.state.provider_runs.values())
    assert len(result.state.findings) >= 1
    assert len(result.state.actions) >= 5
    assert len(result.state.observations) >= 5
    assert any(
        artifact.artifact_type == "TECHNICAL_SPECIFICATION" and artifact.revision >= 2
        for artifact in result.state.artifacts.values()
    )
    assert any(evidence.evidence_type == "SOURCE_RECORD" and evidence.passed for evidence in result.state.evidence.values())
    assert all(item.status.value == "COMPLETED" for item in result.state.work_items.values())


def test_runtime_v3_provider_failure_blocks_work_without_artifact(tmp_path):
    provider = FakeProviderAdapter("CODEX_CLI", error="provider timeout")
    service = RuntimeV3GoalService(tmp_path, provider_adapters={"CODEX_CLI": provider})
    agents = [ChatAgent("roman", "agent-roman", "Roman", "CODEX_CLI", ["DESIGN_ENGINEER"], "roman_2050", "", None)]

    result = service.run_goal("org", "Create one file as a simple note", agents)

    assert not result.ok
    assert result.state.artifacts == {}
    assert result.state.actions == {}
    assert any(item.status.value == "BLOCKED" for item in result.state.work_items.values())
    assert any(item.evidence_type == "PROVIDER_FAILURE" and not item.passed for item in result.state.evidence.values())
    run = next(iter(result.state.provider_runs.values()))
    assert run.status == "FAILED"
    assert run.action_count == 0


def test_runtime_v3_service_enforces_core_permission_snapshot_before_write(tmp_path):
    provider = FakeProviderAdapter(
        "CODEX_CLI",
        '{"action":"filesystem.write","path":"v3_provider_output/blocked.md","content":"blocked"}',
    )
    service = RuntimeV3GoalService(
        tmp_path, provider_adapters={"CODEX_CLI": provider}, permission_resolver=lambda _agent_id: {"READ_WORKSPACE"}
    )
    agents = [ChatAgent("roman", "agent-roman", "Roman", "CODEX_CLI", ["DESIGN_ENGINEER"], "roman_2050", "", None)]

    result = service.run_goal("org", "Create one file as a simple note", agents)

    assert not result.ok
    assert not result.state.artifacts
    assert any("permission denied" in item.summary for item in result.state.observations.values())


def test_runtime_v3_second_provider_adapter_uses_the_same_contract(tmp_path):
    provider = FakeProviderAdapter(
        "SECOND_PROVIDER",
        '{"action":"filesystem.write","path":"v3_provider_output/second.md","content":"# Second adapter\\ncontroller: verified"}',
    )
    service = RuntimeV3GoalService(tmp_path, provider_adapters={"SECOND_PROVIDER": provider})
    agents = [ChatAgent("other", "agent-other", "Other", "SECOND_PROVIDER", ["DESIGN_ENGINEER"], "other", "", None)]

    result = service.run_goal("org", "Create one file as a simple note", agents)

    assert result.ok
    run = next(iter(result.state.provider_runs.values()))
    assert run.provider_id == "SECOND_PROVIDER"
    assert run.action_count == 1


def test_runtime_v3_skips_provider_without_required_capabilities(tmp_path):
    class Profile:
        def supports(self, required):
            return False

    class UnsupportedProvider(FakeProviderAdapter):
        capability_profile = Profile()

    blocked = UnsupportedProvider("CODEX_CLI", '{"action":"filesystem.write","path":"v3_provider_output/no.md","content":"no"}')
    recovered = FakeProviderAdapter("GEMINI_CLI", '{"action":"filesystem.write","path":"v3_provider_output/yes.md","content":"# Result\\ncontroller: verified"}')
    service = RuntimeV3GoalService(tmp_path, provider_adapters={"CODEX_CLI": blocked, "GEMINI_CLI": recovered})
    agents = [ChatAgent("roman", "agent-roman", "Roman", "CODEX_CLI", ["DESIGN_ENGINEER"], "roman_2050", "", None)]

    result = service.run_goal("org", "Create one file as a simple note", agents)

    assert result.ok
    assert all(run.provider_id != "CODEX_CLI" for run in result.state.provider_runs.values())


def test_runtime_v3_fails_over_to_next_provider_adapter(tmp_path):
    failed = FakeProviderAdapter("CODEX_CLI", error="primary unavailable")
    recovered = FakeProviderAdapter(
        "GEMINI_CLI",
        '{"action":"filesystem.write","path":"v3_provider_output/failover.md","content":"# Failover\\ncontroller: verified"}',
    )
    service = RuntimeV3GoalService(tmp_path, provider_adapters={"CODEX_CLI": failed, "GEMINI_CLI": recovered})
    agents = [ChatAgent("roman", "agent-roman", "Roman", "CODEX_CLI", ["DESIGN_ENGINEER"], "roman_2050", "", None)]

    result = service.run_goal("org", "Create one file as a simple note", agents)

    assert result.ok
    assert len(result.state.provider_runs) == 2
    assert [run.status for run in result.state.provider_runs.values()] == ["FAILED", "SUCCEEDED"]
    assert result.state.artifacts


def test_runtime_v3_resume_retries_provider_blocked_work_item(tmp_path):
    adapter = FakeProviderAdapter("CODEX_CLI", error="temporary provider failure")
    employee = EmployeeBinding("engineer", "Engineer", "engineering", ["engineering"], "CODEX_CLI")
    runtime = ProviderAgentRuntime({"CODEX_CLI": adapter}, {"engineer": "CODEX_CLI"})
    engine = HybridWorkflowEngine("org", [employee], tmp_path, agent_runtime=runtime)
    goal = engine.create_goal("Create one file as a simple note")
    engine.create_plan(goal.goal_id)
    engine.start(goal.goal_id)
    assert any(item.status.value == "BLOCKED" for item in engine.state.work_items.values())

    adapter.error = ""
    adapter.content = '{"action":"filesystem.write","path":"v3_provider_output/resumed.md","content":"# Resumed\\ncontroller: verified"}'
    resumed = HybridWorkflowEngine("org", [employee], tmp_path, agent_runtime=ProviderAgentRuntime({"CODEX_CLI": adapter}, {"engineer": "CODEX_CLI"}))
    resumed.repository = engine.repository
    state = resumed.resume()

    assert state.goals[goal.goal_id].status.value == "COMPLETED"
    # First failure is retried autonomously; restart performs the final recovery.
    assert len(state.provider_runs) == 3
    assert [run.status for run in state.provider_runs.values()] == ["FAILED", "FAILED", "SUCCEEDED"]
    assert state.artifacts


def test_runtime_v3_goal_service_keeps_social_chat_out_of_workflow(tmp_path):
    service = RuntimeV3GoalService(tmp_path)

    result = service.run_goal("org", "привет, как дела?", [])

    assert result.ok
    assert result.state.work_items == {}
    assert "План: 0 рабочих пункта." in result.summary
