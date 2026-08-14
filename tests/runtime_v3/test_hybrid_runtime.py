from runtime_v3 import GoalStatus, HybridWorkflowEngine, WorkItemStatus
from runtime_v3.models import EmployeeBinding, Goal, WorkItem


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
