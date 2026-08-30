"""Durable runtime-neutral execution journal with organization isolation."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from .runtime_contracts import ExecutionRequest, ExecutionResult


@dataclass(frozen=True)
class JournalRecord:
    correlation_id: str
    organization_id: str
    status: str
    runtime_id: str = ""
    summary: str = ""
    artifact_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    error: str = ""


class RuntimeExecutionJournal:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def begin(self, request: ExecutionRequest) -> JournalRecord:
        if not request.correlation_id.strip():
            raise ValueError("durable execution requires correlation_id")
        record = JournalRecord(request.correlation_id, request.organization_id, "RUNNING")
        self._write(record)
        return record

    def complete(self, request: ExecutionRequest, result: ExecutionResult) -> JournalRecord:
        self._assert_scope(request.organization_id, result.organization_id)
        record = JournalRecord(
            request.correlation_id,
            request.organization_id,
            "COMPLETED" if result.ok else "FAILED",
            result.runtime_id,
            result.summary,
            result.artifact_refs,
            result.evidence_refs,
        )
        self._write(record)
        return record

    def fail(self, request: ExecutionRequest, error: Exception) -> JournalRecord:
        record = JournalRecord(request.correlation_id, request.organization_id, "FAILED", error=str(error))
        self._write(record)
        return record

    def recover(self, organization_id: str, correlation_id: str) -> JournalRecord | None:
        path = self._path(organization_id, correlation_id)
        if not path.is_file():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            record = JournalRecord(
                raw["correlation_id"], raw["organization_id"], raw["status"],
                raw.get("runtime_id", ""), raw.get("summary", ""),
                tuple(raw.get("artifact_refs", ())), tuple(raw.get("evidence_refs", ())),
                raw.get("error", ""),
            )
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            return None
        return record if record.organization_id == organization_id else None

    def _path(self, organization_id: str, correlation_id: str) -> Path:
        safe_org = "".join(char for char in organization_id if char.isalnum() or char in "-_")
        safe_id = "".join(char for char in correlation_id if char.isalnum() or char in "-_")
        if not safe_org or not safe_id:
            raise ValueError("invalid journal scope")
        return self.root / safe_org / f"{safe_id}.json"

    def _write(self, record: JournalRecord) -> None:
        path = self._path(record.organization_id, record.correlation_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(record), ensure_ascii=True, sort_keys=True), encoding="utf-8")
        os.replace(temporary, path)

    @staticmethod
    def _assert_scope(expected: str, actual: str) -> None:
        if expected != actual:
            raise ValueError("runtime result organization scope mismatch")
