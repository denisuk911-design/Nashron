from pathlib import Path

from core.database import Database
from core.agent_router import AgentRouter
from core.task_orchestrator import TaskOrchestrator
from core.task_state_service import TaskStateService
from core.learning_evidence_service import ExperienceRecord, LearningEvidenceService
from core.learning_manager_service import LearningManagerService
from core.skill_package_service import SkillPackageService


def _organization(database: Database, organization_id: str, title: str) -> None:
    with database.connect() as conn:
        conn.execute(
            "INSERT INTO organizations (id, name, purpose, status) VALUES (?, ?, '', 'ACTIVE')",
            (organization_id, title),
        )


def test_operational_records_are_scoped_by_organization_after_restart(tmp_path: Path) -> None:
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    _organization(database, "org-a", "Команда A")
    _organization(database, "org-b", "Команда B")

    first = TaskOrchestrator(database, TaskStateService(database), AgentRouter(database), organization_id="org-a")
    second = TaskOrchestrator(database, TaskStateService(database), AgentRouter(database), organization_id="org-b")
    task_a = first.start_user_task("Задача A", None)
    task_b = second.start_user_task("Задача B", None)

    assert {row["id"] for row in database.list_tasks(organization_id="org-a")} == {task_a}
    assert {row["id"] for row in database.list_tasks(organization_id="org-b")} == {task_b}

    database.create_learning_queue_item(
        {"organization_id": "org-a", "competence": "CAD", "reason": "task A"}
    )
    database.create_learning_queue_item(
        {"organization_id": "org-b", "competence": "QA", "reason": "task B"}
    )
    assert len(database.list_learning_queue(organization_id="org-a")) == 1
    assert len(database.list_learning_queue(organization_id="org-b")) == 1

    reopened = Database(database.path)
    reopened.initialize()
    assert {row["title"] for row in reopened.list_tasks(organization_id="org-a")} == {"Задача A"}
    assert {row["title"] for row in reopened.list_tasks(organization_id="org-b")} == {"Задача B"}
    with reopened.connect() as conn:
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_director_tasks_use_the_plan_organization(tmp_path: Path) -> None:
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    _organization(database, "org-a", "Команда A")
    database.ensure_project("project-org-a", "Проект A", "org-a")
    task_id = database.create_task("project-org-a", "Работа A", None, "1.0", "org-a")
    assert database.get_task(task_id)["organization_id"] == "org-a"
    assert database.list_tasks(organization_id="org-b") == []


def test_chat_only_phrase_cannot_create_skill_and_scoped_skill_survives_restart(tmp_path: Path) -> None:
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    _organization(database, "org-a", "Команда A")
    manager = LearningManagerService(database, LearningEvidenceService(database), SkillPackageService(database))
    chat_only = ExperienceRecord(
        "EXP-chat", None, "", "org-a", None, None, "болтовня", ("случайная фраза",), (), (), (), {}, "RECORDED", ""
    )
    assert manager._ensure_skill_candidate(chat_only, "случайная фраза") is False
    assert SkillPackageService(database).list_packages("org-a") == []

    skill_id = SkillPackageService(database).create_package(
        name="Проверка BOM", organization_id="org-a", status="DRAFT"
    )
    package = SkillPackageService(database).list_packages("org-a")[0]
    assert package.skill_id == skill_id
    assert package.lifecycle_state == "CANDIDATE"
    assert SkillPackageService(database).list_packages("org-b") == []
    reopened = Database(database.path)
    reopened.initialize()
    assert reopened.get_skill_package(skill_id)["organization_id"] == "org-a"
    assert reopened.get_skill_package(skill_id)["lifecycle_state"] == "CANDIDATE"
