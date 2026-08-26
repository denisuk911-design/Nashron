from runtime_v3 import GoalStatus, HybridWorkflowEngine, WorkItemStatus
from runtime_v3.agent_runtime import AgentDecision, DeterministicAgentRuntime
import time

from runtime_v3.models import Action, ActionType, EmployeeBinding, Goal, Plan, WorkItem, new_id
from runtime_v3.supervisor import GoalSupervisor
from runtime_v3.supervisor_policy import HybridSupervisorPolicy


def employees():
    return [
        EmployeeBinding("engineer", "Engineer", "engineering", ["engineering", "specification"]),
        EmployeeBinding("researcher", "Researcher", "research", ["research", "components"]),
        EmployeeBinding("reviewer", "Reviewer", "qa", ["review", "qa", "evidence"]),
    ]


def test_social_chat_does_not_create_goal_work_items(tmp_path):
    engine = HybridWorkflowEngine("org", employees(), tmp_path)
    goal = engine.create_goal("hello, how are you?")
    plan = engine.create_plan(goal.goal_id)

    assert plan.work_item_ids == []
    assert engine.get_state().goals[goal.goal_id].status == GoalStatus.COMPLETED
    assert engine.get_state().work_items == {}


def test_ordinary_goal_remains_autonomous_without_hitl(tmp_path):
    engine = HybridWorkflowEngine("org", employees(), tmp_path)
    goal = engine.create_goal("Create one file as a simple note")
    engine.create_plan(goal.goal_id)

    state = engine.start(goal.goal_id)

    assert state.goals[goal.goal_id].status == GoalStatus.COMPLETED
    assert engine.pending_interrupts(goal.goal_id) == []


def test_supervisor_rules_route_obvious_work_without_any_model_call(tmp_path):
    class Adapter:
        def __init__(self): self.calls = 0
        def decide(self, objective): self.calls += 1; return "COMPLEX"

    local, strong = Adapter(), Adapter()
    engine = HybridWorkflowEngine("org", employees(), tmp_path, supervisor_policy=HybridSupervisorPolicy(local, strong))
    goal = engine.create_goal("Create one file as a simple note")
    engine.create_plan(goal.goal_id)

    assert engine.supervisor.last_policy_decision.level == "DETERMINISTIC"
    assert local.calls == strong.calls == 0


def test_supervisor_uses_local_then_strong_planning_with_safe_fallback(tmp_path):
    class Adapter:
        def __init__(self, answer=None, fail=False): self.answer, self.fail, self.calls = answer, fail, 0
        def decide(self, objective):
            self.calls += 1
            if self.fail: raise RuntimeError("offline")
            return self.answer

    local = Adapter("SIMPLE")
    engine = HybridWorkflowEngine("org", employees(), tmp_path, supervisor_policy=HybridSupervisorPolicy(local, Adapter(fail=True)))
    goal = engine.create_goal("Unclassified request")
    plan = engine.create_plan(goal.goal_id)
    assert engine.supervisor.last_policy_decision.level == "LOCAL"
    assert len(plan.work_item_ids) == 1

    strong = Adapter("COMPLEX")
    engine = HybridWorkflowEngine("org", employees(), tmp_path, supervisor_policy=HybridSupervisorPolicy(Adapter(fail=True), strong))
    goal = engine.create_goal("Unclassified request")
    plan = engine.create_plan(goal.goal_id)
    assert engine.supervisor.last_policy_decision.level == "STRONG"
    assert len(plan.work_item_ids) == 3

    engine = HybridWorkflowEngine("org", employees(), tmp_path, supervisor_policy=HybridSupervisorPolicy(Adapter(fail=True), Adapter(fail=True)))
    goal = engine.create_goal("Unclassified request")
    engine.create_plan(goal.goal_id)
    assert engine.supervisor.last_policy_decision.level == "DETERMINISTIC"


