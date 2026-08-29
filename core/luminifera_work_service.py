"""Read-only product view model for Luminifera Work and Goals."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.agent_directory import list_chat_agents
from core.database import Database
from runtime_v3.models import GoalStatus, WorkItemStatus, load_state


@dataclass(frozen=True)
class WorkArtifact:
    title: str
    status: str


@dataclass(frozen=True)
class WorkStep:
    title: str
    status: str
    is_review: bool = False


@dataclass(frozen=True)
class WorkSnapshot:
    organization_name: str = ""
    team_size: int = 0
    goal_title: str = ""
    goal_state: str = ""
    goal_progress: int = 0
    artifacts: tuple[WorkArtifact, ...] = ()
    findings: int = 0
    steps: tuple[WorkStep, ...] = ()


class LuminiferaWorkService:
    _PROGRESS = {
        "PENDING": 10,
        "PLANNED": 15,
        "IN_PROGRESS": 50,
        "REVIEW": 75,
        "COMPLETED": 100,
        "DONE": 100,
        "BLOCKED": 25,
        "CANCELLED": 0,
    }

    def __init__(self, database: Database, runtime_root: Path | None = None) -> None:
        self._database = database
        self._runtime_root = Path(runtime_root) if runtime_root else None

    def snapshot(self, organization_id: str | None) -> WorkSnapshot:
        if not organization_id:
            return WorkSnapshot()
        organization = next((row for row in self._database.list_organizations() if str(row["id"]) == organization_id), None)
        if organization is None:
            return WorkSnapshot()
        runtime_snapshot = self._runtime_snapshot(organization_id, str(organization["name"]))
        if runtime_snapshot is not None:
            return runtime_snapshot
        tasks = self._database.list_tasks(limit=1, organization_id=organization_id)
        artifacts = self._database.list_artifacts(limit=6, organization_id=organization_id)
        findings = self._database.list_findings(limit=100, organization_id=organization_id)
        plans = self._database.list_project_plans(organization_id)
        steps: tuple[WorkStep, ...] = ()
        if plans:
            assignments = self._database.list_work_assignments(str(plans[0]["id"]))
            steps = tuple(
                WorkStep(
                    title=str(row["position"] or row["role_id"] or "Участок работы"),
                    status=str(row["status"] or "ASSIGNED"),
                    is_review=str(row["assignment_type"] or "") == "REVIEW",
                )
                for row in assignments[:8]
            )
        task = tasks[0] if tasks else None
        state = str(task["state"] or "") if task is not None else ""
        return WorkSnapshot(
            organization_name=str(organization["name"]),
            team_size=len(list_chat_agents(self._database, organization_id=organization_id)),
            goal_title=str(task["title"]) if task is not None else "",
            goal_state=state,
            goal_progress=self._PROGRESS.get(state.upper(), 0),
            artifacts=tuple(WorkArtifact(str(row["relative_path"] or row["kind"] or "Результат"), str(row["status"] or "")) for row in artifacts),
            findings=len(findings),
            steps=steps,
        )

    def _runtime_snapshot(self, organization_id: str, organization_name: str) -> WorkSnapshot | None:
        """Project the durable V3 checkpoint into the product Work view."""
        if self._runtime_root is None:
            return None
        state_path = self._runtime_root / organization_id / "checkpoints" / "state.json"
        if not state_path.is_file():
            return None
        try:
            state = load_state(state_path)
        except (OSError, ValueError, KeyError, TypeError):
            return None
        goals = sorted(state.goals.values(), key=lambda item: (item.updated_at, item.created_at), reverse=True)
        if not goals:
            return None
        goal = goals[0]
        items = [item for item in state.work_items.values() if item.goal_id == goal.goal_id]
        completed = sum(item.status == WorkItemStatus.COMPLETED for item in items)
        progress = 100 if goal.status == GoalStatus.COMPLETED else round((completed / len(items)) * 100) if items else self._PROGRESS.get(goal.status.value.upper(), 0)
        artifacts = [item for item in state.artifacts.values() if item.goal_id == goal.goal_id]
        findings = [item for item in state.findings.values() if item.goal_id == goal.goal_id]
        steps = tuple(
            WorkStep(
                title=item.objective,
                status=item.status.value,
                is_review=any(token in " ".join(item.required_capabilities).lower() for token in ("review", "audit", "evidence", "qa")),
            )
            for item in items[:8]
        )
        return WorkSnapshot(
            organization_name=organization_name,
            goal_title=goal.objective,
            goal_state=goal.status.value,
            goal_progress=max(0, min(100, progress)),
            artifacts=tuple(WorkArtifact(Path(item.path).name or item.artifact_type, "verified") for item in artifacts[:6]),
            findings=len(findings),
            steps=steps,
        )
