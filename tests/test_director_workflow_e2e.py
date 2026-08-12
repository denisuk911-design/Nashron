import json

from core.agent_router import AgentRouter
from core.config_repository import ConfigurationRepository
from core.database import Database
from core.director_service import DirectorService
from core.management_service import ManagementService
from core.models import CodexResult
from core.task_orchestrator import TaskOrchestrator
from core.task_state_service import TaskStateService
from core.universal_platform_service import UniversalPlatformService


class FakeEvidenceProvider:
    def generate(self, action):
        review = action.assignment_type == "REVIEW"
        envelope = {
            "schema_version": "1.0",
            "agent_id": action.agent_id,
            "role": "REVIEWER" if review else "SPECIALIST",
            "task_id": action.task_id,
            "run_id": "filled-by-test",
            "action": "APPROVE" if review else "RESULT",
            "summary": "Проверка пройдена" if review else "Назначенная часть выполнена",
            "files_created": [] if review else [f"artifacts/{action.assignment_id}.txt"],
            "files_modified": [],
            "checks": [{"name": "independent_review", "ok": True}] if review else [{"name": "file_exists", "ok": True}],
            "findings": [],
            "risks": [],
        }
        return CodexResult(True, f"{envelope['summary']}\n```json\n{json.dumps(envelope)}\n```", 0, 0.01)


def _organization(tmp_path):
    database = Database(tmp_path / "director-e2e.sqlite3")
    database.initialize()
    management = ManagementService(database, ConfigurationRepository(tmp_path / "management"))
    management.ensure_foundations()
    universal = UniversalPlatformService(database, management_service=management)
    universal.seed_management_library()
    template = next(item for item in universal.list_templates() if item.name == "SOFTWARE_PRODUCT_TEAM")
    activation = universal.activate_template(template.template_id, "E2E team", team_size="STANDARD")
    return database, activation.organization.organization_id


def test_goal_runs_through_real_runs_evidence_and_independent_review(tmp_path):
    database, organization_id = _organization(tmp_path)
    director = DirectorService(database)
    orchestrator = TaskOrchestrator(database, TaskStateService(database), AgentRouter(database))
    provider = FakeEvidenceProvider()
    plan = director.create_plan(organization_id, "Создать проверяемый файл")
    executed_agents = []

    for _ in range(20):
        action = director.next_action(plan.plan_id)
        if action is None:
            break
        orchestrator.current_task_id = action.task_id
        run = orchestrator.start_run(action.agent_key)
        director.start_assignment(action.assignment_id, run.run_id)
        result = provider.generate(action)
        parsed = orchestrator.finish_run(run.run_id, result, result.content).parsed_response
        envelope = parsed.envelope or {}
        envelope["run_id"] = run.run_id
        director.finish_assignment(
            action.assignment_id,
            ok=result.ok,
            run_id=run.run_id,
            message_id=None,
            summary=str(envelope.get("summary") or ""),
            evidence={
                "files_created": envelope.get("files_created", []),
                "checks": envelope.get("checks", []),
            },
            review_decision=str(envelope.get("action") or ""),
            findings=list(envelope.get("findings") or []),
        )
        executed_agents.append((action.assignment_type, action.agent_id))

    completed = director.get_plan(plan.plan_id)
    reviewers = {agent for kind, agent in executed_agents if kind == "REVIEW"}
    executors = {agent for kind, agent in executed_agents if kind == "EXECUTION"}
    assert completed.status == "COMPLETED"
    assert reviewers
    assert executors
    assert reviewers.isdisjoint(executors)
    assert len(database.list_director_workflow_events(plan.plan_id)) >= len(executed_agents) * 2
    assert all(database.get_agent_run(item.result_run_id) is not None for item in completed.assignments)
