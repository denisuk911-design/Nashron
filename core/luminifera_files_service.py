from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.database import Database
from runtime_v3.models import load_state


@dataclass(frozen=True)
class ProductArtifact:
    title: str
    artifact_type: str
    status: str
    modified: str
    artifact_id: str = ""
    goal_id: str = ""
    source_goal: str = ""
    creator: str = ""
    review_status: str = ""


class LuminiferaFilesService:
    def __init__(self, database: Database, runtime_root: Path | None = None) -> None:
        self._database = database
        self._runtime_root = Path(runtime_root) if runtime_root else None

    def list_files(self, organization_id: str | None, project_id: str | None = None) -> tuple[ProductArtifact, ...]:
        if not organization_id:
            return ()
        rows = self._database.list_artifacts(limit=50, organization_id=organization_id)
        if project_id:
            rows = [row for row in rows if str(row["project_id"] or "") == project_id]
        legacy = tuple(
            ProductArtifact(
                title=str(row["relative_path"] or row["artifact_type"] or "Результат"),
                artifact_type=str(row["artifact_type"] or "Файл"),
                status=str(row["status"] or ""),
                modified=str(row["last_modified_time"] or row["created_at"] or ""),
                artifact_id=str(row["id"] or ""),
                review_status=str(row["validation_status"] or row["status"] or ""),
            )
            for row in rows
        )
        runtime = self._runtime_files(organization_id, project_id)
        seen = {item.title for item in runtime}
        return runtime + tuple(item for item in legacy if item.title not in seen)

    def runtime_artifact_path(self, organization_id: str | None, artifact_id: str) -> Path | None:
        """Resolve a durable Runtime V3 artifact without allowing path escape."""
        if not organization_id or self._runtime_root is None:
            return None
        state_path = self._runtime_root / organization_id / "checkpoints" / "state.json"
        if not state_path.is_file():
            return None
        try:
            state = load_state(state_path)
            artifact = state.artifacts.get(artifact_id)
            if artifact is None:
                return None
            path = (self._runtime_root / organization_id / Path(artifact.path)).resolve(strict=False)
            path.relative_to((self._runtime_root / organization_id).resolve())
        except (OSError, ValueError, KeyError, TypeError):
            return None
        return path if path.is_file() else None

    def _runtime_files(self, organization_id: str, project_id: str | None = None) -> tuple[ProductArtifact, ...]:
        if self._runtime_root is None:
            return ()
        state_path = self._runtime_root / organization_id / "checkpoints" / "state.json"
        if not state_path.is_file():
            return ()
        try:
            state = load_state(state_path)
        except (OSError, ValueError, KeyError, TypeError):
            return ()
        goals = sorted(state.goals.values(), key=lambda item: (item.updated_at, item.created_at), reverse=True)
        if not goals:
            return ()
        allowed_goals = {str(row["goal"]) for row in self._database.list_project_plans(organization_id, project_id)} if project_id else set()
        goal_ids = {item.goal_id for item in goals[:5] if not allowed_goals or item.objective in allowed_goals}
        goal_names = {item.goal_id: item.objective for item in goals}
        employee_names = {key: str(value.get("display_name") or "") for key, value in state.employee_snapshots.items()}
        return tuple(
            ProductArtifact(
                title=Path(item.path).name or item.artifact_type,
                artifact_type=item.artifact_type,
                status="VERIFIED",
                modified=item.created_at,
                artifact_id=item.artifact_id,
                goal_id=item.goal_id,
                source_goal=goal_names.get(item.goal_id, ""),
                creator=employee_names.get(item.created_by_employee_id, ""),
                review_status="VERIFIED",
            )
            for item in sorted(state.artifacts.values(), key=lambda value: value.created_at, reverse=True)
            if item.goal_id in goal_ids
        )