def test_supervisor_decision_router_escalates_by_complexity_risk_and_persists(tmp_path):
    class Adapter:
        def __init__(self, answer="COMPLEX", fail=False): self.answer, self.fail, self.calls = answer, fail, 0
        def decide(self, objective):
            self.calls += 1
            if self.fail: raise RuntimeError("offline")
            return self.answer

    local, strong = Adapter("SIMPLE"), Adapter("COMPLEX")
    policy = HybridSupervisorPolicy(local, strong)
    assert policy.route("transition", "x", "LOW", "LOW", "LOW", []).level == "DETERMINISTIC"
    assert local.calls == strong.calls == 0
    assert policy.route("routing", "x", "MEDIUM", "LOW", "LOW", []).level == "LOCAL"
    assert policy.route("replanning", "x", "HIGH", "HIGH", "HIGH", ["engineering"]).level == "STRONG"

    engine = HybridWorkflowEngine("org", employees(), tmp_path, supervisor_policy=policy)
    goal = engine.create_goal("Create one file as a simple note")
    engine.create_plan(goal.goal_id)
    assert engine.state.supervisor_decisions
    restored = HybridWorkflowEngine("org", employees(), tmp_path, supervisor_policy=policy)
    restored.repository = engine.repository
    assert restored.resume().workflow_graph(goal.goal_id)["supervisor_decision_ids"]


def test_supervisor_decomposes_goal_and_assigns_by_competency(tmp_path):
    engine = HybridWorkflowEngine("org", employees(), tmp_path)
    goal = engine.create_goal("Prepare technical specification and controller research")
    plan = engine.create_plan(goal.goal_id)
    items = [engine.get_state().work_items[item_id] for item_id in plan.work_item_ids]

    assert len(items) == 3
    assert items[0].assigned_employee_id == "engineer"
    assert items[1].assigned_employee_id == "researcher"
    assert items[2].assigned_employee_id == "reviewer"
    assert items[2].dependencies == [items[0].work_item_id, items[1].work_item_id]
    assert plan.strategy == "HANDOFF"


def test_simple_work_item_does_not_launch_whole_team(tmp_path):
    engine = HybridWorkflowEngine("org", employees(), tmp_path)
    goal = engine.create_goal("Create one file as a simple note")
    plan = engine.create_plan(goal.goal_id)

    assert len(plan.work_item_ids) == 1
    assert plan.strategy == "SEQUENTIAL"


def test_supervisor_selects_all_orchestration_strategies_from_dependencies():
    supervisor = GoalSupervisor(employees())
    first = WorkItem("first", "goal", "first", "engineer")
    second = WorkItem("second", "goal", "second", "researcher")
    dependent = WorkItem("review", "goal", "review", "reviewer", dependencies=["first"])

    assert supervisor.choose_strategy([first]) == "SEQUENTIAL"
    assert supervisor.choose_strategy([first, second]) == "CONCURRENT"
    assert supervisor.choose_strategy([first, dependent]) == "HANDOFF"


def test_concurrent_executor_runs_independent_agent_decisions_in_parallel(tmp_path):
    class SlowRuntime:
        def __init__(self):
            self.started: list[float] = []

        def decide(self, employee_id, work_item, attempt):
            self.started.append(time.monotonic())
            time.sleep(0.15)
            return AgentDecision(actions=[Action(
                new_id("action"), work_item.work_item_id, employee_id, ActionType.FILESYSTEM_WRITE,
                {"path": f"artifacts/{work_item.work_item_id}.md", "content": work_item.objective},
            )])

    runtime = SlowRuntime()
    engine = HybridWorkflowEngine("org", employees(), tmp_path, agent_runtime=runtime)
    goal = Goal("goal-concurrent", "parallel independent work")
    first = WorkItem("work-first", goal.goal_id, "first", "engineer", status=WorkItemStatus.READY)
    second = WorkItem("work-second", goal.goal_id, "second", "researcher", status=WorkItemStatus.READY)
    plan = Plan("plan-concurrent", goal.goal_id, "supervisor", [first.work_item_id, second.work_item_id], strategy="CONCURRENT")
    engine.state.goals[goal.goal_id] = goal
    engine.state.plans[plan.plan_id] = plan
    engine.state.work_items = {first.work_item_id: first, second.work_item_id: second}

    state = engine.start(goal.goal_id)

    assert max(runtime.started) - min(runtime.started) < 0.10
    assert state.goals[goal.goal_id].status == GoalStatus.COMPLETED
    assert len(state.artifacts) == 2


