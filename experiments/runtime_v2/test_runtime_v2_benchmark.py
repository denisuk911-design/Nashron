from __future__ import annotations

from pathlib import Path

import pytest

from experiments.runtime_v2.models import (
    AgentIdentity,
    EvaluationCase,
    KnowledgeStatus,
    OrganizationKnowledge,
    ProfessionalCapability,
    SkillDecision,
    SkillVersion,
    StepState,
    Task,
    TaskState,
    TaskStep,
)
from experiments.runtime_v2.prototype import (
    AgentRuntimePrototype,
    DeterministicToolRunner,
    LearningEngine,
    OrganizationBootstrapService,
    ScriptedProvider,
    SimulatedCrash,
    ToolExecutionFailure,
)
from experiments.runtime_v2.store import SQLitePrototypeStore


@pytest.fixture
def store(tmp_path: Path):
    result = SQLitePrototypeStore(tmp_path / "runtime_v2_benchmark.sqlite3")
    yield result
    result.close()


def identity(agent_id: str = "agent-alexey") -> AgentIdentity:
    return AgentIdentity(
        agent_id=agent_id,
        organization_id="org-demo",
        role_id="role-specialist",
        display_name="Алексей Орлов",
        preferred_name="Алексей",
        communication_style="concise_professional",
    )


def capability() -> ProfessionalCapability:
    return ProfessionalCapability(
        profession_id="profession-engineer",
        competencies=("analysis",),
        skill_refs=("skill-report",),
        tool_refs=("file.write",),
        knowledge_refs=("knowledge-baseline",),
        qualification_state="PRACTICING",
    )


def five_step_task() -> Task:
    steps: list[TaskStep] = []
    for number in range(1, 6):
        steps.append(
            TaskStep(
                step_id=f"step-{number}",
                instruction=f"Execute step {number}",
                expected_output=f"Output {number}",
                effect_key=f"task-five:step-{number}",
                required_artifact_ids=(["artifact-step-2"] if number == 3 else []),
                output_artifact_id=("artifact-step-2" if number == 2 else ""),
            )
        )
    return Task(
        task_id="task-five",
        title="Five step provider switch",
        goal="Complete five steps without repeating committed work",
        acceptance=["steps 1-5 completed", "artifact from step 2 used at step 3"],
        steps=steps,
    )


def test_provider_switch_preserves_canonical_state_and_does_not_repeat_steps(store):
    provider_a = ScriptedProvider(
        "provider-a", model="mock-a", fail_after_successes=2
    )
    provider_b = ScriptedProvider(
        "provider-b",
        model="mock-b",
        required_artifacts={"step-3": {"artifact-step-2"}},
    )
    runtime = AgentRuntimePrototype(store, [provider_a, provider_b])
    state = runtime.create_state(
        identity=identity(),
        capability=capability(),
        task=five_step_task(),
        provider_ids=("provider-a", "provider-b"),
        workspace_uri="workspace://organizations/org-demo/tasks/task-five",
    )

    completed = runtime.run(state.run_id)

    assert completed.task_state == TaskState.COMPLETED
    assert [request.step.step_id for request in provider_a.calls] == [
        "step-1",
        "step-2",
        "step-3",
    ]
    assert [request.step.step_id for request in provider_b.calls] == [
        "step-3",
        "step-4",
        "step-5",
    ]
    assert all(step.state == StepState.COMPLETED for step in completed.active_task.steps)
    assert completed.provider_binding.provider_id == "provider-b"
    assert completed.identity == identity()
    assert completed.capability == capability()
    assert "artifact-step-2" in completed.artifact_ids
    assert provider_b.calls[0].artifact_ids == ("artifact-step-2",)
    assert completed.active_task.steps[0].attempts == 1
    assert completed.active_task.steps[1].attempts == 1
    assert completed.active_task.steps[2].attempts == 2
    assert store.effect_commit_count("task-five:step-1") == 1
    assert store.effect_commit_count("task-five:step-2") == 1
    assert store.checkpoint_count(state.run_id) >= 7
    assert any(event.event_type == "PROVIDER_UNAVAILABLE" for event in store.list_traces(state.run_id))


