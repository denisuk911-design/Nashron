from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .provider_adapter import ProviderAdapter, ProviderExecutionRequest, ProviderExecutionResult
from .sqlite_repository import RUNTIME_V2_SCHEMA_VERSION, dumps, ensure_runtime_v2_schema, loads


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


class V2TaskStatus:
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"
    RECOVERABLE = "RECOVERABLE"


class EffectStatus:
    PREPARED = "PREPARED"
    EXECUTING = "EXECUTING"
    EFFECT_COMMITTED = "EFFECT_COMMITTED"
    STATE_COMMITTED = "STATE_COMMITTED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class CreateTextFileRequest:
    filename: str
    content: str


@dataclass
class RuntimeTaskState:
    runtime_task_id: str
    agent_id: str
    organization_id: str
    intent: str
    goal: str
    status: str
    workspace_uri: str
    provider_binding: dict[str, Any] = field(default_factory=dict)
    artifact_refs: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    checkpoint_id: str | None = None
    completed_effect_keys: list[str] = field(default_factory=list)
    context_refs: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class RuntimeTaskResult:
    ok: bool
    task_id: str
    status: str
    summary: str
    provider: ProviderExecutionResult | None = None
    artifact_id: str = ""
    evidence_id: str = ""
    checkpoint_id: str = ""
    effect_key: str = ""
    logical_uri: str = ""
    physical_path: str = ""
    content_exact: bool = False
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        if self.provider is not None:
            value["provider"] = asdict(self.provider)
        return value


