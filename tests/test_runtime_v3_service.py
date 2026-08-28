from core.agent_directory import ChatAgent
from core.provider_execution import ProviderCapabilityProfile, ProviderCircuitBreaker, ProviderExecutionResult, isolated_provider_environment
from core.runtime_v3_service import RuntimeV3GoalService
from core.provider_execution import ContextWindowPolicy
from runtime_v3.agent_runtime import ProviderAgentRuntime
from runtime_v3.engine import HybridWorkflowEngine
from runtime_v3.models import EmployeeBinding, WorkItem
from runtime_v3.models import load_state
import time


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
        if "research sources" in request.prompt.lower():
            self.content = (
                '{"action":"filesystem.write","path":"v3_provider_output/research.md",'
                '"content":"# Research notes\\nSource evidence: https://example.com/source"}'
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
    assert run.correlation_id == f"corr-{next(iter(result.state.goals))}-{run.work_item_id}"
    action = next(iter(result.state.actions.values()))
    assert action.payload["correlation_id"] == run.correlation_id
    trace_stages = {
        event.stage
        for event in result.state.trace_events.values()
        if event.detail == run.correlation_id
    }
    assert {"provider_run_finished", "tool_observed", "artifact_created"} <= trace_stages
    restored = load_state(result.workspace_root / "checkpoints" / "state.json")
    assert restored.provider_runs[run.run_id].provider_id == "CODEX_CLI"
    assert restored.provider_runs[run.run_id].correlation_id == run.correlation_id


def test_provider_action_list_executes_multiple_real_tool_observations(tmp_path):
    provider = FakeProviderAdapter(
        "CODEX_CLI",
        '{"actions":[{"action":"filesystem.write","path":"v3_provider_output/one.md","content":"one"},{"action":"filesystem.write","path":"v3_provider_output/two.md","content":"two"}]}',
    )
    service = RuntimeV3GoalService(tmp_path, provider_adapters={"CODEX_CLI": provider})
    agents = [ChatAgent("roman", "agent-roman", "Roman", "CODEX_CLI", ["DESIGN_ENGINEER"], "roman", "", None)]

    result = service.run_goal("org", "Create one file as a simple note", agents)

    assert result.ok
    assert len(result.state.actions) == 2
    assert len(result.state.observations) == 2
    assert len(result.state.artifacts) == 2
    assert next(iter(result.state.provider_runs.values())).action_count == 2


def test_runtime_v3_golden_goal_uses_two_provider_items_then_rework_and_final_review(tmp_path):
    provider = GoldenProviderAdapter("CODEX_CLI")
    service = RuntimeV3GoalService(tmp_path, provider_adapters={"CODEX_CLI": provider})
    agents = [
        ChatAgent("engineer", "agent-engineer", "Engineer", "CODEX_CLI", ["DESIGN_ENGINEER"], "engineer", "", None),
        ChatAgent("researcher", "agent-researcher", "Researcher", "CODEX_CLI", ["RESEARCH_ASSISTANT"], "researcher", "", None),
        ChatAgent("reviewer", "agent-reviewer", "Reviewer", "CODEX_CLI", ["QA_ENGINEER"], "reviewer", "", None),
    ]

    result = service.run_goal("org", "Prepare technical specification for 24 V to 12 V 5 A converter and select a controller; force rework.", agents)

    assert result.ok
    assert len(result.state.work_items) == 3
    assert len(provider.prompts) == 2
    assert len(result.state.provider_runs) == 2
    assert all(run.status == "SUCCEEDED" and run.action_count == 1 for run in result.state.provider_runs.values())
    assert len(result.state.findings) >= 1
    assert len(result.state.actions) >= 5
    assert len(result.state.observations) >= 5
    assert any(
        artifact.artifact_type == "WORK_PRODUCT" and artifact.revision >= 2
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


def test_context_window_policy_preserves_header_and_latest_task():
    policy = ContextWindowPolicy(max_characters=120, head_characters=40)
    prompt = "SYSTEM RULES " + ("old context " * 30) + "LATEST TASK: create artifact"

    result = policy.apply(prompt)

    assert result.condensed
    assert len(result.prompt) <= 120
    assert result.prompt.startswith("SYSTEM RULES")
    assert result.prompt.endswith("LATEST TASK: create artifact")
    assert "CONTEXT CONDENSED" in result.prompt


def test_provider_runtime_cancellation_prevents_new_provider_run():
    provider = FakeProviderAdapter("CODEX_CLI", '{"action":"filesystem.write","path":"v3_provider_output/x.md","content":"x"}')
    runtime = ProviderAgentRuntime({"CODEX_CLI": provider}, {"engineer": "CODEX_CLI"}, max_concurrent_runs=1)
    runtime.cancel_active_runs()
    item = WorkItem("work-cancel", "goal", "Create one file", "engineer")

    decision = runtime.decide("engineer", item, 0)

    assert decision.failure_kind == "PROVIDER_CANCELLED"
    assert provider.prompts == []


def test_provider_runtime_timeout_cancels_slow_adapter_without_leaving_work_running(tmp_path):
    class SlowProvider(FakeProviderAdapter):
        def __init__(self):
            super().__init__("CODEX_CLI")
            self.cancelled = False

        def execute(self, request):
            time.sleep(0.2)
            return super().execute(request)

        def cancel(self):
            self.cancelled = True

    provider = SlowProvider()
    runtime = ProviderAgentRuntime(
        {"CODEX_CLI": provider}, {"engineer": "CODEX_CLI"}, provider_timeout_seconds=0.02
    )
    engine = HybridWorkflowEngine(
        "org", [EmployeeBinding("engineer", "Engineer", "engineering", ["engineering"])],
        tmp_path, agent_runtime=runtime,
    )
    goal = engine.create_goal("Create one file as a simple note")
    engine.create_plan(goal.goal_id)

    state = engine.start(goal.goal_id)

    assert provider.cancelled
    assert all(item.status.value != "RUNNING" for item in state.work_items.values())
    assert any(run.status == "FAILED" and "timed out" in run.error for run in state.provider_runs.values())


def test_provider_circuit_opens_after_failure_and_prevents_repeat_call():
    provider = FakeProviderAdapter("CODEX_CLI", error="token=private-value unavailable")
    circuit = ProviderCircuitBreaker(failure_threshold=1, cooldown_seconds=60, clock=lambda: 10.0)
    runtime = ProviderAgentRuntime({"CODEX_CLI": provider}, {"engineer": "CODEX_CLI"}, circuit_breaker=circuit)

    first = runtime.decide("engineer", WorkItem("work-first", "goal", "Create one file", "engineer"), 0)
    second = runtime.decide("engineer", WorkItem("work-second", "goal", "Create another file", "engineer"), 0)

    assert first.failure_kind == "PROVIDER_FAILURE"
    assert "private-value" not in first.message
    assert "[REDACTED]" in first.message
    assert second.failure_kind == "PROVIDER_FAILURE"
    assert second.provider_run is not None and second.provider_run.status == "SKIPPED"
    assert len(provider.prompts) == 1
    assert runtime.provider_health("CODEX_CLI")["circuit"] == "OPEN"


def test_isolated_provider_environment_keeps_only_its_credential():
    environment = isolated_provider_environment(
        {"GEMINI_API_KEY": "gemini-secret"},
        {"PATH": "system", "OPENAI_API_KEY": "openai-secret", "GEMINI_API_KEY": "old", "LANG": "ru"},
    )

    assert environment == {"PATH": "system", "LANG": "ru", "GEMINI_API_KEY": "gemini-secret"}


def test_incompatible_provider_contract_is_blocked_before_execution():
    class IncompatibleAdapter(FakeProviderAdapter):
        capability_profile = ProviderCapabilityProfile(
            "CODEX_CLI", contract_version="2.0", capabilities=frozenset({"filesystem.write", "structured_output"})
        )

    provider = IncompatibleAdapter("CODEX_CLI", '{"action":"filesystem.write","path":"v3_provider_output/x.md","content":"x"}')
    runtime = ProviderAgentRuntime(
        {"CODEX_CLI": provider}, {"engineer": "CODEX_CLI"}, provider_contract_versions={"CODEX_CLI": "1.0"}
    )

    decision = runtime.decide("engineer", WorkItem("work-contract", "goal", "Create one file", "engineer"), 0)

    assert decision.failure_kind == "PROVIDER_FAILURE"
    assert decision.provider_run is not None and decision.provider_run.status == "BLOCKED"
    assert provider.prompts == []


def test_compatible_contract_upgrade_migrates_snapshot_without_losing_state(tmp_path):
    class UpgradedAdapter(FakeProviderAdapter):
        capability_profile = ProviderCapabilityProfile(
            "CODEX_CLI", contract_version="1.1", capabilities=frozenset({"filesystem.write", "structured_output"})
        )

    provider = UpgradedAdapter(
        "CODEX_CLI", '{"action":"filesystem.write","path":"v3_provider_output/migrated.md","content":"# Result\\ncontroller"}'
    )
    employee = EmployeeBinding("engineer", "Engineer", "engineering", ["engineering"], "CODEX_CLI", provider_contract_version="1.0")
    runtime = ProviderAgentRuntime({"CODEX_CLI": provider}, {"engineer": "CODEX_CLI"})
    engine = HybridWorkflowEngine("org", [employee], tmp_path, agent_runtime=runtime)
    goal = engine.create_goal("Create one file as a simple note")
    engine.create_plan(goal.goal_id)
    state = engine.start(goal.goal_id)
    artifact_count = len(state.artifacts)

    resumed = HybridWorkflowEngine("org", [employee], tmp_path, agent_runtime=ProviderAgentRuntime({"CODEX_CLI": provider}, {"engineer": "CODEX_CLI"}))
    resumed.repository = engine.repository
    restored = resumed.resume()

    snapshot = restored.employee_snapshots["engineer"]
    assert snapshot["provider_contract_version"] == "1.1"
    assert snapshot["provider_contract_migrated_from"] == "1.0"
    assert len(restored.artifacts) == artifact_count


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
