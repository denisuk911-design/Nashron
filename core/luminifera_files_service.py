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


class LuminiferaFilesService:
    def __init__(self, database: Database, runtime_root: Path | None = None) -> None:
        self._database = database
        self._runtime_root = Path(runtime_root) if runtime_root else None

    def list_files(self, organization_id: str | None) -> tuple[ProductArtifact, ...]:
        if not organization_id:
            return ()
        rows = self._database.list_artifacts(limit=50, organization_id=organization_id)
        legacy = tuple(
            ProductArtifact(
                title=str(row["relative_path"] or row["artifact_type"] or "Результат"),
                artifact_type=str(row["artifact_type"] or "Файл"),
                status=str(row["status"] or ""),
                modified=str(row["last_modified_time"] or row["created_at"] or ""),
            )
            for row in rows
        )
        runtime = self._runtime_files(organization_id)
        seen = {item.title for item in runtime}
        return runtime + tuple(item for item in legacy if item.title not in seen)

    def _runtime_files(self, organization_id: str) -> tuple[ProductArtifact, ...]:
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
        goal_ids = {item.goal_id for item in goals[:5]}
        return tuple(
            ProductArtifact(
                title=Path(item.path).name or item.artifact_type,
                artifact_type=item.artifact_type,
                status="VERIFIED",
                modified=item.created_at,
            )
            for item in sorted(state.artifacts.values(), key=lambda value: value.created_at, reverse=True)
            if item.goal_id in goal_ids
        )
