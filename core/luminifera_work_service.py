"""Read-only product view model for Luminifera Work and Goals."""

from __future__ import annotations

from dataclasses import dataclass

from core.agent_directory import list_chat_agents
from core.database import Database


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

    def __init__(self, database: Database) -> None:
        self._database = database

    def snapshot(self, organization_id: str | None) -> WorkSnapshot:
        if not organization_id:
            return WorkSnapshot()
        organization = next((row for row in self._database.list_organizations() if str(row["id"]) == organization_id), None)
        if organization is None:
            return WorkSnapshot()
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
