from core.competence_graph_service import CompetenceGraphService
from core.database import Database
from core.management_models import AgentProfile


def _organization(database: Database, organization_id: str) -> None:
    with database.connect() as conn:
        conn.execute("INSERT INTO organizations (id, name, purpose, status) VALUES (?, ?, '', 'ACTIVE')", (organization_id, organization_id))


def _run(database: Database, agent_id: str, role: str, *, checks=None, artifact=False) -> str:
    database.ensure_project("project-memory", "Memory project")
    task_id = database.create_task("project-memory", "Evidence task", None, "1.0")
    run_id = database.create_agent_run(
        task_id=task_id, agent_id=agent_id, agent_key=agent_id.removeprefix("agent-"), logical_role=role,
        provider="CODEX_CLI", prompt_hash=None, started_at="2026-08-28T10:00:00",
    )
    database.finish_agent_run(
        run_id=run_id, ok=True, cancelled=False, returncode=0, duration_seconds=1, error=None,
        raw_response="done", parsed_response={"checks": checks or [], "findings": []}, parse_errors=[], finished_at="2026-08-28T10:00:01",
    )
    if artifact:
        database.upsert_artifact(
            task_id=task_id, project_id="project-memory", relative_path=f"{run_id}.md", created_by_run_id=run_id,
            status="OBSERVED", validation_status="VERIFIED",
        )
    return run_id


def test_competence_grows_only_after_evidenced_independent_review(tmp_path):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    _organization(database, "org-a")
    for agent_id, name in (("agent-worker", "Ірина"), ("agent-reviewer", "Олег")):
        database.create_agent_profile(AgentProfile(agent_id, name, "", "ACTIVE", "CODEX_CLI"), actor="owner", reason="test")
    service = CompetenceGraphService(database)
    source_run = _run(database, "agent-worker", "DESIGN_ENGINEER", artifact=True)

    candidate = service.propose_knowledge(
        organization_id="org-a", source_run_id=source_run, competence="PCB review",
        title="Проверка зазоров", content="Практическое правило проверки.", outcome="REWORK",
    )
    assert candidate.lifecycle_state == "CANDIDATE"
    assert service.list_competence("org-a") == []

    review_run = _run(database, "agent-reviewer", "QA_ENGINEER", checks=[{"name": "review", "ok": True}])
    verified, node = service.verify_knowledge(candidate.entry_id, review_run)

    assert verified.lifecycle_state == "VERIFIED"
    assert node.competence == "PCB review"
    assert node.growth_points == 1
    assert node.evidence["artifact_ids"]
    assert node.evidence["review_run_id"] == review_run


def test_org_memory_is_isolated_and_survives_employee_delete_and_restart(tmp_path):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    _organization(database, "org-a")
    _organization(database, "org-b")
    for agent_id, name in (("agent-worker", "Марія"), ("agent-reviewer", "Тарас")):
        database.create_agent_profile(AgentProfile(agent_id, name, "", "ACTIVE", "CODEX_CLI"), actor="owner", reason="test")
    service = CompetenceGraphService(database)
    source_run = _run(database, "agent-worker", "DESIGN_ENGINEER", artifact=True)
    candidate = service.propose_knowledge(
        organization_id="org-a", source_run_id=source_run, competence="BOM audit", title="BOM rule", content="Сверять номиналы.",
    )
    review_run = _run(database, "agent-reviewer", "QA_ENGINEER", checks=[{"name": "review", "ok": True}])
    service.verify_knowledge(candidate.entry_id, review_run)

    assert service.list_memory("org-b") == []
    database.delete_agent_profile("agent-worker", actor="owner", reason="test deletion")

    persisted = service.list_memory("org-a", "VERIFIED")
    assert len(persisted) == 1
    assert persisted[0].source_agent_id is None
    assert persisted[0].source_employee_name == "Марія"
    reopened = Database(database.path)
    reopened.initialize()
    after_restart = CompetenceGraphService(reopened)
    assert [item.title for item in after_restart.list_memory("org-a", "VERIFIED")] == ["BOM rule"]
    assert after_restart.list_memory("org-b") == []
    with reopened.connect() as conn:
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_chat_or_run_without_real_evidence_cannot_create_knowledge_candidate(tmp_path):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    _organization(database, "org-a")
    database.create_agent_profile(AgentProfile("agent-worker", "Марія", "", "ACTIVE", "CODEX_CLI"), actor="owner", reason="test")
    run_id = _run(database, "agent-worker", "DESIGN_ENGINEER")

    try:
        CompetenceGraphService(database).propose_knowledge(
            organization_id="org-a", source_run_id=run_id, competence="Narrative", title="Narrative", content="No evidence",
        )
    except ValueError as exc:
        assert str(exc) == "work_evidence_required"
    else:
        raise AssertionError("knowledge candidate was created without evidence")
