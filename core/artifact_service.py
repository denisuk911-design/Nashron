from __future__ import annotations

import hashlib
import mimetypes
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .database import Database
from .finding_service import Finding, FindingService


ARTIFACT_STATUSES = ("OBSERVED", "MISSING", "DELETED")
ARTIFACT_VALIDATION_STATUSES = ("VERIFIED", "NOT_FOUND", "VERIFIED_ABSENT", "CLAIMED_BUT_PRESENT", "UNSAFE_PATH")


@dataclass(frozen=True)
class Artifact:
    artifact_id: str
    task_id: str
    project_id: str
    relative_path: str
    artifact_type: str
    media_type: str
    authoring_role: str
    created_by_run_id: str
    current_revision: str
    sha256: str
    size: int | None
    status: str
    validation_status: str
    last_modified_time: str
    deleted: bool


@dataclass(frozen=True)
class ArtifactFindingLink:
    link_id: str
    artifact_id: str
    finding_id: str
    match_type: str
    confidence: str
    status: str
    updated_at: str


class ArtifactService:
    def __init__(self, database: Database, workspace_root: Path, project_id: str = "project-default") -> None:
        self.database = database
        self.workspace_root = workspace_root.expanduser().resolve(strict=False)
        self.project_id = project_id

    def import_from_structured_response(
        self,
        *,
        envelope: dict[str, Any] | None,
        task_id: str | None = None,
        run_id: str | None = None,
    ) -> list[str]:
        if not isinstance(envelope, dict):
            return []
        resolved_task_id = self._text(task_id) or self._text(envelope.get("task_id")) or None
        resolved_run_id = self._text(run_id) or self._text(envelope.get("run_id")) or None
        role = self._text(envelope.get("role"))
        created: list[str] = []
        for field, action in (
            ("files_created", "created"),
            ("files_modified", "modified"),
            ("files_deleted", "deleted"),
        ):
            items = envelope.get(field)
            if not isinstance(items, list):
                continue
            for item in items:
                artifact_id = self._register_item(
                    item,
                    action=action,
                    task_id=resolved_task_id,
                    run_id=resolved_run_id,
                    authoring_role=role,
                )
                if artifact_id:
                    created.append(artifact_id)
        if resolved_task_id:
            self.reconcile_finding_links(task_id=resolved_task_id, actor="artifact_import")
        return created

    def register_chat_artifact(
        self,
        *,
        content: str,
        title: str,
        artifact_type: str,
        task_id: str | None,
        run_id: str | None,
        source_agent_id: str,
        source_message_id: int | None = None,
    ) -> str:
        """Register a useful chat result before it becomes a filesystem file."""
        artifact_key = f"chat://{source_agent_id}/{(title or artifact_type).strip().lower().replace(' ', '-')[:80]}"
        artifact_id = self.database.upsert_artifact(
            task_id=task_id,
            project_id=self.project_id,
            relative_path=artifact_key,
            artifact_type=artifact_type.upper(),
            media_type="text/plain",
            authoring_role=source_agent_id,
            created_by_run_id=run_id,
            size=len(content.encode("utf-8")),
            status="OBSERVED",
            validation_status="VERIFIED",
            last_modified_time=datetime.now().isoformat(timespec="seconds"),
            metadata={"artifact_kind": "CHAT_ARTIFACT", "title": title},
        )
        self.database.upsert_artifact_payload(
            artifact_id=artifact_id,
            title=title,
            content=content,
            source_agent_id=source_agent_id,
            source_message_id=source_message_id,
        )
        return artifact_id

    def list_artifacts(self, task_id: str | None = None, status: str | None = None) -> list[Artifact]:
        return [self._artifact_from_row(row) for row in self.database.list_artifacts(task_id=task_id, status=status)]

    def related_findings(self, artifact: Artifact | str, task_id: str | None = None) -> list[Finding]:
        if isinstance(artifact, Artifact):
            self.reconcile_finding_links(task_id=artifact.task_id or None)
            link_rows = self.database.list_artifact_finding_links(artifact_id=artifact.artifact_id)
            finding_ids = [str(row["finding_id"]) for row in link_rows]
            if finding_ids:
                findings = FindingService(self.database).list_findings(task_id=artifact.task_id or None)
                by_id = {finding.finding_id: finding for finding in findings}
                return [by_id[finding_id] for finding_id in finding_ids if finding_id in by_id]
            return []

        relative_path = str(artifact)
        artifact_task_id = task_id
        candidates = FindingService(self.database).list_findings(task_id=artifact_task_id or None)
        return [finding for finding in candidates if self._artifact_reference_matches(relative_path, finding.affected_artifact)[0]]

    def reconcile_finding_links(self, task_id: str | None = None, actor: str = "system") -> list[str]:
        artifacts = self.list_artifacts(task_id=task_id)
        finding_service = FindingService(self.database)
        findings = finding_service.list_findings(task_id=task_id)
        link_ids: list[str] = []
        for artifact in artifacts:
            for finding in findings:
                matches, match_type, confidence = self._artifact_reference_matches(artifact.relative_path, finding.affected_artifact)
                if not matches:
                    continue
                link_id = self.database.upsert_artifact_finding_link(
                    artifact_id=artifact.artifact_id,
                    finding_id=finding.finding_id,
                    match_type=match_type,
                    confidence=confidence,
                    actor=actor,
                )
                link_ids.append(link_id)
        return link_ids

    def list_finding_links(self, artifact_id: str | None = None, finding_id: str | None = None) -> list[ArtifactFindingLink]:
        return [
            self._link_from_row(row)
            for row in self.database.list_artifact_finding_links(artifact_id=artifact_id, finding_id=finding_id)
        ]

    def _register_item(
        self,
        item: object,
        *,
        action: str,
        task_id: str | None,
        run_id: str | None,
        authoring_role: str,
    ) -> str | None:
        path_text = self._path_from_item(item)
        if not path_text:
            return None
        try:
            absolute_path, relative_path = self._resolve_inside_workspace(path_text)
        except ValueError:
            return self.database.upsert_artifact(
                task_id=task_id,
                project_id=self.project_id,
                relative_path=path_text,
                artifact_type=self._artifact_type(path_text),
                media_type=self._media_type(path_text),
                authoring_role=authoring_role,
                created_by_run_id=run_id,
                status="MISSING",
                validation_status="UNSAFE_PATH",
                metadata={"source_action": action, "declared_path": path_text},
            )

        exists = absolute_path.is_file()
        if action == "deleted":
            status = "DELETED"
            validation_status = "VERIFIED_ABSENT" if not absolute_path.exists() else "CLAIMED_BUT_PRESENT"
            return self.database.upsert_artifact(
                task_id=task_id,
                project_id=self.project_id,
                relative_path=relative_path,
                artifact_type=self._artifact_type(relative_path),
                media_type=self._media_type(relative_path),
                authoring_role=authoring_role,
                created_by_run_id=run_id,
                status=status,
                validation_status=validation_status,
                deleted=True,
                metadata={"source_action": action, "declared_path": path_text},
            )

        sha256 = self._sha256(absolute_path) if exists else None
        stat = absolute_path.stat() if exists else None
        return self.database.upsert_artifact(
            task_id=task_id,
            project_id=self.project_id,
            relative_path=relative_path,
            artifact_type=self._artifact_type(relative_path),
            media_type=self._media_type(relative_path),
            authoring_role=authoring_role,
            created_by_run_id=run_id,
            sha256=sha256,
            size=stat.st_size if stat is not None else None,
            status="OBSERVED" if exists else "MISSING",
            validation_status="VERIFIED" if exists else "NOT_FOUND",
            last_modified_time=datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds") if stat is not None else None,
            deleted=False,
            metadata={"source_action": action, "declared_path": path_text},
        )

    def _resolve_inside_workspace(self, path_text: str) -> tuple[Path, str]:
        raw = Path(path_text)
        candidate = raw if raw.is_absolute() else self.workspace_root / raw
        resolved = candidate.expanduser().resolve(strict=False)
        if not resolved.is_relative_to(self.workspace_root):
            raise ValueError("artifact path is outside workspace")
        relative_path = resolved.relative_to(self.workspace_root).as_posix()
        return resolved, relative_path

    @staticmethod
    def _path_from_item(item: object) -> str:
        if isinstance(item, str):
            return item.strip()
        if not isinstance(item, dict):
            return ""
        for key in ("path", "relative_path", "file", "artifact", "affected_artifact"):
            text = ArtifactService._text(item.get(key))
            if text:
                return text
        return ""

    @classmethod
    def _artifact_reference_matches(cls, relative_path: str, affected_artifact: str) -> tuple[bool, str, str]:
        left = cls._normalized_path(relative_path)
        right = cls._normalized_path(affected_artifact)
        if not left or not right:
            return False, "", ""
        if left == right:
            return True, "EXACT_PATH", "HIGH"
        left_name = Path(left).name.lower()
        right_name = Path(right).name.lower()
        if left_name and right_name and left_name == right_name and ("/" not in right and "\\" not in affected_artifact):
            return True, "FILENAME", "MEDIUM"
        return False, "", ""

    @staticmethod
    def _normalized_path(value: str) -> str:
        text = value.strip().replace("\\", "/").strip("/")
        while "//" in text:
            text = text.replace("//", "/")
        return text.lower()

    @staticmethod
    def _artifact_type(path_text: str) -> str:
        suffix = Path(path_text).suffix.lower().lstrip(".")
        return suffix or "file"

    @staticmethod
    def _media_type(path_text: str) -> str:
        media_type, _encoding = mimetypes.guess_type(path_text)
        return media_type or "application/octet-stream"

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _artifact_from_row(row) -> Artifact:
        size_value = row["size"]
        return Artifact(
            artifact_id=str(row["id"]),
            task_id=str(row["task_id"] or ""),
            project_id=str(row["project_id"] or ""),
            relative_path=str(row["relative_path"]),
            artifact_type=str(row["artifact_type"] or ""),
            media_type=str(row["media_type"] or ""),
            authoring_role=str(row["authoring_role"] or ""),
            created_by_run_id=str(row["created_by_run_id"] or ""),
            current_revision=str(row["current_revision"] or ""),
            sha256=str(row["sha256"] or ""),
            size=int(size_value) if size_value is not None else None,
            status=str(row["status"]),
            validation_status=str(row["validation_status"]),
            last_modified_time=str(row["last_modified_time"] or ""),
            deleted=bool(row["deleted"]),
        )

    @staticmethod
    def _link_from_row(row) -> ArtifactFindingLink:
        return ArtifactFindingLink(
            link_id=str(row["id"]),
            artifact_id=str(row["artifact_id"]),
            finding_id=str(row["finding_id"]),
            match_type=str(row["match_type"]),
            confidence=str(row["confidence"]),
            status=str(row["status"]),
            updated_at=str(row["updated_at"] or ""),
        )

    @staticmethod
    def _text(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()
