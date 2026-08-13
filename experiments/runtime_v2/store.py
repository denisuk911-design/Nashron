from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import (
    AgentIdentity,
    Artifact,
    CanonicalAgentState,
    KnowledgeStatus,
    OrganizationKnowledge,
    SkillDecision,
    SkillVersion,
    StructuredHandoff,
    TraceEvent,
    utc_now,
)


class SQLitePrototypeStore:
    """Small SQLite system of record for the isolated benchmark.

    The database path is deployment configuration. Canonical records use logical
    URIs and stable IDs, so state is not tied to a local Windows path.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._ensure_schema()

    def close(self) -> None:
        self.connection.close()

    def _ensure_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS checkpoints (
                run_id TEXT PRIMARY KEY,
                revision INTEGER NOT NULL,
                state_json TEXT NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS checkpoint_history (
                run_id TEXT NOT NULL,
                revision INTEGER NOT NULL,
                state_json TEXT NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (run_id, revision)
            );
            CREATE TABLE IF NOT EXISTS artifacts (
                artifact_id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS committed_effects (
                effect_key TEXT PRIMARY KEY,
                result_json TEXT NOT NULL,
                commit_count INTEGER NOT NULL DEFAULT 1,
                committed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tool_attempts (
                effect_key TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                attempt_count INTEGER NOT NULL,
                PRIMARY KEY (effect_key, tool_name)
            );
            CREATE TABLE IF NOT EXISTS identities (
                agent_id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                profession_id TEXT NOT NULL,
                identity_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS organizational_knowledge (
                knowledge_id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                profession_id TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS skill_versions (
                skill_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                PRIMARY KEY (skill_id, organization_id, version)
            );
            CREATE TABLE IF NOT EXISTS handoffs (
                handoff_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS traces (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def save_state(self, state: CanonicalAgentState, reason: str) -> CanonicalAgentState:
        row = self.connection.execute(
            "SELECT revision FROM checkpoints WHERE run_id = ?", (state.run_id,)
        ).fetchone()
        revision = (int(row["revision"]) if row else 0) + 1
        state.checkpoint.revision = revision
        state.checkpoint.reason = reason
        state.checkpoint.created_at = utc_now()
        payload = json.dumps(state.to_dict(), ensure_ascii=False, sort_keys=True)
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO checkpoints(run_id, revision, state_json, reason, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    revision = excluded.revision,
                    state_json = excluded.state_json,
                    reason = excluded.reason,
                    created_at = excluded.created_at
                """,
                (state.run_id, revision, payload, reason, state.checkpoint.created_at),
            )
            self.connection.execute(
                """
                INSERT INTO checkpoint_history(run_id, revision, state_json, reason, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (state.run_id, revision, payload, reason, state.checkpoint.created_at),
            )
        return state

    def load_state(self, run_id: str) -> CanonicalAgentState:
        row = self.connection.execute(
            "SELECT state_json FROM checkpoints WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            raise KeyError(run_id)
        return CanonicalAgentState.from_dict(json.loads(row["state_json"]))

    def checkpoint_count(self, run_id: str) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) AS count FROM checkpoint_history WHERE run_id = ?", (run_id,)
        ).fetchone()
        return int(row["count"])

    def save_artifact(self, artifact: Artifact) -> None:
        payload = json.dumps(asdict(artifact), ensure_ascii=False, sort_keys=True)
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO artifacts(artifact_id, organization_id, task_id, payload_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(artifact_id) DO UPDATE SET payload_json = excluded.payload_json
                """,
                (artifact.artifact_id, artifact.organization_id, artifact.task_id, payload),
            )

    def get_artifact(self, artifact_id: str) -> Artifact | None:
        row = self.connection.execute(
            "SELECT payload_json FROM artifacts WHERE artifact_id = ?", (artifact_id,)
        ).fetchone()
        if row is None:
            return None
        payload = json.loads(row["payload_json"])
        payload["provenance"] = tuple(payload.get("provenance", ()))
        return Artifact(**payload)

    def commit_effect(self, effect_key: str, result: dict[str, Any]) -> bool:
        payload = json.dumps(result, ensure_ascii=False, sort_keys=True)
        with self.connection:
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO committed_effects(effect_key, result_json, committed_at)
                VALUES (?, ?, ?)
                """,
                (effect_key, payload, utc_now()),
            )
        return cursor.rowcount == 1

    def load_effect(self, effect_key: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT result_json FROM committed_effects WHERE effect_key = ?", (effect_key,)
        ).fetchone()
        return json.loads(row["result_json"]) if row else None

    def effect_commit_count(self, effect_key: str) -> int:
        row = self.connection.execute(
            "SELECT commit_count FROM committed_effects WHERE effect_key = ?", (effect_key,)
        ).fetchone()
        return int(row["commit_count"]) if row else 0

    def record_tool_attempt(self, effect_key: str, tool_name: str) -> int:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO tool_attempts(effect_key, tool_name, attempt_count)
                VALUES (?, ?, 1)
                ON CONFLICT(effect_key, tool_name) DO UPDATE SET
                    attempt_count = attempt_count + 1
                """,
                (effect_key, tool_name),
            )
        row = self.connection.execute(
            "SELECT attempt_count FROM tool_attempts WHERE effect_key = ? AND tool_name = ?",
            (effect_key, tool_name),
        ).fetchone()
        return int(row["attempt_count"])

    def save_identity(self, identity: AgentIdentity, profession_id: str) -> None:
        payload = json.dumps(asdict(identity), ensure_ascii=False, sort_keys=True)
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO identities(agent_id, organization_id, profession_id, identity_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    organization_id = excluded.organization_id,
                    profession_id = excluded.profession_id,
                    identity_json = excluded.identity_json
                """,
                (identity.agent_id, identity.organization_id, profession_id, payload),
            )

    def get_identity(self, agent_id: str) -> AgentIdentity | None:
        row = self.connection.execute(
            "SELECT identity_json FROM identities WHERE agent_id = ?", (agent_id,)
        ).fetchone()
        return AgentIdentity(**json.loads(row["identity_json"])) if row else None

    def delete_identity(self, agent_id: str) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM identities WHERE agent_id = ?", (agent_id,))
            rows = self.connection.execute(
                "SELECT knowledge_id, payload_json FROM organizational_knowledge"
            ).fetchall()
            for row in rows:
                payload = json.loads(row["payload_json"])
                if payload.get("contributor_id") != agent_id:
                    continue
                payload["contributor_status"] = "DELETED_CONTRIBUTOR"
                self.connection.execute(
                    "UPDATE organizational_knowledge SET payload_json = ? WHERE knowledge_id = ?",
                    (json.dumps(payload, ensure_ascii=False, sort_keys=True), row["knowledge_id"]),
                )

    def save_knowledge(self, record: OrganizationKnowledge) -> None:
        payload = json.dumps(asdict(record), ensure_ascii=False, sort_keys=True)
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO organizational_knowledge(
                    knowledge_id, organization_id, profession_id, payload_json
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(knowledge_id) DO UPDATE SET payload_json = excluded.payload_json
                """,
                (record.knowledge_id, record.organization_id, record.profession_id, payload),
            )

    def list_validated_knowledge(
        self, organization_id: str, profession_id: str
    ) -> list[OrganizationKnowledge]:
        rows = self.connection.execute(
            """
            SELECT payload_json FROM organizational_knowledge
            WHERE organization_id = ? AND profession_id = ?
            ORDER BY knowledge_id
            """,
            (organization_id, profession_id),
        ).fetchall()
        records: list[OrganizationKnowledge] = []
        for row in rows:
            payload = json.loads(row["payload_json"])
            if payload.get("status") != KnowledgeStatus.VALIDATED:
                continue
            payload["source_refs"] = tuple(payload.get("source_refs", ()))
            payload["evidence_ids"] = tuple(payload.get("evidence_ids", ()))
            payload["status"] = KnowledgeStatus(payload["status"])
            records.append(OrganizationKnowledge(**payload))
        return records

    def save_skill(self, skill: SkillVersion) -> None:
        payload = json.dumps(asdict(skill), ensure_ascii=False, sort_keys=True)
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO skill_versions(skill_id, organization_id, version, status, payload_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(skill_id, organization_id, version) DO UPDATE SET
                    status = excluded.status,
                    payload_json = excluded.payload_json
                """,
                (skill.skill_id, skill.organization_id, skill.version, skill.status, payload),
            )

    def active_skill(self, organization_id: str, skill_id: str) -> SkillVersion | None:
        row = self.connection.execute(
            """
            SELECT payload_json FROM skill_versions
            WHERE organization_id = ? AND skill_id = ? AND status IN (?, ?)
            ORDER BY version DESC LIMIT 1
            """,
            (organization_id, skill_id, SkillDecision.CURRENT, SkillDecision.PROMOTED),
        ).fetchone()
        if row is None:
            return None
        payload = json.loads(row["payload_json"])
        payload["status"] = SkillDecision(payload["status"])
        return SkillVersion(**payload)

    def list_active_skills(self, organization_id: str, profession_id: str) -> list[SkillVersion]:
        rows = self.connection.execute(
            """
            SELECT payload_json FROM skill_versions
            WHERE organization_id = ? AND status IN (?, ?)
            ORDER BY skill_id, version DESC
            """,
            (organization_id, SkillDecision.CURRENT, SkillDecision.PROMOTED),
        ).fetchall()
        selected: dict[str, SkillVersion] = {}
        for row in rows:
            payload = json.loads(row["payload_json"])
            if payload.get("profession_id") != profession_id:
                continue
            payload["status"] = SkillDecision(payload["status"])
            skill = SkillVersion(**payload)
            selected.setdefault(skill.skill_id, skill)
        return list(selected.values())

    def save_handoff(self, handoff: StructuredHandoff) -> None:
        payload = json.dumps(asdict(handoff), ensure_ascii=False, sort_keys=True)
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO handoffs(handoff_id, payload_json) VALUES (?, ?)
                ON CONFLICT(handoff_id) DO UPDATE SET payload_json = excluded.payload_json
                """,
                (handoff.handoff_id, payload),
            )

    def get_handoff(self, handoff_id: str) -> StructuredHandoff:
        row = self.connection.execute(
            "SELECT payload_json FROM handoffs WHERE handoff_id = ?", (handoff_id,)
        ).fetchone()
        if row is None:
            raise KeyError(handoff_id)
        return StructuredHandoff(**json.loads(row["payload_json"]))

    def append_trace(self, event: TraceEvent) -> None:
        payload = json.dumps(asdict(event), ensure_ascii=False, sort_keys=True)
        with self.connection:
            self.connection.execute(
                "INSERT INTO traces(trace_id, run_id, payload_json) VALUES (?, ?, ?)",
                (event.trace_id, event.run_id, payload),
            )

    def list_traces(self, run_id: str) -> list[TraceEvent]:
        rows = self.connection.execute(
            "SELECT payload_json FROM traces WHERE run_id = ? ORDER BY sequence", (run_id,)
        ).fetchall()
        events: list[TraceEvent] = []
        tuple_fields = {
            "context_input_ids",
            "skill_ids",
            "knowledge_ids",
            "tool_names",
            "artifact_ids",
            "handoff_ids",
            "errors",
        }
        for row in rows:
            payload = json.loads(row["payload_json"])
            for key in tuple_fields:
                payload[key] = tuple(payload.get(key, ()))
            events.append(TraceEvent(**payload))
        return events

    def foreign_key_check(self) -> list[sqlite3.Row]:
        return self.connection.execute("PRAGMA foreign_key_check").fetchall()
