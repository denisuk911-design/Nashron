import pytest

from core.config_repository import ConfigurationRepository
from core.database import Database
from core.director_service import DirectorService
from core.management_service import ManagementService
from core.universal_platform_service import UniversalPlatformService


def _team(tmp_path, template_name="SOFTWARE_PRODUCT_TEAM"):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    management = ManagementService(database, ConfigurationRepository(tmp_path / "management"))
    management.ensure_foundations()
    universal = UniversalPlatformService(database, management_service=management)
    universal.seed_management_library()
    template = next(item for item in universal.list_templates() if item.name == template_name)
    activation = universal.activate_template(template.template_id, "Product team", team_size="STANDARD")
    return database, activation.organization.organization_id


def test_director_creates_persisted_specialist_and_review_assignments(tmp_path):
    database, organization_id = _team(tmp_path)
    service = DirectorService(database)

    plan = service.create_plan(organization_id, "Создать небольшой менеджер заметок")

    assert plan.director_agent_id
    assert plan.assignments
    assert all(item.agent_id != plan.director_agent_id for item in plan.assignments)
    assert any(item.role_id == "QA_ENGINEER" for item in plan.assignments)
    assert any(item.review_required for item in plan.assignments if item.role_id != "QA_ENGINEER")
    assert plan.status == "READY"
    assert service.get_plan(plan.plan_id) == plan


def test_director_reports_missing_staff_instead_of_doing_everything(tmp_path):
    database, organization_id = _team(tmp_path)
    service = DirectorService(database)
    with database.connect() as conn:
        conn.execute(
            "UPDATE organization_members SET status = 'ARCHIVED' WHERE organization_id = ? AND role_id != 'PROJECT_MANAGER'",
            (organization_id,),
        )

    plan = service.create_plan(organization_id, "Подготовить проект")

    assert plan.status == "NEEDS_STAFFING"
    assert "SPECIALIST" in plan.missing_roles
    assert plan.assignments == ()


def test_director_requires_owner_for_installation_or_destructive_goal(tmp_path):
    _database, organization_id = _team(tmp_path)
    service = DirectorService(_database)

    plan = service.create_plan(organization_id, "Установить платную программу и удалить старые данные")

    assert plan.owner_approval_required is True
    assert plan.status == "AWAITING_OWNER_APPROVAL"


def test_plan_requires_explicit_director_assignment(tmp_path):
    database, organization_id = _team(tmp_path)
    with database.connect() as conn:
        conn.execute(
            "UPDATE organization_members SET role_id = 'CUSTOM_ROLE' WHERE organization_id = ? AND role_id = 'PROJECT_MANAGER'",
            (organization_id,),
        )

    with pytest.raises(ValueError, match="director_not_assigned"):
        DirectorService(database).create_plan(organization_id, "Сделать продукт")


def test_director_workflow_runs_execution_then_independent_review(tmp_path):
    database, organization_id = _team(tmp_path)
    service = DirectorService(database)
    plan = service.create_plan(organization_id, "Создать проверяемый результат")

    action = service.next_action(plan.plan_id)
    assert action is not None
    assert action.assignment_type == "EXECUTION"
    service.start_assignment(action.assignment_id, "RUN-EXEC-1")
    service.finish_assignment(
        action.assignment_id,
        ok=True,
        run_id="RUN-EXEC-1",
        message_id=10,
        summary="Артефакт создан",
        evidence={"files_created": ["result.txt"], "checks": [{"name": "syntax", "ok": True}]},
    )

    while True:
        action = service.next_action(plan.plan_id)
        assert action is not None
        service.start_assignment(action.assignment_id, f"RUN-{action.assignment_id}")
        if action.assignment_type == "REVIEW":
            review_action = action
            break
        service.finish_assignment(
            action.assignment_id,
            ok=True,
            run_id=f"RUN-{action.assignment_id}",
            message_id=11,
            summary="Часть результата создана",
            evidence={"files_modified": ["result.txt"], "checks": [{"name": "content", "ok": True}]},
        )

    assert review_action.agent_id != service.get_plan(plan.plan_id).director_agent_id
    service.finish_assignment(
        review_action.assignment_id,
        ok=True,
        run_id=f"RUN-{review_action.assignment_id}",
        message_id=12,
        summary="Проверка пройдена",
        evidence={"checks": [{"name": "review", "ok": True}]},
        review_decision="APPROVE",
        findings=[],
    )

    completed = service.get_plan(plan.plan_id)
    assert completed.status == "COMPLETED"
    assert all(item.status == "COMPLETED" for item in completed.assignments)
    assert any(row["event_type"] == "REVIEW_APPROVED" for row in database.list_director_workflow_events(plan.plan_id))


def test_review_rework_returns_execution_to_same_owner(tmp_path):
    database, organization_id = _team(tmp_path)
    service = DirectorService(database)
    plan = service.create_plan(organization_id, "Подготовить результат", max_rework_attempts=3)

    executions = [item for item in plan.assignments if item.assignment_type == "EXECUTION"]
    for index, assignment in enumerate(executions, start=1):
        action = service.next_action(plan.plan_id)
        assert action is not None and action.assignment_id == assignment.assignment_id
        service.start_assignment(action.assignment_id, f"RUN-E-{index}")
        service.finish_assignment(
            action.assignment_id,
            ok=True,
            run_id=f"RUN-E-{index}",
            message_id=20 + index,
            summary="Результат",
            evidence={"files_created": [f"part-{index}.txt"]},
        )

    review = service.next_action(plan.plan_id)
    assert review is not None and review.assignment_type == "REVIEW"
    service.start_assignment(review.assignment_id, "RUN-R-1")
    service.finish_assignment(
        review.assignment_id,
        ok=True,
        run_id="RUN-R-1",
        message_id=30,
        summary="Нужна правка",
        evidence={"checks": [{"name": "review", "ok": False}]},
        review_decision="REWORK",
        findings=[{"severity": "HIGH", "summary": "Ошибка"}],
    )

    rework = service.next_action(plan.plan_id)
    assert rework is not None
    assert rework.assignment_type == "EXECUTION"
    assert rework.agent_id == executions[0].agent_id
    assert service.get_plan(plan.plan_id).status == "IN_PROGRESS"


def test_missing_evidence_retries_then_blocks_instead_of_claiming_completion(tmp_path):
    database, organization_id = _team(tmp_path)
    service = DirectorService(database)
    plan = service.create_plan(organization_id, "Создать файл", max_rework_attempts=2)

    first = service.next_action(plan.plan_id)
    assert first is not None
    service.start_assignment(first.assignment_id, "RUN-NO-EVIDENCE-1")
    retried = service.finish_assignment(
        first.assignment_id,
        ok=True,
        run_id="RUN-NO-EVIDENCE-1",
        message_id=40,
        summary="Якобы готово",
        evidence={},
    )
    assert retried.status == "IN_PROGRESS"
    assert service.next_action(plan.plan_id).assignment_id == first.assignment_id

    service.start_assignment(first.assignment_id, "RUN-NO-EVIDENCE-2")
    blocked = service.finish_assignment(
        first.assignment_id,
        ok=True,
        run_id="RUN-NO-EVIDENCE-2",
        message_id=41,
        summary="Снова якобы готово",
        evidence={},
    )
    assert blocked.status == "BLOCKED"
    assert service.next_action(plan.plan_id) is None
    assert service.get_plan(plan.plan_id).assignments[0].failure_reason == "verifiable_evidence_required"