def test_failed_work_is_replanned_to_an_alternate_employee_and_succeeds(tmp_path):
    class FailOnceRuntime:
        def decide(self, employee_id, work_item, attempt):
            path = "../bad.md" if attempt == 0 else "artifacts/recovered.md"
            return AgentDecision(actions=[Action(
                new_id("action"), work_item.work_item_id, employee_id, ActionType.FILESYSTEM_WRITE,
                {"path": path, "content": "recovered"},
            )])

    team = [
        EmployeeBinding("engineer-a", "Engineer A", "engineering", ["engineering", "specification"]),
        EmployeeBinding("engineer-b", "Engineer B", "engineering", ["engineering", "specification"]),
    ]
    engine = HybridWorkflowEngine("org", team, tmp_path, agent_runtime=FailOnceRuntime())
    goal = engine.create_goal("Create one file as a simple note")
    engine.create_plan(goal.goal_id)

    state = engine.start(goal.goal_id)
    item = next(iter(state.work_items.values()))

    assert state.goals[goal.goal_id].status == GoalStatus.COMPLETED
    assert item.assigned_employee_id == "engineer-b"
    assert item.attempt == 2
    assert any(evidence.evidence_type == "SUPERVISOR_REPLAN" for evidence in state.evidence.values())


def test_blocked_provider_work_is_replanned_once_without_an_infinite_loop(tmp_path):
    class ProviderFailsThenWorks:
        def __init__(self):
            self.calls = 0

        def decide(self, employee_id, work_item, attempt):
            self.calls += 1
            if self.calls == 1:
                return AgentDecision(message="temporary provider outage", failure_kind="PROVIDER_FAILURE")
            return AgentDecision(actions=[Action(
                new_id("action"), work_item.work_item_id, employee_id, ActionType.FILESYSTEM_WRITE,
                {"path": "artifacts/provider-recovered.md", "content": "recovered"},
            )])

    runtime = ProviderFailsThenWorks()
    engine = HybridWorkflowEngine("org", employees(), tmp_path, agent_runtime=runtime)
    goal = engine.create_goal("Create one file as a simple note")
    engine.create_plan(goal.goal_id)

    state = engine.start(goal.goal_id)

    assert state.goals[goal.goal_id].status == GoalStatus.COMPLETED
    assert runtime.calls == 2
    assert sum(evidence.evidence_type == "SUPERVISOR_REPLAN" for evidence in state.evidence.values()) == 1


def test_rework_replans_the_work_graph_and_preserves_handoff_inputs(tmp_path):
    engine = HybridWorkflowEngine("org", employees(), tmp_path)
    goal = engine.create_goal("Prepare technical specification for converter")
    engine.create_plan(goal.goal_id)

    state = engine.start(goal.goal_id)
    specification = next(item for item in state.work_items.values() if "specification" in item.objective.lower())

    assert state.goals[goal.goal_id].status == GoalStatus.COMPLETED
    assert specification.attempt == 2
    assert any(evidence.evidence_type == "SUPERVISOR_REPLAN" for evidence in state.evidence.values())
    assert state.replans
    graph = state.workflow_graph(goal.goal_id)
    assert graph["strategy"] == "HANDOFF"
    assert graph["replan_ids"]
    assert all(handoff.artifact_ids for handoff in state.handoffs.values())


def test_provider_failure_does_not_consume_the_content_rework_budget(tmp_path):
    class TemporarySpecificationProviderFailure(DeterministicAgentRuntime):
        def __init__(self):
            self.failed = False

        def decide(self, employee_id, work_item, attempt):
            if "specification" in work_item.objective.lower() and not self.failed:
                self.failed = True
                return AgentDecision(message="temporary outage", failure_kind="PROVIDER_FAILURE")
            return super().decide(employee_id, work_item, attempt)

    engine = HybridWorkflowEngine(
        "org", employees(), tmp_path, agent_runtime=TemporarySpecificationProviderFailure(), max_rework_attempts=2
    )
    goal = engine.create_goal("Prepare technical specification for converter")
    engine.create_plan(goal.goal_id)

    state = engine.start(goal.goal_id)

    assert state.goals[goal.goal_id].status == GoalStatus.COMPLETED
    assert any(artifact.revision == 2 for artifact in state.artifacts.values())


