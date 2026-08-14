from __future__ import annotations

import json
import sqlite3
from typing import Any


RUNTIME_V2_SCHEMA_VERSION = "1.0"


def ensure_runtime_v2_schema(conn: sqlite3.Connection) -> None:
    """Create only the V2 tables; this migration is additive and FK-safe."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS runtime_v2_tasks (
            runtime_task_id TEXT PRIMARY KEY,
            schema_version TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            organization_id TEXT NOT NULL,
            intent TEXT NOT NULL,
            goal TEXT NOT NULL,
            status TEXT NOT NULL,
            workspace_uri TEXT NOT NULL,
            provider_binding TEXT NOT NULL DEFAULT '{}',
            artifact_refs TEXT NOT NULL DEFAULT '[]',
            evidence_refs TEXT NOT NULL DEFAULT '[]',
            checkpoint_id TEXT,
            completed_effect_keys TEXT NOT NULL DEFAULT '[]',
            context_refs TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS runtime_v2_checkpoints (
            checkpoint_id TEXT PRIMARY KEY,
            runtime_task_id TEXT NOT NULL,
            state_json TEXT NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (runtime_task_id) REFERENCES runtime_v2_tasks(runtime_task_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS runtime_v2_artifacts (
            artifact_id TEXT PRIMARY KEY,
            runtime_task_id TEXT NOT NULL,
            artifact_type TEXT NOT NULL,
            logical_uri TEXT NOT NULL,
            workspace_uri TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            created_by_agent TEXT NOT NULL,
            created_by_effect TEXT NOT NULL,
            provenance TEXT NOT NULL DEFAULT '{}',
            validation_status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(runtime_task_id, logical_uri, version),
            FOREIGN KEY (runtime_task_id) REFERENCES runtime_v2_tasks(runtime_task_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS runtime_v2_evidence (
            evidence_id TEXT PRIMARY KEY,
            runtime_task_id TEXT NOT NULL,
            effect_key TEXT NOT NULL,
            artifact_id TEXT,
            evidence_type TEXT NOT NULL,
            validation_method TEXT NOT NULL,
            expected TEXT NOT NULL,
            actual TEXT NOT NULL,
            passed INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (runtime_task_id) REFERENCES runtime_v2_tasks(runtime_task_id) ON DELETE CASCADE,
            FOREIGN KEY (artifact_id) REFERENCES runtime_v2_artifacts(artifact_id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS runtime_v2_effects (
            effect_key TEXT PRIMARY KEY,
            runtime_task_id TEXT NOT NULL,
            effect_type TEXT NOT NULL,
            target_uri TEXT NOT NULL,
            status TEXT NOT NULL,
            prepared_at TEXT NOT NULL,
            executed_at TEXT,
            verified_at TEXT,
            state_commit_at TEXT,
            provider_run_id TEXT,
            artifact_id TEXT,
            FOREIGN KEY (runtime_task_id) REFERENCES runtime_v2_tasks(runtime_task_id) ON DELETE CASCADE,
            FOREIGN KEY (artifact_id) REFERENCES runtime_v2_artifacts(artifact_id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS runtime_v2_traces (
            trace_id TEXT PRIMARY KEY,
            runtime_task_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            detail_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (runtime_task_id) REFERENCES runtime_v2_tasks(runtime_task_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS runtime_v2_context_refs (
            context_ref_id TEXT PRIMARY KEY,
            runtime_task_id TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            priority TEXT NOT NULL,
            content_hash TEXT NOT NULL DEFAULT '',
            token_estimate INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (runtime_task_id) REFERENCES runtime_v2_tasks(runtime_task_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_runtime_v2_tasks_status ON runtime_v2_tasks(status);
        CREATE INDEX IF NOT EXISTS idx_runtime_v2_traces_task ON runtime_v2_traces(runtime_task_id, created_at);
        """
    )


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def loads(value: str, default: Any) -> Any:
    try:
        parsed = json.loads(value)
        return parsed
    except (TypeError, ValueError, json.JSONDecodeError):
        return default