class SQLiteRuntimeV2Repository:
    """Persistence adapter. Domain execution uses this boundary, not SQL."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            ensure_runtime_v2_schema(conn)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def create_task(self, state: RuntimeTaskState) -> None:
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO runtime_v2_tasks
                (runtime_task_id,schema_version,agent_id,organization_id,intent,goal,status,workspace_uri,
                 provider_binding,artifact_refs,evidence_refs,checkpoint_id,completed_effect_keys,context_refs,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    state.runtime_task_id,
                    RUNTIME_V2_SCHEMA_VERSION,
                    state.agent_id,
                    state.organization_id,
                    state.intent,
                    state.goal,
                    state.status,
                    state.workspace_uri,
                    dumps(state.provider_binding),
                    dumps(state.artifact_refs),
                    dumps(state.evidence_refs),
                    state.checkpoint_id,
                    dumps(state.completed_effect_keys),
                    dumps(state.context_refs),
                    state.created_at,
                    state.updated_at,
                ),
            )

    def get_task(self, task_id: str) -> RuntimeTaskState:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM runtime_v2_tasks WHERE runtime_task_id = ?", (task_id,)).fetchone()
        if row is None:
            raise KeyError(task_id)
        return RuntimeTaskState(
            runtime_task_id=row["runtime_task_id"],
            agent_id=row["agent_id"],
            organization_id=row["organization_id"],
            intent=row["intent"],
            goal=row["goal"],
            status=row["status"],
            workspace_uri=row["workspace_uri"],
            provider_binding=loads(row["provider_binding"], {}),
            artifact_refs=loads(row["artifact_refs"], []),
            evidence_refs=loads(row["evidence_refs"], []),
            checkpoint_id=row["checkpoint_id"],
            completed_effect_keys=loads(row["completed_effect_keys"], []),
            context_refs=loads(row["context_refs"], []),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def update_task(self, state: RuntimeTaskState) -> None:
        state.updated_at = utc_now()
        with self.connect() as conn:
            conn.execute(
                """UPDATE runtime_v2_tasks SET status=?, provider_binding=?, artifact_refs=?, evidence_refs=?,
                checkpoint_id=?, completed_effect_keys=?, context_refs=?, updated_at=? WHERE runtime_task_id=?""",
                (
                    state.status,
                    dumps(state.provider_binding),
                    dumps(state.artifact_refs),
                    dumps(state.evidence_refs),
                    state.checkpoint_id,
                    dumps(state.completed_effect_keys),
                    dumps(state.context_refs),
                    state.updated_at,
                    state.runtime_task_id,
                ),
            )

    def checkpoint(self, state: RuntimeTaskState, reason: str) -> str:
        checkpoint_id = new_id("checkpoint")
        state.checkpoint_id = checkpoint_id
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO runtime_v2_checkpoints VALUES (?,?,?,?,?)",
                (checkpoint_id, state.runtime_task_id, dumps(asdict(state)), reason, utc_now()),
            )
        self.update_task(state)
        return checkpoint_id

    def trace(self, task_id: str, event_type: str, detail: dict[str, Any]) -> str:
        trace_id = new_id("trace")
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO runtime_v2_traces VALUES (?,?,?,?,?)",
                (trace_id, task_id, event_type, dumps(detail), utc_now()),
            )
        return trace_id

    def add_context(self, task_id: str, source_type: str, source_id: str, reason: str, priority: str) -> str:
        context_id = new_id("context")
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO runtime_v2_context_refs VALUES (?,?,?,?,?,?,?,?,?)",
                (context_id, task_id, source_type, source_id, reason, priority, "", None, utc_now()),
            )
        return context_id

    def get_effect(self, effect_key: str):
        with self.connect() as conn:
            return conn.execute("SELECT * FROM runtime_v2_effects WHERE effect_key=?", (effect_key,)).fetchone()

    def upsert_effect(self, values: dict[str, Any]) -> None:
        columns = [
            "effect_key",
            "runtime_task_id",
            "effect_type",
            "target_uri",
            "status",
            "prepared_at",
            "executed_at",
            "verified_at",
            "state_commit_at",
            "provider_run_id",
            "artifact_id",
        ]
        with self.connect() as conn:
            conn.execute(
                f"INSERT INTO runtime_v2_effects ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)}) "
                "ON CONFLICT(effect_key) DO UPDATE SET "
                "status=excluded.status, executed_at=excluded.executed_at, verified_at=excluded.verified_at, "
                "state_commit_at=excluded.state_commit_at, provider_run_id=excluded.provider_run_id, "
                "artifact_id=excluded.artifact_id",
                tuple(values.get(column) for column in columns),
            )

    def add_artifact(self, values: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO runtime_v2_artifacts
                (artifact_id,runtime_task_id,artifact_type,logical_uri,workspace_uri,version,created_by_agent,created_by_effect,provenance,validation_status,created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                tuple(
                    values[key]
                    for key in (
                        "artifact_id",
                        "runtime_task_id",
                        "artifact_type",
                        "logical_uri",
                        "workspace_uri",
                        "version",
                        "created_by_agent",
                        "created_by_effect",
                        "provenance",
                        "validation_status",
                        "created_at",
                    )
                ),
            )

    def find_artifact_id(self, task_id: str, logical_uri: str, version: int = 1) -> str | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT artifact_id FROM runtime_v2_artifacts
                WHERE runtime_task_id = ? AND logical_uri = ? AND version = ?
                """,
                (task_id, logical_uri, version),
            ).fetchone()
        return str(row["artifact_id"]) if row is not None else None

    def add_evidence(self, values: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO runtime_v2_evidence
                (evidence_id,runtime_task_id,effect_key,artifact_id,evidence_type,validation_method,expected,actual,passed,created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                tuple(
                    values[key]
                    for key in (
                        "evidence_id",
                        "runtime_task_id",
                        "effect_key",
                        "artifact_id",
                        "evidence_type",
                        "validation_method",
                        "expected",
                        "actual",
                        "passed",
                        "created_at",
                    )
                ),
            )

    def list_recoverable(self) -> list[RuntimeTaskState]:
        with self.connect() as conn:
            ids = [
                row[0]
                for row in conn.execute(
                    "SELECT runtime_task_id FROM runtime_v2_tasks WHERE status IN ('RUNNING','RECOVERABLE','CANCEL_REQUESTED')"
                )
            ]
        return [self.get_task(task_id) for task_id in ids]


def parse_create_text_file(text: str) -> CreateTextFileRequest | None:
    normalized = " ".join(str(text or "").strip().split())
    if not re.search(r"\b(создай|создать|создайте|create|make)\b", normalized, re.I):
        return None
    if not re.search(r"\b(файл|file)\b", normalized, re.I):
        return None
    match = re.search(r"\b(?:файл|file)\s+[`'\"]?([A-Za-z0-9][A-Za-z0-9_.-]{0,127})[`'\"]?", normalized, re.I)
    content_match = re.search(r"\b(?:точно|exactly|content)\s+[`'\"]?([^`'\"]{1,512}?)[`'\"]?$", normalized, re.I)
    if not match or not content_match:
        return None
    filename = match.group(1)
    content = content_match.group(1).strip()
    if Path(filename).name != filename or filename in {".", ".."} or not content:
        return None
    return CreateTextFileRequest(filename, content)


class RuntimeV2Service:
    def __init__(self, repository: SQLiteRuntimeV2Repository, workspace_root: Path) -> None:
        self.repository = repository
        self.workspace_root = Path(workspace_root).resolve()

    def create_task(
        self,
        request: CreateTextFileRequest,
        agent_id: str,
        organization_id: str,
        provider_id: str,
    ) -> RuntimeTaskState:
        task_id = new_id("task")
        workspace_uri = f"workspace://{organization_id}/{task_id}/"
        state = RuntimeTaskState(
            task_id,
            agent_id,
            organization_id,
            "CREATE_TEXT_FILE",
            f"Create {request.filename} with exact content",
            V2TaskStatus.READY,
            workspace_uri,
            {"provider_id": provider_id},
        )
        self.repository.create_task(state)
        context_id = self.repository.add_context(task_id, "USER_REQUEST", task_id, "bounded file request", "REQUIRED")
        state.context_refs.append(context_id)
        self.repository.checkpoint(state, "TASK_CREATED")
        self.repository.trace(task_id, "TASK_CREATED", {"intent": state.intent, "workspace_uri": workspace_uri})
        return state

    def physical_workspace(self, state: RuntimeTaskState) -> Path:
        return self.workspace_root / ".runtime_v2" / state.organization_id / state.runtime_task_id

    def execute(
        self,
        task_id: str,
        request: CreateTextFileRequest,
        adapter: ProviderAdapter,
        *,
        on_status=None,
        crash_after_effect=False,
    ) -> RuntimeTaskResult:
        state = self.repository.get_task(task_id)
        physical_workspace = self.physical_workspace(state)
        physical_path = physical_workspace / request.filename
        logical_uri = f"artifact://{state.organization_id}/{task_id}/{request.filename}"
        effect_key = "create-text-file:" + hashlib.sha256(f"{logical_uri}\0{request.content}".encode()).hexdigest()
        state.status = V2TaskStatus.RUNNING
        self.repository.update_task(state)
        self.repository.trace(task_id, "STATE_RUNNING", {"provider_id": adapter.provider_id, "context_refs": state.context_refs})

        if "CREATE_TEXT_FILE" not in adapter.capabilities() or "FILES" not in adapter.capabilities():
            return self._fail(state, effect_key, "BLOCKED_CAPABILITY", "provider capability gate rejected CREATE_TEXT_FILE")

        existing = self.repository.get_effect(effect_key)
        if (
            existing is not None
            and existing["status"] in {EffectStatus.EFFECT_COMMITTED, EffectStatus.STATE_COMMITTED}
            and self._valid_file(physical_path, request.content)
        ):
            return self._finalize(state, request, effect_key, logical_uri, physical_path, None, reconciled=True)

        physical_workspace.mkdir(parents=True, exist_ok=True)
        prepared_at = utc_now()
        self.repository.upsert_effect(
            {
                "effect_key": effect_key,
                "runtime_task_id": task_id,
                "effect_type": "CREATE_TEXT_FILE",
                "target_uri": logical_uri,
                "status": EffectStatus.PREPARED,
                "prepared_at": prepared_at,
            }
        )
        self.repository.upsert_effect(
            {
                "effect_key": effect_key,
                "runtime_task_id": task_id,
                "effect_type": "CREATE_TEXT_FILE",
                "target_uri": logical_uri,
                "status": EffectStatus.EXECUTING,
                "prepared_at": prepared_at,
                "executed_at": utc_now(),
            }
        )
        result = adapter.execute(ProviderExecutionRequest(task_id, state.goal, request.filename, request.content, physical_workspace), on_status=on_status)
        if result.cancelled:
            state.status = V2TaskStatus.CANCELLED
            self.repository.update_task(state)
            self.repository.trace(task_id, "CANCELLED", {})
            return RuntimeTaskResult(False, task_id, state.status, "Task cancelled", result, effect_key=effect_key, error="CANCELLED")
        if not result.ok and not self._valid_file(physical_path, request.content):
            return self._fail(state, effect_key, "PROVIDER_FAILED", result.error or result.diagnostics or "provider failed", result)
        if not self._valid_file(physical_path, request.content):
            return self._fail(state, effect_key, "VERIFICATION_FAILED", "provider claimed success but file content was not exact", result)

        self.repository.upsert_effect(
            {
                "effect_key": effect_key,
                "runtime_task_id": task_id,
                "effect_type": "CREATE_TEXT_FILE",
                "target_uri": logical_uri,
                "status": EffectStatus.EFFECT_COMMITTED,
                "prepared_at": prepared_at,
                "executed_at": utc_now(),
                "verified_at": utc_now(),
                "provider_run_id": new_id("run"),
            }
        )
        self.repository.trace(task_id, "EFFECT_COMMITTED", {"effect_key": effect_key})
        if crash_after_effect:
            state.status = V2TaskStatus.RECOVERABLE
            self.repository.update_task(state)
            raise RuntimeError("SIMULATED_CRASH_AFTER_EFFECT")
        return self._finalize(state, request, effect_key, logical_uri, physical_path, result)

    def recover(self, task_id: str, request: CreateTextFileRequest) -> RuntimeTaskResult:
        state = self.repository.get_task(task_id)
        physical_path = self.physical_workspace(state) / request.filename
        logical_uri = f"artifact://{state.organization_id}/{task_id}/{request.filename}"
        effect_key = "create-text-file:" + hashlib.sha256(f"{logical_uri}\0{request.content}".encode()).hexdigest()
        if self._valid_file(physical_path, request.content) and self.repository.get_effect(effect_key) is not None:
            return self._finalize(state, request, effect_key, logical_uri, physical_path, None, reconciled=True)
        state.status = V2TaskStatus.RECOVERABLE
        self.repository.update_task(state)
        return RuntimeTaskResult(False, task_id, state.status, "Task requires retry", effect_key=effect_key, error="RECOVERY_INCOMPLETE")

    def cancel(self, task_id: str) -> RuntimeTaskState:
        state = self.repository.get_task(task_id)
        state.status = V2TaskStatus.CANCEL_REQUESTED
        self.repository.checkpoint(state, "CANCEL_REQUESTED")
        state.status = V2TaskStatus.CANCELLED
        self.repository.update_task(state)
        self.repository.trace(task_id, "CANCELLED", {})
        return state

    @staticmethod
    def _valid_file(path: Path, expected: str) -> bool:
        try:
            return path.is_file() and path.read_text(encoding="utf-8") == expected
        except (OSError, UnicodeError):
            return False

    def _fail(self, state, effect_key, reason, error, provider=None):
        self.repository.upsert_effect(
            {
                "effect_key": effect_key,
                "runtime_task_id": state.runtime_task_id,
                "effect_type": "CREATE_TEXT_FILE",
                "target_uri": state.workspace_uri,
                "status": EffectStatus.FAILED,
                "prepared_at": utc_now(),
            }
        )
        state.status = V2TaskStatus.FAILED
        self.repository.update_task(state)
        self.repository.trace(state.runtime_task_id, "FAILED", {"reason": reason, "error": error})
        return RuntimeTaskResult(False, state.runtime_task_id, state.status, error, provider, effect_key=effect_key, error=reason)

    def _finalize(self, state, request, effect_key, logical_uri, physical_path, provider, reconciled=False):
        artifact_id = self.repository.find_artifact_id(state.runtime_task_id, logical_uri, 1) or new_id("artifact")
        evidence_id = new_id("evidence")
        now = utc_now()
        self.repository.add_artifact(
            {
                "artifact_id": artifact_id,
                "runtime_task_id": state.runtime_task_id,
                "artifact_type": "TEXT_FILE",
                "logical_uri": logical_uri,
                "workspace_uri": state.workspace_uri,
                "version": 1,
                "created_by_agent": state.agent_id,
                "created_by_effect": effect_key,
                "provenance": dumps({"reconciled": reconciled}),
                "validation_status": "VERIFIED",
                "created_at": now,
            }
        )
        artifact_id = self.repository.find_artifact_id(state.runtime_task_id, logical_uri, 1) or artifact_id
        self.repository.add_evidence(
            {
                "evidence_id": evidence_id,
                "runtime_task_id": state.runtime_task_id,
                "effect_key": effect_key,
                "artifact_id": artifact_id,
                "evidence_type": "FILE_CONTENT",
                "validation_method": "utf8_exact_content_read",
                "expected": request.content,
                "actual": physical_path.read_text(encoding="utf-8"),
                "passed": 1,
                "created_at": now,
            }
        )
        state.artifact_refs = list(dict.fromkeys([*state.artifact_refs, artifact_id]))
        state.evidence_refs = list(dict.fromkeys([*state.evidence_refs, evidence_id]))
        state.completed_effect_keys = list(dict.fromkeys([*state.completed_effect_keys, effect_key]))
        state.status = V2TaskStatus.COMPLETE
        checkpoint_id = self.repository.checkpoint(state, "STATE_COMMITTED")
        self.repository.upsert_effect(
            {
                "effect_key": effect_key,
                "runtime_task_id": state.runtime_task_id,
                "effect_type": "CREATE_TEXT_FILE",
                "target_uri": logical_uri,
                "status": EffectStatus.STATE_COMMITTED,
                "prepared_at": now,
                "executed_at": now,
                "verified_at": now,
                "state_commit_at": now,
                "artifact_id": artifact_id,
            }
        )
        self.repository.trace(
            state.runtime_task_id,
            "COMPLETE",
            {"artifact_id": artifact_id, "evidence_id": evidence_id, "checkpoint_id": checkpoint_id},
        )
        return RuntimeTaskResult(
            True,
            state.runtime_task_id,
            state.status,
            f"Created and verified {request.filename}",
            provider,
            artifact_id,
            evidence_id,
            checkpoint_id,
            effect_key,
            logical_uri,
            str(physical_path),
            True,
        )