def test_replan_removes_completed_dependencies_from_the_active_work_graph():
    supervisor = GoalSupervisor(employees())
    completed = WorkItem("completed", "goal", "source", "researcher", status=WorkItemStatus.COMPLETED)
    blocked = WorkItem(
        "blocked", "goal", "publish", "engineer", dependencies=[completed.work_item_id],
        required_capabilities=["engineering"], status=WorkItemStatus.BLOCKED, attempt=1,
    )

    decision = supervisor.replan(blocked, [completed, blocked])

    assert decision is not None
    assert decision["dependencies"] == []
    assert decision["strategy"] == "SEQUENTIAL"


def test_persistent_blocked_work_stops_after_the_autonomous_replan_limit(tmp_path):
    class AlwaysBlockedRuntime:
        def __init__(self):
            self.calls = 0

        def decide(self, employee_id, work_item, attempt):
            self.calls += 1
            return AgentDecision(message="provider unavailable", failure_kind="PROVIDER_FAILURE")

    runtime = AlwaysBlockedRuntime()
    engine = HybridWorkflowEngine("org", employees(), tmp_path, agent_runtime=runtime)
    goal = engine.create_goal("Create one file as a simple note")
    engine.create_plan(goal.goal_id)

    state = engine.start(goal.goal_id)

    assert runtime.calls == 2
    assert state.goals[goal.goal_id].status == GoalStatus.RUNNING
    assert next(iter(state.work_items.values())).status == WorkItemStatus.BLOCKED


def test_hitl_interrupt_survives_restart_and_resumes_without_duplicate_effects(tmp_path):
    class DecisionRuntime:
        def __init__(self):
            self.calls: list[str] = []

        def decide(self, employee_id, work_item, attempt):
            self.calls.append(work_item.work_item_id)
            if work_item.work_item_id == "decision" and not work_item.result.get("owner_decision"):
                return AgentDecision(hitl_request={
                    "question": "Choose output voltage.",
                    "options": ["12 V", "15 V"],
                    "context": "The available requirements conflict.",
                })
            return AgentDecision(actions=[Action(
                new_id("action"), work_item.work_item_id, employee_id, ActionType.FILESYSTEM_WRITE,
                {"path": f"artifacts/{work_item.work_item_id}.md", "content": work_item.result.get("owner_decision", "done")},
            )])

    first_runtime = DecisionRuntime()
    engine = HybridWorkflowEngine("org", employees(), tmp_path, agent_runtime=first_runtime)
    goal = Goal("goal-hitl", "owner decision required")
    completed_work = WorkItem("completed", goal.goal_id, "prepare evidence", "engineer", status=WorkItemStatus.READY)
    blocked_work = WorkItem("decision", goal.goal_id, "select voltage", "researcher", status=WorkItemStatus.READY)
    plan = Plan("plan-hitl", goal.goal_id, "supervisor", [completed_work.work_item_id, blocked_work.work_item_id], strategy="CONCURRENT")
    goal.plan_id = plan.plan_id
    engine.state.goals[goal.goal_id] = goal
    engine.state.plans[plan.plan_id] = plan
    engine.state.work_items = {completed_work.work_item_id: completed_work, blocked_work.work_item_id: blocked_work}
    engine.start(goal.goal_id)
    interrupt = engine.pending_interrupts(goal.goal_id)[0]

    resumed_runtime = DecisionRuntime()
    resumed = HybridWorkflowEngine("org", employees(), tmp_path, agent_runtime=resumed_runtime)
    resumed.repository = engine.repository
    state = resumed.resume()
    assert resumed.pending_interrupts(goal.goal_id)[0].interrupt_id == interrupt.interrupt_id

    state = resumed.answer_interrupt(interrupt.interrupt_id, "12 V")

    assert state.goals[goal.goal_id].status == GoalStatus.COMPLETED
    assert state.interrupts[interrupt.interrupt_id].owner_decision == "12 V"
    assert state.interrupts[interrupt.interrupt_id].status.value == "RESOLVED"
    assert "completed" not in resumed_runtime.calls
    assert len(state.actions) == 2
    assert len(state.artifacts) == 2


def test_canonical_workflow_graph_restores_strategy_interrupt_and_replan_history(tmp_path):
    engine = HybridWorkflowEngine("org", employees(), tmp_path)
    goal = engine.create_goal("Prepare technical specification for converter")
    engine.create_plan(goal.goal_id)
    state = engine.start(goal.goal_id)
    expected = state.workflow_graph(goal.goal_id)

    resumed = HybridWorkflowEngine("org", employees(), tmp_path)
    resumed.repository = engine.repository
    restored = resumed.resume().workflow_graph(goal.goal_id)

    assert restored == expected
    assert restored["strategy"] == "HANDOFF"
    assert restored["replan_ids"]


