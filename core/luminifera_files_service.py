from __future__ import annotations

from dataclasses import dataclass

from core.database import Database


@dataclass(frozen=True)
class ProductArtifact:
    title: str
    artifact_type: str
    status: str
    modified: str


class LuminiferaFilesService:
    def __init__(self, database: Database) -> None:
        self._database = database

    def list_files(self, organization_id: str | None) -> tuple[ProductArtifact, ...]:
        if not organization_id:
            return ()
        rows = self._database.list_artifacts(limit=50, organization_id=organization_id)
        return tuple(
            ProductArtifact(
                title=str(row["relative_path"] or row["artifact_type"] or "Результат"),
                artifact_type=str(row["artifact_type"] or "Файл"),
                status=str(row["status"] or ""),
                modified=str(row["last_modified_time"] or row["created_at"] or ""),
            )
            for row in rows
        )
