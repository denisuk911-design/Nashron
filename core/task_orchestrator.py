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
        organization_id: str | None = None,
    ) -> None:
        self.database = database
        self.task_state_service = task_state_service
        self.agent_router = agent_router
        self.organization_id = organization_id
        self.project_id = project_id if organization_id is None else f"project-{organization_id}"
        self.current_task_id: str | None = None

    def ensure_project(self) -> None:
        self.database.ensure_project(self.project_id, "Default Project", self.organization_id)

    def start_user_task(self, title: str, owner_message_id: int | None) -> str:
        self.ensure_project()
        self.current_task_id = self.database.create_task(self.project_id, title[:160] or "Untitled task", owner_message_id, "1.0", self.organization_id)
        self.database.audit_event("task_created", self.current_task_id, {"owner_message_id": owner_message_id})
        return self.current_task_id

    def start_run(self, agent_key: str, prompt_hash: str | None = None) -> RunHandle:
        self.ensure_project()
        if self.current_task_id is None:
            self.current_task_id = self.database.create_task(self.project_id, "Chat task", None, "1.0", self.organization_id)
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
        self._update_runtime_state(
            route.agent_id,
            {
                "organization_id": self.organization_id,
                "current_task_id": self.current_task_id,
                "current_operation": "RUNNING",
                "current_plan": ["execute assigned task", "record result", "validate output"],
                "status": "WORKING",
            },
        )
        self.database.audit_event("agent_run_started", self.current_task_id, {"run_id": run_id, "role": route.role})
        return RunHandle(self.current_task_id, run_id, route.agent_id, route.role, route.provider)

    def finish_run(self, run_id: str, result: CodexResult, raw_response: str) -> RunCompletion:
        parsed = parse_agent_response(raw_response)
        run_row = self.database.get_agent_run(run_id)
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
            timed_out=result.timed_out,
        )
        event_type = "agent_run_finished" if result.ok else "agent_run_failed"
        self.database.audit_event(event_type, None, {"run_id": run_id, "errors": parsed.errors})
        if run_row is not None:
            self._update_runtime_state(
                str(run_row["agent_id"]),
                {
                    "current_task_id": str(run_row["task_id"]),
                    "current_operation": "RESULT_RECORDED" if result.ok else "RUN_FAILED",
                    "current_plan": [],
                    "checkpoint": {"run_id": run_id, "ok": result.ok, "cancelled": result.cancelled},
                    "status": "IDLE" if result.ok else "BLOCKED",
                },
            )
        return RunCompletion(parsed_response=parsed)

    def _update_runtime_state(self, agent_id: str, values: dict[str, object]) -> None:
        """Keep legacy router-only runs valid until an employee profile exists."""
        if self.database.get_agent_profile(agent_id) is None:
            return
        self.database.upsert_agent_runtime_state(agent_id, values)