def test_goal_runs_through_action_tool_observation_artifacts_review_rework(tmp_path):
    engine = HybridWorkflowEngine("org", employees(), tmp_path)
    goal = engine.create_goal("Prepare technical specification for converter")
    engine.create_plan(goal.goal_id)
    state = engine.start(goal.goal_id)

    assert state.goals[goal.goal_id].status == GoalStatus.COMPLETED
    assert state.actions
    assert state.observations
    assert state.artifacts
    assert all(artifact.created_from_observation_id in state.observations for artifact in state.artifacts.values())
    assert all(evidence.passed for evidence in state.evidence.values() if evidence.evidence_type == "TOOL_OBSERVATION")
    assert state.findings
    assert any(artifact.revision == 2 for artifact in state.artifacts.values() if artifact.artifact_type == "TECHNICAL_SPECIFICATION")
    assert any(evidence.evidence_type == "SOURCE_RECORD" and evidence.passed for evidence in state.evidence.values())


def test_handoff_contains_real_artifacts_for_reviewer(tmp_path):
    engine = HybridWorkflowEngine("org", employees(), tmp_path)
    goal = engine.create_goal("Prepare technical specification and controller research")
    engine.create_plan(goal.goal_id)
    state = engine.start(goal.goal_id)

    handoffs = list(state.handoffs.values())
    assert handoffs
    assert all(handoff.artifact_ids for handoff in handoffs)
    assert all(artifact_id in state.artifacts for handoff in handoffs for artifact_id in handoff.artifact_ids)


def test_fake_claim_does_not_create_artifact_or_close_work_item(tmp_path):
    engine = HybridWorkflowEngine("org", employees(), tmp_path)
    goal = Goal("goal-fake", "Fake claim goal")
    item = WorkItem("work-fake", goal.goal_id, "fake claim create docs/fake.md", "engineer", status=WorkItemStatus.READY)
    engine.state.goals[goal.goal_id] = goal
    engine.state.work_items[item.work_item_id] = item

    engine.start(goal.goal_id)

    assert engine.state.work_items[item.work_item_id].status == WorkItemStatus.BLOCKED
    assert engine.state.artifacts == {}
    assert any(not evidence.passed and evidence.evidence_type == "UNSUPPORTED_CLAIM" for evidence in engine.state.evidence.values())


def test_failed_tool_observation_cannot_close_work_item(tmp_path):
    class EscapingRuntime:
        def decide(self, employee_id, work_item, attempt):
            return AgentDecision(actions=[Action(new_id("action"), work_item.work_item_id, employee_id, ActionType.FILESYSTEM_WRITE, {"path": "../escape.md", "content": "no"})])

    engine = HybridWorkflowEngine("org", employees(), tmp_path, agent_runtime=EscapingRuntime())
    goal = engine.create_goal("Create one file as a simple note")
    engine.create_plan(goal.goal_id)
    state = engine.start(goal.goal_id)

    item = next(iter(state.work_items.values()))
    assert item.status == WorkItemStatus.FAILED
    assert state.goals[goal.goal_id].status == GoalStatus.FAILED
    assert not state.artifacts


def test_denied_workspace_permission_blocks_before_side_effect(tmp_path):
    employee = EmployeeBinding("limited", "Limited", "engineering", ["engineering"], permissions=["READ_WORKSPACE"])
    engine = HybridWorkflowEngine("org", [employee], tmp_path)
    goal = engine.create_goal("Create one file as a simple note")
    engine.create_plan(goal.goal_id)
    state = engine.start(goal.goal_id)

    assert not state.artifacts
    assert any("permission denied" in observation.summary for observation in state.observations.values())


def test_supervisor_does_not_assign_employee_without_required_capability():
    supervisor = GoalSupervisor([EmployeeBinding("sales", "Sales", "sales", ["sales"])])

    try:
        supervisor.create_plan(Goal("goal-no-capability", "Create one file as a simple note"))
    except ValueError as exc:
        assert "no employee has required capabilities" in str(exc)
    else:
        raise AssertionError("Supervisor assigned a work item without a matching capability")


