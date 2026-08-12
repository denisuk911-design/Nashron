from core.config_repository import ConfigurationRepository
from core.database import Database
from core.learning_evidence_service import LearningEvidenceService
from core.learning_manager_service import LearningManagerService
from core.management_models import AgentProfile
from core.management_service import ManagementService
from core.skill_package_service import SkillPackageService
from core.universal_platform_service import UniversalPlatformService


def _services(tmp_path):
    database = Database(tmp_path / "learning-manager.sqlite3")
    database.initialize()
    evidence = LearningEvidenceService(database)
    return database, evidence, LearningManagerService(database, evidence, SkillPackageService(database))


def _run(database, agent_id, role, *, parsed, artifact=False):
    database.ensure_project("project-default", "Project")
    task_id = database.create_task("project-default", "Practice", None, "1.0")
    run_id = database.create_agent_run(
        task_id=task_id,
        agent_id=agent_id,
        agent_key=agent_id.removeprefix("agent-"),
        logical_role=role,
        provider="CODEX_CLI",
        prompt_hash=None,
        started_at="2026-08-13T10:00:00",
    )
    database.finish_agent_run(
        run_id=run_id,
        ok=True,
        cancelled=False,
        returncode=0,
        duration_seconds=1,
        error=None,
        raw_response="done",
        parsed_response=parsed,
        parse_errors=[],
        finished_at="2026-08-13T10:00:01",
    )
    if artifact:
        database.upsert_artifact(
            task_id=task_id,
            project_id="project-default",
            relative_path=f"{run_id}.txt",
            created_by_run_id=run_id,
            status="OBSERVED",
            validation_status="VERIFIED",
        )
    return run_id


def test_learning_item_requires_evidenced_practice_and_independent_qualification(tmp_path):
    database, evidence, manager = _services(tmp_path)
    for agent_id, name in (("agent-worker", "Практикант"), ("agent-reviewer", "Ревьюер")):
        database.create_agent_profile(
            AgentProfile(agent_id, name, "", "ACTIVE", "CODEX_CLI"),
            actor="ORGANIZATION_OWNER",
            reason="test",
        )
    item_id = evidence.propose_learning(
        agent_id="agent-worker",
        competence="Проверка документа",
        reason="Найдено замечание",
        evidence={"finding_id": "FIND-1"},
        practice_task="Исправить и повторно проверить",
    )

    prepared = manager.prepare_learning_item(item_id)
    assert prepared.status == "PRACTICE_REQUIRED"
    assert prepared.skill_id

    practice_run = _run(
        database,
        "agent-worker",
        "DOCUMENT_CONTROL_OFFICER",
        parsed={"skills_used": ["Проверка документа"], "files_created": ["practice.txt"]},
        artifact=True,
    )
    evidence.record_completed_run(practice_run, summary="Практика выполнена")
    practiced = manager.record_practice(item_id, practice_run)
    assert practiced.status == "READY_FOR_REVIEW"
    assert practiced.practice_run_id == practice_run

    review_run = _run(
        database,
        "agent-reviewer",
        "QA_ENGINEER",
        parsed={"action": "APPROVE", "checks": [{"name": "qualification", "ok": True}], "findings": []},
    )
    verified = manager.record_qualification(item_id, review_run, approved=True)
    assert verified.status == "VERIFIED"
    assert verified.review_run_id == review_run
    assignment = next(item for item in SkillPackageService(database).list_assignments("agent-worker") if item.skill_id == verified.skill_id)
    assert assignment.state == "QUALIFIED"
    package = next(item for item in SkillPackageService(database).list_packages() if item.skill_id == verified.skill_id)
    assert package.status == "VERIFIED"


def test_employee_cannot_qualify_own_practice(tmp_path):
    database, evidence, manager = _services(tmp_path)
    database.create_agent_profile(
        AgentProfile("agent-worker", "Практикант", "", "ACTIVE", "CODEX_CLI"),
        actor="ORGANIZATION_OWNER",
        reason="test",
    )
    item_id = evidence.propose_learning(
        agent_id="agent-worker",
        competence="Навык",
        reason="Ошибка",
        evidence={"finding_id": "FIND-1"},
    )
    manager.prepare_learning_item(item_id)
    practice_run = _run(database, "agent-worker", "DESIGN_ENGINEER", parsed={"skills_used": ["Навык"]}, artifact=True)
    evidence.record_completed_run(practice_run, summary="Практика")
    manager.record_practice(item_id, practice_run)
    self_review = _run(
        database,
        "agent-worker",
        "QA_ENGINEER",
        parsed={"checks": [{"name": "self", "ok": True}], "findings": []},
    )

    try:
        manager.record_qualification(item_id, self_review, approved=True)
    except ValueError as exc:
        assert str(exc) == "independent_reviewer_required"
    else:
        raise AssertionError("self-qualification must be rejected")


def test_project_retrospective_creates_practiced_candidate_from_real_experience(tmp_path):
    database, evidence, manager = _services(tmp_path)
    management = ManagementService(database, ConfigurationRepository(tmp_path / "management"))
    management.ensure_foundations()
    universal = UniversalPlatformService(database, management_service=management)
    universal.seed_management_library()
    template = next(item for item in universal.list_templates() if item.name == "SOFTWARE_PRODUCT_TEAM")
    organization = universal.activate_template(template.template_id, "Learning E2E", team_size="STANDARD")
    worker = next(
        row for row in database.list_organization_members(organization.organization.organization_id)
        if str(row["role_id"]) == "DESIGN_ENGINEER"
    )
    run_id = _run(
        database,
        str(worker["agent_id"]),
        "DESIGN_ENGINEER",
        parsed={"skills_used": ["Evidence workflow"], "files_created": ["evidence.txt"]},
        artifact=True,
    )
    record = evidence.record_completed_run(run_id, organization_id=organization.organization.organization_id, summary="Работа")
    database.ensure_project("project-default", "Project")
    plan_id = database.create_project_plan(
        {
            "organization_id": organization.organization.organization_id,
            "project_id": "project-default",
            "director_agent_id": next(
                str(row["agent_id"]) for row in database.list_organization_members(organization.organization.organization_id)
                if str(row["role_id"]) == "PROJECT_MANAGER"
            ),
            "goal": "Goal",
            "status": "COMPLETED",
        }
    )
    database.create_work_assignment(
        {
            "plan_id": plan_id,
            "task_id": record.task_id,
            "agent_id": record.agent_id,
            "role_id": "DESIGN_ENGINEER",
            "position": "Developer",
            "sequence_no": 1,
            "status": "COMPLETED",
        }
    )

    retrospective = manager.retrospective_for_plan(plan_id)

    assert retrospective.candidates_created == 1
    package = next(item for item in SkillPackageService(database).list_packages() if item.name == "Evidence workflow")
    assert package.status == "PRACTICED"
    assert SkillPackageService(database).list_assignments(record.agent_id)[0].state == "PRACTICED"
