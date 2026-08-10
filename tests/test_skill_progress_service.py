from core.config_repository import ConfigurationRepository
from core.database import Database
from core.management_service import ManagementService
from core.skill_progress_service import SkillProgressService
from core.skill_service import SkillService


def _database(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    management = ManagementService(db, ConfigurationRepository(tmp_path / "management"))
    management.ensure_foundations()
    db.ensure_project("project-default", "Default Project")
    return db


def test_progress_uses_real_runs_and_existing_files(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    created = workspace / "docs" / "standard.md"
    created.parent.mkdir()
    created.write_text("ok", encoding="utf-8")

    db = _database(tmp_path)
    task_id = db.create_task("project-default", "task", None, "1.0")
    run_id = db.create_agent_run(
        task_id=task_id,
        agent_id="agent-roman",
        agent_key="roman",
        logical_role="DESIGN_ENGINEER",
        provider="CODEX_CLI",
        prompt_hash=None,
        started_at="2026-01-01T00:00:00",
    )
    db.finish_agent_run(
        run_id=run_id,
        ok=True,
        cancelled=False,
        returncode=0,
        duration_seconds=1.0,
        error=None,
        raw_response="",
        parsed_response={"skills_used": ["create docs standard"], "files_created": ["docs/standard.md"]},
        parse_errors=[],
        finished_at="2026-01-01T00:00:01",
    )

    skills = SkillService(tmp_path / "agent_skills.json")
    skills.learn_from_exchange("roman", "create docs standard", "Created docs/standard.md")

    progress = SkillProgressService(db, skills, workspace).list_progress()
    roman = next(row for row in progress if row.agent_key == "roman" and row.percent > 0)

    assert roman.uses == 1
    assert roman.successful_runs == 1
    assert roman.verified_files == 1
    assert roman.status == "Показал результат"
    assert roman.tasks_completed == 1
    assert roman.reviews_passed == 0
    assert roman.percent == 26


def test_skill_claim_without_evidence_has_zero_progress(tmp_path):
    db = _database(tmp_path)
    skills = SkillService(tmp_path / "agent_skills.json")
    skills.learn_from_exchange("roman", "claim skill", "I learned it.")

    progress = SkillProgressService(db, skills, tmp_path / "workspace").list_progress()
    roman = next(row for row in progress if row.agent_key == "roman")

    assert roman.percent == 0
    assert "сама по себе процент не повышает" in roman.basis
    assert roman.status == "Назначен"


def test_employee_without_real_skill_has_zero_progress(tmp_path):
    db = _database(tmp_path)
    skills = SkillService(tmp_path / "agent_skills.json")

    progress = SkillProgressService(db, skills, tmp_path / "workspace").list_progress()
    empty_rows = [row for row in progress if row.percent == 0 and row.skill_title == "Навыков пока нет"]

    assert empty_rows
