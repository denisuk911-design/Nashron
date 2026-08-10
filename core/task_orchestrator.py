from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .agent_router import AgentRouter
from .database import Database
from .models import CodexResult
from .structured_response import ParsedAgentResponse, parse_agent_response
from .task_state_service import TaskStateService


@dataclass(frozen=True)
class RunHandle:
    task_id: str
    run_id: str
    agent_id: str
    role: str
    provider: str


@dataclass(frozen=True)
class RunCompletion:
    parsed_response: ParsedAgentResponse
    accepted_transition: str | None = None


class TaskOrchestrator:
    """Application orchestration boundary for Phase 1.

    It records tasks/runs/audit data and keeps workflow decisions outside the
    GUI. Existing chat behavior remains controlled by MainWindow for now.
    """

    def __init__(
        self,
        database: Database,
        task_state_service: TaskStateService,
        agent_router: AgentRouter,
        project_id: str = "project-default",
    ) -> None:
        self.database = database
        self.task_state_service = task_state_service
        self.agent_router = agent_router
        self.project_id = project_id
        self.current_task_id: str | None = None

    def ensure_project(self) -> None:
        self.database.ensure_project(self.project_id, "Default Project")

    def start_user_task(self, title: str, owner_message_id: int | None) -> str:
        self.ensure_project()
        self.current_task_id = self.task_state_service.create_task(self.project_id, title[:160] or "Untitled task", owner_message_id)
        self.database.audit_event("task_created", self.current_task_id, {"owner_message_id": owner_message_id})
        return self.current_task_id

    def start_run(self, agent_key: str, prompt_hash: str | None = None) -> RunHandle:
        self.ensure_project()
        if self.current_task_id is None:
            self.current_task_id = self.task_state_service.create_task(self.project_id, "Chat task", None)
        route = self.agent_router.route(agent_key)
        run_id = self.database.create_agent_run(
            task_id=self.current_task_id,
            agent_id=route.agent_id,
            agent_key=agent_key,
            logical_role=route.role,
            provider=route.provider,
            prompt_hash=prompt_hash,
            started_at=datetime.now().isoformat(timespec="seconds"),
        )
        self.database.audit_event("agent_run_started", self.current_task_id, {"run_id": run_id, "role": route.role})
        return RunHandle(self.current_task_id, run_id, route.agent_id, route.role, route.provider)

    def finish_run(self, run_id: str, result: CodexResult, raw_response: str) -> RunCompletion:
        parsed = parse_agent_response(raw_response)
        self.database.finish_agent_run(
            run_id=run_id,
            ok=result.ok,
            cancelled=result.cancelled,
            returncode=result.returncode,
            duration_seconds=result.duration_seconds,
            error=result.error,
            raw_response=raw_response,
            parsed_response=parsed.envelope,
            parse_errors=parsed.errors,
            finished_at=datetime.now().isoformat(timespec="seconds"),
        )
        event_type = "agent_run_finished" if result.ok else "agent_run_failed"
        self.database.audit_event(event_type, None, {"run_id": run_id, "errors": parsed.errors})
        return RunCompletion(parsed_response=parsed)
