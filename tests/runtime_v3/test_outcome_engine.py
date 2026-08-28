from runtime_v3 import GoalStatus, HybridWorkflowEngine, WorkItemStatus
from runtime_v3.models import EmployeeBinding


def employees():
    return [
        EmployeeBinding("engineer", "Engineer", "engineering", ["engineering", "specification"]),
        EmployeeBinding("researcher", "Researcher", "research", ["research", "components"]),
        EmployeeBinding("reviewer", "Reviewer", "qa", ["review", "qa", "evidence"]),
    ]


def test_outcome_definitions_are_specific_to_goal_type(tmp_path):
    engine = HybridWorkflowEngine("org", employees(), tmp_path)
    goals = [
        engine.create_goal("Prepare technical specification for a converter"),
        engine.create_goal("Research and select a suitable controller"),
        engine.create_goal("Create a marketing delivery plan"),
    ]

    definitions = [goal.definition_of_done[0].description for goal in goals]

    assert len(set(definitions)) == 3
    assert all(goal.definition_of_done for goal in goals)


def test_fake_completed_work_cannot_complete_goal_without_runtime_evidence(tmp_path):
    engine = HybridWorkflowEngine("org", employees(), tmp_path)
    goal = engine.create_goal("Create one file as a simple note")
    plan = engine.create_plan(goal.goal_id)
    item = engine.state.work_items[plan.work_item_ids[0]]

    item.status = WorkItemStatus.COMPLETED
    item.result = {"claim": "done"}
    engine._update_goal(goal)

    assert goal.status == GoalStatus.REWORK
    assert goal.work_receipt_id is None
    assert engine.state.work_receipts == {}


def test_work_receipt_is_durable_after_restart(tmp_path):
    engine = HybridWorkflowEngine("org", employees(), tmp_path)
    goal = engine.create_goal("Prepare technical specification and controller research")
    engine.create_plan(goal.goal_id)

    state = engine.start(goal.goal_id)

    assert state.goals[goal.goal_id].status == GoalStatus.COMPLETED
    receipt_id = state.goals[goal.goal_id].work_receipt_id
    assert receipt_id
    receipt = state.work_receipts[receipt_id]
    assert receipt.artifact_ids and receipt.evidence_ids

    restored = HybridWorkflowEngine("org", employees(), tmp_path)
    restored.repository = engine.repository
    state_after_restart = restored.resume()

    assert state_after_restart.goals[goal.goal_id].work_receipt_id == receipt_id
    assert state_after_restart.work_receipts[receipt_id] == receipt
