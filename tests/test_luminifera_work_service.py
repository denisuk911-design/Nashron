from core.luminifera_work_service import LuminiferaWorkService
from core.luminifera_home_service import LuminiferaHomeService
from core.luminifera_files_service import LuminiferaFilesService
from runtime_v3 import HybridWorkflowEngine
from runtime_v3.models import EmployeeBinding


class DatabaseStub:
    def list_organizations(self):
        return [{"id": "org-1", "name": "Engineering"}]

    def list_artifacts(self, **_kwargs):
        return []


def test_work_view_projects_durable_v3_goal_and_artifacts(tmp_path):
    employees = [
        EmployeeBinding("engineer", "Engineer", "engineering", ["engineering", "specification"]),
        EmployeeBinding("reviewer", "Reviewer", "qa", ["review", "qa", "evidence"]),
    ]
    engine = HybridWorkflowEngine("org-1", employees, tmp_path / "org-1")
    goal = engine.create_goal("Prepare a converter specification")
    engine.create_plan(goal.goal_id)
    engine.start(goal.goal_id)

    snapshot = LuminiferaWorkService(DatabaseStub(), tmp_path).snapshot("org-1")

    assert snapshot.goal_title == "Prepare a converter specification"
    assert snapshot.goal_state == "COMPLETED"
    assert snapshot.goal_progress == 100
    assert snapshot.team_size == 2
    assert snapshot.artifacts
    assert snapshot.receipt_ready
    assert snapshot.evidence_count
    assert snapshot.steps

    receipt = LuminiferaWorkService(DatabaseStub(), tmp_path).receipt("org-1")
    assert receipt.completed
    assert receipt.review_status == "PASSED"
    assert receipt.artifacts


def test_home_view_projects_the_same_durable_v3_goal(tmp_path):
    engine = HybridWorkflowEngine(
        "org-1",
        [
            EmployeeBinding("engineer", "Engineer", "engineering", ["engineering"]),
            EmployeeBinding("reviewer", "Reviewer", "qa", ["review", "qa", "evidence"]),
        ],
        tmp_path / "org-1",
    )
    goal = engine.create_goal("Create a verified design brief")
    engine.create_plan(goal.goal_id)

    snapshot = LuminiferaHomeService(DatabaseStub(), tmp_path).snapshot("org-1")

    assert snapshot.goal_title == "Create a verified design brief"
    assert snapshot.goal_state == "PLANNED"
    assert snapshot.goal_progress > 0


def test_files_view_projects_v3_artifacts_without_absolute_paths(tmp_path):
    employees = [
        EmployeeBinding("engineer", "Engineer", "engineering", ["engineering", "specification"]),
        EmployeeBinding("reviewer", "Reviewer", "qa", ["review", "qa", "evidence"]),
    ]
    engine = HybridWorkflowEngine("org-1", employees, tmp_path / "org-1")
    goal = engine.create_goal("Create a verified design brief")
    engine.create_plan(goal.goal_id)
    engine.start(goal.goal_id)

    files = LuminiferaFilesService(DatabaseStub(), tmp_path).list_files("org-1")

    assert files
    assert all("\\" not in item.title and "/" not in item.title for item in files)
    assert all(item.status == "VERIFIED" for item in files)