def test_structured_handoff_supplies_real_artifact_and_acceptance(store):
    creator = ScriptedProvider("provider-a", model="mock-a")
    reviewer = ScriptedProvider(
        "provider-b",
        model="mock-b",
        required_artifacts={"handoff:handoff-fixed": {"artifact-source"}},
    )
    runtime = AgentRuntimePrototype(store, [creator, reviewer])
    task = Task(
        task_id="task-handoff",
        title="Create source artifact",
        goal="Create a structured source",
        acceptance=["source exists"],
        steps=[
            TaskStep(
                step_id="create-source",
                instruction="Create the source artifact",
                expected_output="source",
                effect_key="handoff:create",
                output_artifact_id="artifact-source",
            )
        ],
    )
    state = runtime.create_state(
        identity=identity("agent-a"),
        capability=capability(),
        task=task,
        provider_ids=("provider-a",),
        workspace_uri="workspace://organizations/org-demo/tasks/task-handoff",
    )
    runtime.run(state.run_id)
    handoff = runtime.create_handoff(
        from_agent_id="agent-a",
        to_agent_id="agent-b",
        task_id=task.task_id,
        intent="Review the supplied source",
        artifact_ids=["artifact-source"],
        expected_output="review artifact",
        acceptance=["review references artifact-source", "review is evidence-backed"],
        evidence_requirements=["artifact_created", "source_linked"],
    )
    # Keep the provider's requirement deterministic while preserving the real ID.
    reviewer.required_artifacts = {
        f"handoff:{handoff.handoff_id}": {"artifact-source"}
    }

    result = runtime.execute_handoff(
        handoff.handoff_id,
        organization_id="org-demo",
        provider_id="provider-b",
        output_artifact_id="artifact-review",
    )

    saved = store.get_handoff(handoff.handoff_id)
    assert saved.status == "COMPLETED"
    assert saved.artifact_ids == ["artifact-source"]
    assert saved.expected_output == "review artifact"
    assert saved.acceptance == [
        "review references artifact-source",
        "review is evidence-backed",
    ]
    assert reviewer.calls[0].artifact_ids == ("artifact-source",)
    assert result.provenance[-1] == "artifact:artifact-source"
    assert "conversation" not in result.content.lower()


def base_skill() -> SkillVersion:
    return SkillVersion(
        skill_id="skill-bom",
        organization_id="org-demo",
        profession_id="profession-engineer",
        version=1,
        instructions="Prepare and validate a BOM.",
        source_refs=["standard:ipc-demo"],
        examples=["bom-example-1"],
        tools=["spreadsheet.validate"],
        limitations=["Do not invent manufacturer data"],
        behaviors={"valid": "PASS", "duplicate": "FAIL", "critical": "REJECT"},
        contributors=["agent-alexey"],
        status=SkillDecision.CURRENT,
    )


def evaluation_dataset() -> list[EvaluationCase]:
    return [
        EvaluationCase("valid", "valid BOM", "PASS"),
        EvaluationCase("duplicate", "duplicate designators", "FAIL"),
        EvaluationCase("critical", "missing critical value", "REJECT", critical=True),
        EvaluationCase("format", "bad output format", "NORMALIZE"),
    ]


def test_learning_promotes_only_measurably_better_candidate(store):
    learning = LearningEngine(store)
    current = base_skill()
    store.save_skill(current)
    lesson = learning.lesson_from_finding(
        organization_id="org-demo",
        profession_id="profession-engineer",
        skill_id=current.skill_id,
        finding_id="finding-format",
        content="Normalize exported BOM columns before review.",
        evidence_ids=("evidence-review-1",),
        contributor_id="agent-alexey",
    )
    candidate = learning.candidate_from_lesson(
        current,
        lesson,
        instructions="Prepare, normalize and validate a BOM.",
        behaviors={**current.behaviors, "format": "NORMALIZE"},
    )

    report = learning.evaluate_and_decide(current, candidate, evaluation_dataset())

    assert report.current_score == 0.75
    assert report.candidate_score == 1.0
    assert report.critical_regressions == ()
    assert report.decision == SkillDecision.PROMOTED
    assert store.active_skill("org-demo", "skill-bom").version == 2  # type: ignore[union-attr]


def test_learning_rejects_candidate_with_critical_regression(store):
    learning = LearningEngine(store)
    current = base_skill()
    store.save_skill(current)
    lesson = learning.lesson_from_finding(
        organization_id="org-demo",
        profession_id="profession-engineer",
        skill_id=current.skill_id,
        finding_id="finding-bad-advice",
        content="Unvalidated suggestion",
        evidence_ids=("evidence-review-2",),
        contributor_id="agent-alexey",
    )
    candidate = learning.candidate_from_lesson(
        current,
        lesson,
        instructions="Apply unvalidated suggestion.",
        behaviors={"valid": "PASS", "duplicate": "FAIL", "critical": "PASS", "format": "NORMALIZE"},
    )

    report = learning.evaluate_and_decide(current, candidate, evaluation_dataset())

    assert report.candidate_score == 0.75
    assert report.critical_regressions == ("critical",)
    assert report.decision == SkillDecision.REJECTED
    assert store.active_skill("org-demo", "skill-bom").version == 1  # type: ignore[union-attr]