def test_supervisor_rejects_employee_with_incompatible_provider_capabilities():
    employee = EmployeeBinding(
        "engineer", "Engineer", "engineering", ["engineering"],
        provider_capabilities=["chat"],
    )
    supervisor = GoalSupervisor([employee])

    try:
        supervisor.create_plan(Goal("goal-provider-capability", "Create one file as a simple note"))
    except ValueError as exc:
        assert "filesystem.write" in str(exc)
    else:
        raise AssertionError("Supervisor assigned a work item to an incompatible provider")


def test_resume_keeps_permission_and_trace_snapshot(tmp_path):
    employee = EmployeeBinding("limited", "Limited", "engineering", ["engineering"], permissions=["READ_WORKSPACE"])
    engine = HybridWorkflowEngine("org", [employee], tmp_path)
    goal = engine.create_goal("Create one file as a simple note")
    engine.create_plan(goal.goal_id)
    state = engine.start(goal.goal_id)
    trace_count = len(state.trace_events)

    resumed = HybridWorkflowEngine("org", [EmployeeBinding("limited", "Changed", "engineering", ["engineering"])], tmp_path)
    resumed.repository = engine.repository
    restored = resumed.resume()

    assert restored.employee_snapshots["limited"]["permissions"] == ["READ_WORKSPACE"]
    assert resumed.tool_runtime.employee_permissions["limited"] == {"READ_WORKSPACE"}
    assert len(restored.trace_events) >= trace_count


def test_repeated_rework_escalates_after_configured_limit(tmp_path):
    class AlwaysBadSpecificationRuntime(DeterministicAgentRuntime):
        def decide(self, employee_id, work_item, attempt):
            if "specification" in work_item.objective.lower():
                return AgentDecision(actions=[Action(
                    new_id("action"), work_item.work_item_id, employee_id, ActionType.FILESYSTEM_WRITE,
                    {"path": "artifacts/specification.md", "content": "# Technical specification\nMissing control section."},
                )])
            return super().decide(employee_id, work_item, attempt)

    engine = HybridWorkflowEngine("org", employees(), tmp_path, agent_runtime=AlwaysBadSpecificationRuntime(), max_rework_attempts=2)
    goal = engine.create_goal("Prepare technical specification for converter")
    engine.create_plan(goal.goal_id)
    state = engine.start(goal.goal_id)

    assert state.goals[goal.goal_id].status == GoalStatus.FAILED
    assert any(item.result.get("escalation") == "MAX_REWORK_ATTEMPTS_EXCEEDED" for item in state.work_items.values())
    assert any(item.evidence_type == "REWORK_ESCALATION" and not item.passed for item in state.evidence.values())
    assert any(artifact.revision == 2 for artifact in state.artifacts.values())


def test_checkpoint_resume_preserves_completed_work(tmp_path):
    engine = HybridWorkflowEngine("org", employees(), tmp_path)
    goal = engine.create_goal("Prepare technical specification for converter")
    engine.create_plan(goal.goal_id)
    engine.start(goal.goal_id)
    artifact_count = len(engine.state.artifacts)
    checkpoint_count = len(engine.state.checkpoints)

    resumed = HybridWorkflowEngine("org", employees(), tmp_path)
    resumed.repository = engine.repository
    state = resumed.resume()

    assert state.goals[goal.goal_id].status == GoalStatus.COMPLETED
    assert len(state.artifacts) == artifact_count
    assert len(state.checkpoints) >= checkpoint_count


def test_resume_recovers_interrupted_running_work_item(tmp_path):
    engine = HybridWorkflowEngine("org", employees(), tmp_path)
    goal = engine.create_goal("Create one file as a simple note")
    engine.create_plan(goal.goal_id)
    item = next(iter(engine.state.work_items.values()))
    item.status = WorkItemStatus.RUNNING
    engine.checkpoint("simulated_crash_during_work")

    resumed = HybridWorkflowEngine("org", employees(), tmp_path)
    resumed.repository = engine.repository
    state = resumed.resume()

    assert state.goals[goal.goal_id].status == GoalStatus.COMPLETED
    assert item.work_item_id in state.work_items
    assert state.work_items[item.work_item_id].attempt == 1
    assert len(state.artifacts) == 1
