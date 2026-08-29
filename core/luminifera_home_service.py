"""Application-facing, read-only state for the Luminifera home screen."""

from __future__ import annotations

from dataclasses import dataclass

from core.agent_directory import list_chat_agents
from core.database import Database
from core.luminifera_work_service import LuminiferaWorkService


@dataclass(frozen=True)
class HomeArtifact:
    title: str
    state: str


@dataclass(frozen=True)
class HomeSnapshot:
    has_organization: bool
    organization_name: str = ""
    team_size: int = 0
    goal_title: str = ""
    goal_state: str = ""
    goal_progress: int = 0
    artifacts: tuple[HomeArtifact, ...] = ()


class LuminiferaHomeService:
    """Maps validated domain data into language-neutral product view state."""

    def __init__(self, database: Database, runtime_root=None) -> None:
        self._database = database
        self._work_service = LuminiferaWorkService(database, runtime_root)

    def snapshot(self, organization_id: str | None) -> HomeSnapshot:
        if not organization_id:
            return HomeSnapshot(has_organization=False)

        organization = next(
            (row for row in self._database.list_organizations() if str(row["id"]) == organization_id),
            None,
        )
        if organization is None:
            return HomeSnapshot(has_organization=False)

        work = self._work_service.snapshot(organization_id)
        if work.goal_title:
            return HomeSnapshot(
                has_organization=True,
                organization_name=str(organization["name"]),
                team_size=work.team_size,
                goal_title=work.goal_title,
                goal_state=work.goal_state,
                goal_progress=work.goal_progress,
                artifacts=tuple(HomeArtifact(item.title, item.status) for item in work.artifacts),
            )

        tasks = self._database.list_tasks(limit=1, organization_id=organization_id)
        artifacts = self._database.list_artifacts(limit=3, organization_id=organization_id)
        employees = list_chat_agents(self._database, organization_id=organization_id)
        task = tasks[0] if tasks else None
        return HomeSnapshot(
            has_organization=True,
            organization_name=str(organization["name"]),
            team_size=len(employees),
            goal_title=str(task["title"]) if task is not None else "",
            goal_state=str(task["state"]) if task is not None else "",
            goal_progress=0,
            artifacts=tuple(
                HomeArtifact(
                    title=str(row["relative_path"] or row["kind"] or "Результат"),
                    state=str(row["status"] or ""),
                )
                for row in artifacts
            ),
        )