def test_employee_delete_keeps_validated_organizational_knowledge_for_new_hire(store):
    bootstrap = OrganizationBootstrapService(store)
    current = base_skill()
    store.save_skill(current)
    old_identity = identity("agent-old")
    store.save_identity(old_identity, "profession-engineer")
    record = OrganizationKnowledge(
        knowledge_id="knowledge-reviewed-bom",
        organization_id="org-demo",
        profession_id="profession-engineer",
        kind="procedure",
        content="Validate duplicate designators before release.",
        source_refs=("standard:ipc-demo",),
        evidence_ids=("evidence-review-3",),
        status=KnowledgeStatus.VALIDATED,
        contributor_id="agent-old",
    )
    store.save_knowledge(record)

    store.delete_identity("agent-old")
    new_hire = bootstrap.bootstrap(identity("agent-new"), "profession-engineer")

    assert store.get_identity("agent-old") is None
    assert store.get_identity("agent-new") is not None
    assert [item.knowledge_id for item in new_hire.organizational_knowledge] == [
        "knowledge-reviewed-bom"
    ]
    assert new_hire.organizational_knowledge[0].contributor_status == "DELETED_CONTRIBUTOR"
    assert new_hire.organizational_knowledge[0].contributor_id == "agent-old"
    assert [item.skill_id for item in new_hire.active_skills] == ["skill-bom"]


def test_timeout_tool_failure_and_restart_resume_from_checkpoint(store):
    provider_a = ScriptedProvider(
        "provider-a", model="mock-a", timeout_once_on_steps={"tool-step"}
    )
    provider_b = ScriptedProvider("provider-b", model="mock-b")
    failing_tools = DeterministicToolRunner(
        store, fail_once={("failure:tool-step", "workspace.write")}
    )
    runtime = AgentRuntimePrototype(
        store, [provider_a, provider_b], tool_runner=failing_tools
    )
    task = Task(
        task_id="task-failure",
        title="Failure recovery",
        goal="Recover from timeout, tool failure and restart",
        acceptance=["effect committed once"],
        steps=[
            TaskStep(
                step_id="tool-step",
                instruction="Write a controlled file",
                expected_output="artifact",
                effect_key="failure:tool-step",
                output_artifact_id="artifact-failure",
                tool_name="workspace.write",
            )
        ],
    )
    state = runtime.create_state(
        identity=identity(),
        capability=capability(),
        task=task,
        provider_ids=("provider-a", "provider-b"),
        workspace_uri="workspace://organizations/org-demo/tasks/task-failure",
    )

    with pytest.raises(ToolExecutionFailure):
        runtime.run(state.run_id)
    after_failure = store.load_state(state.run_id)
    assert after_failure.task_state == TaskState.WAITING_RETRY
    assert after_failure.provider_binding.provider_id == "provider-b"
    assert after_failure.active_task.steps[0].state == StepState.PENDING

    restarted = AgentRuntimePrototype(store, [provider_a, provider_b])
    completed = restarted.run(state.run_id)
    assert completed.task_state == TaskState.COMPLETED
    assert store.effect_commit_count("failure:tool-step") == 1
    assert store.get_artifact("artifact-failure") is not None
    assert any(not item.ok for item in completed.tool_results)
    assert any(item.ok for item in completed.tool_results)
    events = [item.event_type for item in store.list_traces(state.run_id)]
    assert "PROVIDER_TIMEOUT" in events
    assert "TOOL_FAILURE" in events
    assert "STEP_COMPLETED" in events


def test_crash_after_committed_effect_reconciles_without_duplicate_side_effect(store):
    provider = ScriptedProvider("provider-a", model="mock-a")
    runtime = AgentRuntimePrototype(store, [provider])
    task = Task(
        task_id="task-crash",
        title="Crash recovery",
        goal="Do not repeat a committed external effect",
        acceptance=["one provider execution", "one effect commit"],
        steps=[
            TaskStep(
                step_id="publish-result",
                instruction="Commit result",
                expected_output="artifact",
                effect_key="crash:publish-result",
                output_artifact_id="artifact-crash",
            )
        ],
    )
    state = runtime.create_state(
        identity=identity(),
        capability=capability(),
        task=task,
        provider_ids=("provider-a",),
        workspace_uri="workspace://organizations/org-demo/tasks/task-crash",
    )

    with pytest.raises(SimulatedCrash):
        runtime.run(state.run_id, crash_after_effect_key="crash:publish-result")
    assert len(provider.calls) == 1
    assert store.effect_commit_count("crash:publish-result") == 1

    restarted = AgentRuntimePrototype(store, [provider])
    completed = restarted.run(state.run_id)

    assert completed.task_state == TaskState.COMPLETED
    assert len(provider.calls) == 1
    assert store.effect_commit_count("crash:publish-result") == 1
    assert store.get_artifact("artifact-crash") is not None
    assert any(
        event.event_type == "EFFECT_RECONCILED"
        for event in store.list_traces(state.run_id)
    )
    assert store.foreign_key_check() == []
