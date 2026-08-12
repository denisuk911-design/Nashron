from core.database import Database
from core.learning_evidence_service import LearningEvidenceService
from core.management_models import AgentProfile
from core.skill_progress_service import SkillProgressService
from core.skill_service import SkillService


def _run(tmp_path, *, with_artifact: bool, with_finding: bool = False):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    database.create_agent_profile(
        AgentProfile("agent-worker", "Марія Коваль", "Инженер", "ACTIVE", "CODEX_CLI"),
        actor="ORGANIZATION_OWNER",
        reason="test",
    )
    database.ensure_project("project-default", "Project")
    task_id = database.create_task("project-default", "Evidence task", None, "1.0")
    run_id = database.create_agent_run(
        task_id=task_id,
        agent_id="agent-worker",
        agent_key="worker",
        logical_role="DESIGN_ENGINEER",
        provider="CODEX_CLI",
        prompt_hash=None,
        started_at="2026-08-13T10:00:00",
    )
    database.finish_agent_run(
        run_id=run_id,
        ok=True,
        cancelled=False,
        returncode=0,
        duration_seconds=2.0,
        error=None,
        raw_response="done",
        parsed_response={"action": "CREATE", "skills_used": ["Python"], "files_modified": ["result.txt"]},
        parse_errors=[],
        finished_at="2026-08-13T10:00:02",
    )
    if with_artifact:
        database.upsert_artifact(
            task_id=task_id,
            project_id="project-default",
            relative_path="result.txt",
            created_by_run_id=run_id,
            status="OBSERVED",
            validation_status="VERIFIED",
        )
    if with_finding:
        database.create_finding(
            task_id=task_id,
            reviewer_run_id=run_id,
            description="Нарушена проверка результата",
            severity="HIGH",
            confidence="HIGH",
        )
    return database, run_id


def test_social_style_run_without_persisted_evidence_does_not_create_experience(tmp_path):
    database, run_id = _run(tmp_path, with_artifact=False)
    service = LearningEvidenceService(database)

    assert service.record_completed_run(run_id, summary="Просто сообщение") is None
    assert service.list_experience() == []
    assert service.list_learning_queue() == []


def test_completed_work_creates_evidence_backed_experience_and_skill_usage(tmp_path):
    database, run_id = _run(tmp_path, with_artifact=True)
    service = LearningEvidenceService(database)

    record = service.record_completed_run(run_id, summary="Создан проверяемый результат")

    assert record is not None
    assert record.employee_name == "Марія Коваль"
    assert record.skills_used == ("Python",)
    assert record.evidence["artifact_ids"]
    assert record.outcome == "EVIDENCE_RECORDED"
    with database.connect() as conn:
        usage = conn.execute("SELECT * FROM skill_usage WHERE run_id = ?", (run_id,)).fetchall()
    assert len(usage) == 1
    assert usage[0]["usage_type"] == "DECLARED_WITH_WORK_EVIDENCE"
    assert service.record_completed_run(run_id, summary="duplicate") == record

    skills_path = tmp_path / "skills.json"
    skills_path.write_text(
        '{"worker": [{"title": "Python", "uses": 1}]}',
        encoding="utf-8",
    )
    progress = SkillProgressService(database, SkillService(skills_path), tmp_path).list_progress()
    python = next(item for item in progress if item.skill_title == "Python")
    assert python.successful_runs == 1


def test_review_finding_creates_learning_proposal_but_not_verified_competence(tmp_path):
    database, run_id = _run(tmp_path, with_artifact=True, with_finding=True)
    service = LearningEvidenceService(database)

    record = service.record_completed_run(run_id, summary="Проверка завершена")
    queue = service.list_learning_queue()

    assert record is not None
    assert record.outcome == "REVIEW_FINDINGS"
    assert len(queue) == 1
    assert queue[0].status == "PROPOSED"
    assert queue[0].evidence["experience_record_id"] == record.record_id

    try:
        service.update_learning_status(queue[0].item_id, "VERIFIED", {})
    except ValueError as exc:
        assert str(exc) == "verification_evidence_required"
    else:
        raise AssertionError("verification without evidence must be rejected")
