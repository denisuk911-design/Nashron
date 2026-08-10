from core.config_repository import ConfigurationRepository
from core.database import Database
from core.management_service import ManagementService
from core.skill_package_service import SkillPackageService
from core.skill_progress_service import SkillProgressService
from core.skill_service import SkillService


def _database(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    ManagementService(db, ConfigurationRepository(tmp_path / "management")).ensure_foundations()
    return db


def test_skill_package_lifecycle_is_audited(tmp_path):
    db = _database(tmp_path)
    service = SkillPackageService(db)

    skill_id = service.create_package(
        name="KiCad ERC review",
        purpose="Проверять схемы по ERC и инженерному чек-листу.",
        validation_checklist=["ERC без ошибок", "Номиналы проверены"],
    )
    service.update_status(skill_id, "ACTIVE", reason="owner approved")

    package = service.list_packages()[0]
    events = service.list_events(skill_id)

    assert package.skill_id == skill_id
    assert package.status == "ACTIVE"
    assert package.validation_checklist == ["ERC без ошибок", "Номиналы проверены"]
    assert [event.event_type for event in events] == ["STATUS_CHANGED", "CREATED"]


def test_skill_assignment_appears_in_progress_without_fake_percent(tmp_path):
    db = _database(tmp_path)
    package_service = SkillPackageService(db)
    skill_id = package_service.create_package(name="Documentation control", purpose="Вести проектную документацию.")

    package_service.assign_to_employee("agent-roman", skill_id)

    progress = SkillProgressService(db, SkillService(tmp_path / "agent_skills.json"), tmp_path / "workspace").list_progress()
    roman_skill = next(row for row in progress if row.agent_id == "agent-roman" and row.skill_title == "Documentation control")

    assert roman_skill.percent == 0
    assert roman_skill.status == "Назначен"
    assert "skill package" in roman_skill.basis


def test_invalid_skill_status_is_rejected(tmp_path):
    db = _database(tmp_path)
    service = SkillPackageService(db)
    skill_id = service.create_package(name="Safe file edits")

    try:
        service.update_status(skill_id, "MASTERED")
    except ValueError as exc:
        assert "Недопустимый статус" in str(exc)
    else:
        raise AssertionError("invalid status accepted")
