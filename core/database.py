from __future__ import annotations

import shutil
import sqlite3
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .management_models import AgentProfile, RoleProfile
from .models import Conversation, Message, UserMemory
from .provider_models import ProviderHealth, ProviderProfile


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self) -> None:
        self._prepare_existing_storage()
        with self.connect() as conn:
            self._repair_renamed_message_foreign_keys(conn)
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL DEFAULT 'ok',
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS user_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS app_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    detail TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            self._ensure_dynamic_message_roles(conn)
            self._ensure_phase1_schema(conn)
            self._ensure_run_status_schema(conn)
            self._ensure_usage_schema_extensions(conn)
            self._ensure_thread_question_schema(conn)
            self._ensure_finding_schema_extensions(conn)
            self._ensure_artifact_finding_link_schema(conn)
            self._ensure_skill_package_schema(conn)
            self._ensure_knowledge_schema(conn)
            self._ensure_standards_schema(conn)
            self._ensure_management_schema(conn)
            self._ensure_provider_schema(conn)
            self._repair_legacy_provider_diagnostics(conn)
            self._ensure_work_context_schema(conn)
            self._ensure_universal_schema(conn)
            self._ensure_organization_expansion_schema(conn)
            self._ensure_learning_evidence_schema(conn)
            self._ensure_director_schema(conn)
            self._ensure_runtime_v2_schema(conn)
            self._repair_renamed_message_foreign_keys(conn)
            self._repair_orphaned_routing_decisions(conn)
        # A legacy writable-schema migration could leave freed pages outside
        # SQLite's freelist. Run the same narrowly scoped check after schema
        # repair so the problem cannot be recreated by an old database.
        self._prepare_existing_storage()

    @staticmethod
    def _ensure_runtime_v2_schema(conn: sqlite3.Connection) -> None:
        from runtime_v2.sqlite_repository import ensure_runtime_v2_schema

        ensure_runtime_v2_schema(conn)

    def _prepare_existing_storage(self) -> None:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return
        conn = sqlite3.connect(self.path)
        try:
            try:
                integrity_rows = conn.execute("PRAGMA integrity_check").fetchall()
            except sqlite3.DatabaseError as exc:
                # A known legacy migration could leave a zero-root
                # messages_old catalog entry. The schema repair in initialize
                # removes it before this health check is run a second time.
                if "malformed database schema (messages_old)" in str(exc):
                    return
                raise
            integrity_lines = [
                line.strip()
                for row in integrity_rows
                for line in str(row[0] or "").splitlines()
                if line.strip()
                and line.strip().lower() != "ok"
                and not re.fullmatch(r"\*\*\* in database .+ \*\*\*", line.strip())
            ]
            known_page_damage = bool(integrity_lines) and all(
                re.fullmatch(r"Page \d+: never used", line) for line in integrity_lines
            )
            foreign_key_rows = conn.execute("PRAGMA foreign_key_check").fetchall()
            known_orphans = any(str(row[0]) == "routing_decisions" for row in foreign_key_rows)
            if not known_page_damage and not known_orphans:
                return
            self._create_integrity_backup()
            if known_page_damage:
                conn.execute("VACUUM")
                remaining = [
                    line.strip()
                    for row in conn.execute("PRAGMA integrity_check").fetchall()
                    for line in str(row[0] or "").splitlines()
                    if line.strip()
                    and line.strip().lower() != "ok"
                    and not re.fullmatch(r"\*\*\* in database .+ \*\*\*", line.strip())
                ]
                if remaining:
                    raise sqlite3.DatabaseError("database_integrity_repair_failed: " + "; ".join(remaining[:5]))
        finally:
            conn.close()

    def _create_integrity_backup(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup_path = self.path.with_name(f"{self.path.stem}.integrity_backup_{timestamp}{self.path.suffix}")
        shutil.copy2(self.path, backup_path)
        return backup_path

    @staticmethod
    def _repair_orphaned_routing_decisions(conn: sqlite3.Connection) -> None:
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'routing_decisions'"
        ).fetchone()
        messages_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'messages'"
        ).fetchone()
        if table_exists is None or messages_exists is None:
            return
        conn.execute(
            """
            DELETE FROM routing_decisions
            WHERE message_id IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM messages WHERE messages.id = routing_decisions.message_id)
            """
        )

    @staticmethod
    def _repair_legacy_provider_diagnostics(conn: sqlite3.Connection) -> None:
        """Repair one known pre-Unicode-pipeline Codex status value.

        Older Windows builds decoded the CP1251 bytes for ``авторизован`` as
        CP1255, which produced Hebrew-looking text in the persisted diagnostic.
        The current CLI pipeline is UTF-8; this migration only touches the exact
        legacy value and only for an authenticated Codex check.
        """
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'provider_health_checks'"
        ).fetchone()
        if table_exists is None:
            return
        conn.execute(
            """
            UPDATE provider_health_checks
            SET diagnostic = 'Codex: авторизован'
            WHERE provider_id = 'CODEX_CLI'
              AND authentication_status = 'AUTHENTICATED'
              AND diagnostic = ?
            """,
            ("Codex: \u05d0\u05d2\u05e2\u05de\u05e0\u05d8\u05d7\u05de\u05d2\u05d0\u05dd",),
        )

    def _ensure_universal_schema(self, conn: sqlite3.Connection) -> None:
        """U1 domain-neutral organization and profession foundation."""
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS professions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT '',
                responsibilities TEXT NOT NULL DEFAULT '[]',
                typical_results TEXT NOT NULL DEFAULT '[]',
                required_capabilities TEXT NOT NULL DEFAULT '[]',
                initial_skills TEXT NOT NULL DEFAULT '[]',
                recommended_tools TEXT NOT NULL DEFAULT '[]',
                knowledge_sources TEXT NOT NULL DEFAULT '[]',
                qualification_method TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_by TEXT NOT NULL DEFAULT 'owner',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS organizations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                purpose TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_by TEXT NOT NULL DEFAULT 'owner',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS organization_departments (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(organization_id, name),
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS organization_members (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                department_id TEXT,
                agent_id TEXT,
                profession_id TEXT,
                role_id TEXT,
                position TEXT NOT NULL DEFAULT '',
                responsibilities TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
                FOREIGN KEY (department_id) REFERENCES organization_departments(id) ON DELETE SET NULL,
                FOREIGN KEY (agent_id) REFERENCES agent_profiles(agent_id) ON DELETE SET NULL,
                FOREIGN KEY (profession_id) REFERENCES professions(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS organization_templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                purpose TEXT NOT NULL DEFAULT '',
                recommended_team_size TEXT NOT NULL DEFAULT '',
                roles TEXT NOT NULL DEFAULT '[]',
                hierarchy TEXT NOT NULL DEFAULT '[]',
                workflow_id TEXT,
                handoff_rules TEXT NOT NULL DEFAULT '[]',
                review_rules TEXT NOT NULL DEFAULT '[]',
                approval_rules TEXT NOT NULL DEFAULT '[]',
                permissions TEXT NOT NULL DEFAULT '[]',
                required_capabilities TEXT NOT NULL DEFAULT '[]',
                recommended_tools TEXT NOT NULL DEFAULT '[]',
                learning_roles TEXT NOT NULL DEFAULT '[]',
                quality_controls TEXT NOT NULL DEFAULT '[]',
                source_rationale TEXT NOT NULL DEFAULT '',
                version TEXT NOT NULL DEFAULT '1.0.0',
                limitations TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_by TEXT NOT NULL DEFAULT 'owner',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                version TEXT NOT NULL DEFAULT '1.0.0',
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_by TEXT NOT NULL DEFAULT 'owner',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS workflow_steps (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                step_order INTEGER NOT NULL,
                responsibility TEXT NOT NULL DEFAULT '',
                operation TEXT NOT NULL DEFAULT '',
                required_inputs TEXT NOT NULL DEFAULT '[]',
                expected_outputs TEXT NOT NULL DEFAULT '[]',
                review_requirement TEXT NOT NULL DEFAULT '',
                approval_requirement TEXT NOT NULL DEFAULT '',
                next_step TEXT,
                FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS agent_runtime_states (
                agent_id TEXT PRIMARY KEY,
                organization_id TEXT,
                current_task_id TEXT,
                current_operation TEXT NOT NULL DEFAULT '',
                current_plan TEXT NOT NULL DEFAULT '[]',
                active_artifact_ids TEXT NOT NULL DEFAULT '[]',
                open_finding_ids TEXT NOT NULL DEFAULT '[]',
                checkpoint TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'IDLE',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agent_profiles(agent_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS learning_sources (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source_type TEXT NOT NULL,
                location TEXT NOT NULL DEFAULT '',
                added_by TEXT NOT NULL DEFAULT 'owner',
                trust_metadata TEXT NOT NULL DEFAULT '{}',
                processed_state TEXT NOT NULL DEFAULT 'NEW',
                last_checked TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.execute(
            "INSERT OR REPLACE INTO schema_meta (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            ("universal_schema_version", "1.0"),
        )

    def _ensure_organization_expansion_schema(self, conn: sqlite3.Connection) -> None:
        """Add operational organization metadata without rewriting existing data."""
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS management_models (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT '',
                structure_type TEXT NOT NULL DEFAULT '',
                decision_model TEXT NOT NULL DEFAULT '',
                responsibility_model TEXT NOT NULL DEFAULT '',
                workflow_style TEXT NOT NULL DEFAULT '',
                recommended_team_size TEXT NOT NULL DEFAULT '',
                advantages TEXT NOT NULL DEFAULT '[]',
                limitations TEXT NOT NULL DEFAULT '[]',
                source_rationale TEXT NOT NULL DEFAULT '',
                version TEXT NOT NULL DEFAULT '1.0.0',
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_by TEXT NOT NULL DEFAULT 'owner',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS responsibility_models (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT '',
                accountabilities TEXT NOT NULL DEFAULT '[]',
                source_rationale TEXT NOT NULL DEFAULT '',
                version TEXT NOT NULL DEFAULT '1.0.0',
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS organization_workspaces (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL UNIQUE,
                conversation_id INTEGER,
                workspace_path TEXT NOT NULL DEFAULT '',
                routing_config TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'PROVISIONING',
                is_active INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS organization_activation_events (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                status TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
            );
            """
        )

        for table, columns in {
            "organizations": {
                "management_model_id": "TEXT",
                "domain_package": "TEXT NOT NULL DEFAULT ''",
                "responsibility_model_id": "TEXT",
                "active_template_id": "TEXT",
            },
            "organization_templates": {
                "management_model_id": "TEXT",
                "domain_package": "TEXT NOT NULL DEFAULT ''",
                "responsibility_model_id": "TEXT",
                "team_size_variants": "TEXT NOT NULL DEFAULT '{}'",
                "catalog_category": "TEXT NOT NULL DEFAULT 'Other'",
                "review_required": "INTEGER NOT NULL DEFAULT 0",
                "research_required": "INTEGER NOT NULL DEFAULT 0",
                "learning_support": "INTEGER NOT NULL DEFAULT 0",
            },
            "organization_members": {
                "provider_id": "TEXT NOT NULL DEFAULT 'UNAVAILABLE'",
                "assignment_mode": "TEXT NOT NULL DEFAULT 'AUTO_CREATE'",
                "provisioning_status": "TEXT NOT NULL DEFAULT 'UNASSIGNED'",
                "missing_reason": "TEXT NOT NULL DEFAULT ''",
                "functional_manager_member_id": "TEXT",
                "project_manager_member_id": "TEXT",
                "required_capabilities": "TEXT NOT NULL DEFAULT '[]'",
                "permissions": "TEXT NOT NULL DEFAULT '[]'",
                "recommended_tools": "TEXT NOT NULL DEFAULT '[]'",
            },
        }.items():
            existing = {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            for name, definition in columns.items():
                if name not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
        conn.execute(
            "INSERT OR REPLACE INTO schema_meta (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            ("organization_expansion_schema_version", "1.0"),
        )

    def _ensure_learning_evidence_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS experience_records (
                id TEXT PRIMARY KEY,
                agent_id TEXT,
                employee_name TEXT NOT NULL DEFAULT '',
                organization_id TEXT,
                task_id TEXT,
                run_id TEXT UNIQUE,
                summary TEXT NOT NULL DEFAULT '',
                skills_used TEXT NOT NULL DEFAULT '[]',
                errors_found TEXT NOT NULL DEFAULT '[]',
                corrections TEXT NOT NULL DEFAULT '[]',
                lessons_learned TEXT NOT NULL DEFAULT '[]',
                knowledge_created TEXT NOT NULL DEFAULT '[]',
                evidence TEXT NOT NULL DEFAULT '{}',
                outcome TEXT NOT NULL DEFAULT 'RECORDED',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agent_profiles(agent_id) ON DELETE SET NULL,
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE SET NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL,
                FOREIGN KEY (run_id) REFERENCES agent_runs(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS learning_queue (
                id TEXT PRIMARY KEY,
                agent_id TEXT,
                employee_name TEXT NOT NULL DEFAULT '',
                competence TEXT NOT NULL,
                reason TEXT NOT NULL,
                source_id TEXT,
                status TEXT NOT NULL DEFAULT 'PROPOSED',
                practice_task TEXT NOT NULL DEFAULT '',
                evidence TEXT NOT NULL DEFAULT '{}',
                created_by TEXT NOT NULL DEFAULT 'SYSTEM',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agent_profiles(agent_id) ON DELETE SET NULL,
                FOREIGN KEY (source_id) REFERENCES learning_sources(id) ON DELETE SET NULL
            );
            """
        )
        existing = {str(row["name"]) for row in conn.execute("PRAGMA table_info(learning_queue)").fetchall()}
        for name, definition in {
            "skill_id": "TEXT",
            "coordinator_agent_id": "TEXT",
            "qualification_criteria": "TEXT NOT NULL DEFAULT '[]'",
            "practice_run_id": "TEXT",
            "review_run_id": "TEXT",
            "completed_at": "TEXT",
        }.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE learning_queue ADD COLUMN {name} {definition}")

    def _ensure_director_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS project_plans (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                director_agent_id TEXT NOT NULL,
                goal TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'DRAFT',
                clarification_questions TEXT NOT NULL DEFAULT '[]',
                missing_roles TEXT NOT NULL DEFAULT '[]',
                owner_approval_required INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (director_agent_id) REFERENCES agent_profiles(agent_id) ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS work_assignments (
                id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                agent_id TEXT,
                role_id TEXT,
                position TEXT NOT NULL DEFAULT '',
                sequence_no INTEGER NOT NULL,
                review_required INTEGER NOT NULL DEFAULT 0,
                acceptance_criteria TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'ASSIGNED',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plan_id) REFERENCES project_plans(id) ON DELETE CASCADE,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (agent_id) REFERENCES agent_profiles(agent_id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS director_workflow_events (
                id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL,
                assignment_id TEXT,
                event_type TEXT NOT NULL,
                actor_agent_id TEXT,
                detail TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plan_id) REFERENCES project_plans(id) ON DELETE CASCADE,
                FOREIGN KEY (assignment_id) REFERENCES work_assignments(id) ON DELETE SET NULL
            );
            """
        )
        extensions = {
            "project_plans": {
                "owner_message_id": "INTEGER",
                "summary": "TEXT NOT NULL DEFAULT ''",
                "max_rework_attempts": "INTEGER NOT NULL DEFAULT 2",
                "completed_at": "TEXT",
            },
            "work_assignments": {
                "assignment_type": "TEXT NOT NULL DEFAULT 'EXECUTION'",
                "responsibility": "TEXT NOT NULL DEFAULT 'RESPONSIBLE'",
                "depends_on_assignment_id": "TEXT",
                "reviewed_assignment_id": "TEXT",
                "attempt_no": "INTEGER NOT NULL DEFAULT 0",
                "result_run_id": "TEXT",
                "result_message_id": "INTEGER",
                "result_summary": "TEXT NOT NULL DEFAULT ''",
                "evidence": "TEXT NOT NULL DEFAULT '{}'",
                "review_decision": "TEXT NOT NULL DEFAULT ''",
                "failure_reason": "TEXT NOT NULL DEFAULT ''",
                "started_at": "TEXT",
                "completed_at": "TEXT",
            },
        }
        for table, columns in extensions.items():
            existing = {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            for name, definition in columns.items():
                if name not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

    def _ensure_work_context_schema(self, conn: sqlite3.Connection) -> None:
        """Persistent task intent, artifact handoff and provider contracts."""
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS active_work_contexts (
                conversation_id INTEGER PRIMARY KEY,
                thread_id TEXT NOT NULL,
                task_id TEXT,
                task_title TEXT NOT NULL DEFAULT '',
                task_goal TEXT NOT NULL DEFAULT '',
                current_owner_agent_id TEXT,
                previous_owner_agent_id TEXT,
                active_artifact_ids TEXT NOT NULL DEFAULT '[]',
                primary_artifact_id TEXT,
                artifact_type TEXT NOT NULL DEFAULT '',
                source_agent_id TEXT,
                current_operation TEXT NOT NULL DEFAULT 'UNKNOWN',
                expected_output_type TEXT NOT NULL DEFAULT '',
                unresolved_questions TEXT NOT NULL DEFAULT '[]',
                last_completed_action TEXT NOT NULL DEFAULT '',
                last_user_intent TEXT NOT NULL DEFAULT 'UNKNOWN',
                handoff_state TEXT NOT NULL DEFAULT 'NONE',
                status TEXT NOT NULL DEFAULT 'CURRENT',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS artifact_payloads (
                artifact_id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL DEFAULT '',
                source_agent_id TEXT,
                source_message_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS work_handoffs (
                id TEXT PRIMARY KEY,
                conversation_id INTEGER NOT NULL,
                task_id TEXT,
                from_agent_id TEXT,
                to_agent_id TEXT NOT NULL,
                artifact_ids TEXT NOT NULL DEFAULT '[]',
                requested_operation TEXT NOT NULL,
                expected_output TEXT NOT NULL DEFAULT '',
                expected_output_type TEXT NOT NULL DEFAULT '',
                user_instruction TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                superseded_at TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS execution_contracts (
                id TEXT PRIMARY KEY,
                conversation_id INTEGER NOT NULL,
                task_id TEXT,
                run_id TEXT,
                agent_id TEXT NOT NULL,
                role TEXT NOT NULL,
                user_instruction TEXT NOT NULL,
                intent TEXT NOT NULL,
                input_artifact_ids TEXT NOT NULL DEFAULT '[]',
                required_operation TEXT NOT NULL,
                expected_output TEXT NOT NULL DEFAULT '',
                expected_output_type TEXT NOT NULL DEFAULT '',
                allowed_tools TEXT NOT NULL DEFAULT '[]',
                required_evidence TEXT NOT NULL DEFAULT '[]',
                completion_criteria TEXT NOT NULL DEFAULT '[]',
                forbidden_substitutions TEXT NOT NULL DEFAULT '[]',
                clarification_required INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

    def _ensure_usage_schema_extensions(self, conn: sqlite3.Connection) -> None:
        for table in ("knowledge_usage", "standard_usage"):
            columns = {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            if "evidence" not in columns:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN evidence TEXT NOT NULL DEFAULT '{{}}'")

    def _ensure_run_status_schema(self, conn: sqlite3.Connection) -> None:
        columns = {str(row["name"]) for row in conn.execute("PRAGMA table_info(agent_runs)").fetchall()}
        if "status" not in columns:
            conn.execute("ALTER TABLE agent_runs ADD COLUMN status TEXT NOT NULL DEFAULT 'QUEUED'")

    def _ensure_dynamic_message_roles(self, conn: sqlite3.Connection) -> None:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'messages'"
        ).fetchone()
        table_sql = str(row["sql"] if row else "")
        if "CHECK" not in table_sql.upper():
            return
        conn.executescript(
            """
            ALTER TABLE messages RENAME TO messages_old;
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'ok',
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );
            INSERT INTO messages (id, conversation_id, role, content, created_at, status)
                SELECT id, conversation_id, role, content, created_at, status FROM messages_old;
            DROP TABLE messages_old;
            """
        )

    def _ensure_skill_package_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS skill_packages (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                purpose TEXT NOT NULL DEFAULT '',
                supported_roles TEXT NOT NULL DEFAULT '[]',
                prerequisites TEXT NOT NULL DEFAULT '',
                source_material TEXT NOT NULL DEFAULT '[]',
                instructions TEXT NOT NULL DEFAULT '',
                tools TEXT NOT NULL DEFAULT '[]',
                expected_inputs TEXT NOT NULL DEFAULT '',
                expected_outputs TEXT NOT NULL DEFAULT '',
                prohibited_actions TEXT NOT NULL DEFAULT '',
                validation_checklist TEXT NOT NULL DEFAULT '[]',
                examples TEXT NOT NULL DEFAULT '[]',
                negative_examples TEXT NOT NULL DEFAULT '[]',
                qualification_tasks TEXT NOT NULL DEFAULT '[]',
                version TEXT NOT NULL DEFAULT '0.1.0',
                status TEXT NOT NULL DEFAULT 'DRAFT',
                created_by TEXT NOT NULL DEFAULT 'owner',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS skill_package_events (
                id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                detail TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (skill_id) REFERENCES skill_packages(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS employee_skill_assignments (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'ASSIGNED',
                assigned_by TEXT NOT NULL DEFAULT 'owner',
                evidence TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(agent_id, skill_id),
                FOREIGN KEY (skill_id) REFERENCES skill_packages(id) ON DELETE CASCADE
            );
            """
        )

    def _ensure_knowledge_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS knowledge_cards (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL DEFAULT '',
                source_type TEXT NOT NULL DEFAULT 'internal_note',
                source_title TEXT NOT NULL DEFAULT '',
                source_uri TEXT NOT NULL DEFAULT '',
                source_authority TEXT NOT NULL DEFAULT 'UNVERIFIED',
                source_hash TEXT NOT NULL DEFAULT '',
                role_ids TEXT NOT NULL DEFAULT '[]',
                tags TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'DRAFT',
                version TEXT NOT NULL DEFAULT '0.1.0',
                review_notes TEXT NOT NULL DEFAULT '',
                created_by TEXT NOT NULL DEFAULT 'owner',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS knowledge_card_events (
                id TEXT PRIMARY KEY,
                knowledge_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                detail TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (knowledge_id) REFERENCES knowledge_cards(id) ON DELETE CASCADE
            );
            """
        )

    def _ensure_standards_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS standard_cards (
                id TEXT PRIMARY KEY,
                code TEXT NOT NULL,
                title TEXT NOT NULL,
                requirement TEXT NOT NULL DEFAULT '',
                scope TEXT NOT NULL DEFAULT '',
                source_title TEXT NOT NULL DEFAULT '',
                source_uri TEXT NOT NULL DEFAULT '',
                source_hash TEXT NOT NULL DEFAULT '',
                authority TEXT NOT NULL DEFAULT 'INTERNAL',
                mandatory_level TEXT NOT NULL DEFAULT 'GUIDANCE',
                role_ids TEXT NOT NULL DEFAULT '[]',
                tags TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'DRAFT',
                version TEXT NOT NULL DEFAULT '0.1.0',
                review_notes TEXT NOT NULL DEFAULT '',
                created_by TEXT NOT NULL DEFAULT 'owner',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS standard_card_events (
                id TEXT PRIMARY KEY,
                standard_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                detail TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (standard_id) REFERENCES standard_cards(id) ON DELETE CASCADE
            );
            """
        )

    def _ensure_finding_schema_extensions(self, conn: sqlite3.Connection) -> None:
        columns = {str(row["name"]) for row in conn.execute("PRAGMA table_info(findings)").fetchall()}
        additions = {
            "standard_id": "TEXT",
            "finding_type": "TEXT NOT NULL DEFAULT 'QA_FINDING'",
            "repeat_key": "TEXT",
        }
        for name, definition in additions.items():
            if name not in columns:
                conn.execute(f"ALTER TABLE findings ADD COLUMN {name} {definition}")

    def _ensure_artifact_finding_link_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS artifact_finding_links (
                id TEXT PRIMARY KEY,
                artifact_id TEXT NOT NULL,
                finding_id TEXT NOT NULL,
                match_type TEXT NOT NULL,
                confidence TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (artifact_id, finding_id),
                FOREIGN KEY (artifact_id) REFERENCES artifacts(id),
                FOREIGN KEY (finding_id) REFERENCES findings(id)
            );

            CREATE TABLE IF NOT EXISTS artifact_finding_link_events (
                id TEXT PRIMARY KEY,
                link_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                detail TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (link_id) REFERENCES artifact_finding_links(id)
            );
            """
        )

    def _repair_renamed_message_foreign_keys(self, conn: sqlite3.Connection) -> None:
        conn.execute("PRAGMA writable_schema = ON")
        messages_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'messages'"
        ).fetchone()
        deleted_count = 0
        if messages_exists:
            deleted = conn.execute(
                """
                DELETE FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'messages_old'
                  AND sql LIKE 'CREATE TABLE%messages%'
                """
            )
            deleted_count = max(0, deleted.rowcount)
        rows = conn.execute(
            """
            SELECT name, sql
            FROM sqlite_master
            WHERE type = 'table'
              AND sql LIKE '%messages_old%'
            """
        ).fetchall()
        if not rows:
            if deleted_count:
                schema_version = int(conn.execute("PRAGMA schema_version").fetchone()[0])
                conn.execute(f"PRAGMA schema_version = {schema_version + 1}")
            conn.execute("PRAGMA writable_schema = OFF")
            return
        conn.execute(
            """
            UPDATE sqlite_master
            SET sql = REPLACE(sql, 'messages_old', 'messages')
            WHERE type = 'table'
              AND sql LIKE '%messages_old%'
            """
        )
        conn.execute("PRAGMA writable_schema = OFF")
        schema_version = int(conn.execute("PRAGMA schema_version").fetchone()[0])
        conn.execute(f"PRAGMA schema_version = {schema_version + 1}")

    def _ensure_phase1_schema(self, conn: sqlite3.Connection) -> None:
        self._backup_before_phase1_migration(conn)
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'ACTIVE'
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                state TEXT NOT NULL,
                state_machine_version TEXT NOT NULL,
                owner_message_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (owner_message_id) REFERENCES messages(id)
            );

            CREATE TABLE IF NOT EXISTS task_transitions (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                previous_state TEXT NOT NULL,
                next_state TEXT NOT NULL,
                actor TEXT NOT NULL,
                logical_role TEXT NOT NULL,
                created_at TEXT NOT NULL,
                reason TEXT NOT NULL,
                supporting_message_id INTEGER,
                run_id TEXT,
                artifacts_affected TEXT NOT NULL DEFAULT '[]',
                checks_performed TEXT NOT NULL DEFAULT '[]',
                unresolved_risks TEXT NOT NULL DEFAULT '[]',
                owner_approval_required INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (task_id) REFERENCES tasks(id),
                FOREIGN KEY (supporting_message_id) REFERENCES messages(id)
            );

            CREATE TABLE IF NOT EXISTS agent_runs (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                agent_key TEXT NOT NULL,
                logical_role TEXT NOT NULL,
                provider TEXT NOT NULL,
                prompt_hash TEXT,
                context_manifest TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                ok INTEGER NOT NULL DEFAULT 0,
                cancelled INTEGER NOT NULL DEFAULT 0,
                returncode INTEGER,
                duration_seconds REAL,
                error TEXT,
                raw_response TEXT,
                parsed_response TEXT,
                parse_errors TEXT NOT NULL DEFAULT '[]',
                recovery_state TEXT NOT NULL DEFAULT 'IN_PROGRESS',
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            );

            CREATE TABLE IF NOT EXISTS handoffs (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                from_run_id TEXT,
                from_role TEXT NOT NULL,
                to_role TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            );

            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                project_id TEXT,
                relative_path TEXT NOT NULL,
                artifact_type TEXT,
                media_type TEXT,
                authoring_role TEXT,
                created_by_run_id TEXT,
                current_revision TEXT,
                sha256 TEXT,
                size INTEGER,
                status TEXT NOT NULL DEFAULT 'DRAFT',
                validation_status TEXT NOT NULL DEFAULT 'UNKNOWN',
                last_modified_time TEXT,
                supersedes_artifact_id TEXT,
                deleted INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS artifact_revisions (
                id TEXT PRIMARY KEY,
                artifact_id TEXT NOT NULL,
                run_id TEXT,
                sha256 TEXT,
                size INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (artifact_id) REFERENCES artifacts(id)
            );

            CREATE TABLE IF NOT EXISTS findings (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                reviewer_run_id TEXT,
                severity TEXT NOT NULL,
                confidence TEXT NOT NULL,
                affected_artifact TEXT,
                location TEXT,
                evidence TEXT,
                description TEXT NOT NULL,
                impact TEXT,
                required_action TEXT,
                status TEXT NOT NULL,
                resolution TEXT,
                resolved_by_run_id TEXT,
                independent_recheck_status TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            );

            CREATE TABLE IF NOT EXISTS finding_events (
                id TEXT PRIMARY KEY,
                finding_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                detail TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (finding_id) REFERENCES findings(id)
            );

            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                actor TEXT NOT NULL,
                decision_type TEXT NOT NULL,
                detail TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                requested_by_run_id TEXT,
                requested_action TEXT NOT NULL,
                evidence TEXT,
                risks TEXT,
                owner_decision TEXT,
                decided_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS skill_usage (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                run_id TEXT,
                skill_id TEXT NOT NULL,
                role TEXT NOT NULL,
                usage_type TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS knowledge_usage (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                run_id TEXT,
                knowledge_id TEXT NOT NULL,
                role TEXT NOT NULL,
                usage_type TEXT NOT NULL,
                evidence TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS standard_usage (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                run_id TEXT,
                standard_id TEXT NOT NULL,
                role TEXT NOT NULL,
                usage_type TEXT NOT NULL,
                evidence TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reference_design_usage (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                run_id TEXT,
                reference_design_id TEXT NOT NULL,
                role TEXT NOT NULL,
                usage_type TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS tool_evidence (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                run_id TEXT,
                tool_name TEXT NOT NULL,
                command TEXT,
                evidence_path TEXT,
                result TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                event_type TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS routing_decisions (
                id TEXT PRIMARY KEY,
                message_id INTEGER,
                thread_id TEXT,
                participation_mode TEXT NOT NULL,
                explicit_recipients TEXT NOT NULL DEFAULT '[]',
                inferred_recipients TEXT NOT NULL DEFAULT '[]',
                selected_responders TEXT NOT NULL DEFAULT '[]',
                excluded_responders TEXT NOT NULL DEFAULT '{}',
                interruption_policy TEXT,
                reason TEXT NOT NULL,
                router_version TEXT NOT NULL,
                normalized_text TEXT NOT NULL DEFAULT '',
                detected_recipient_tokens TEXT NOT NULL DEFAULT '[]',
                continuation_owner_before TEXT NOT NULL DEFAULT '[]',
                continuation_owner_after TEXT NOT NULL DEFAULT '[]',
                fallback_used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS conversation_threads (
                id TEXT PRIMARY KEY,
                conversation_id INTEGER NOT NULL,
                active_addressee_agent_id TEXT,
                active_task_id TEXT,
                active_topic TEXT,
                last_user_message_id INTEGER,
                expected_next_actor TEXT,
                thread_status TEXT NOT NULL DEFAULT 'OPEN',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                FOREIGN KEY (last_user_message_id) REFERENCES messages(id) ON DELETE SET NULL
            );
            """
        )
        columns = {str(row["name"]) for row in conn.execute("PRAGMA table_info(routing_decisions)").fetchall()}
        for name, definition in (
            ("normalized_text", "TEXT NOT NULL DEFAULT ''"),
            ("detected_recipient_tokens", "TEXT NOT NULL DEFAULT '[]'"),
            ("continuation_owner_before", "TEXT NOT NULL DEFAULT '[]'"),
            ("continuation_owner_after", "TEXT NOT NULL DEFAULT '[]'"),
            ("fallback_used", "INTEGER NOT NULL DEFAULT 0"),
        ):
            if name not in columns:
                conn.execute(f"ALTER TABLE routing_decisions ADD COLUMN {name} {definition}")
        conn.execute(
            "INSERT OR REPLACE INTO schema_meta (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            ("phase1_schema_version", "1"),
        )

    def _ensure_thread_question_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS thread_questions (
                id TEXT PRIMARY KEY,
                conversation_id INTEGER NOT NULL,
                thread_id TEXT NOT NULL,
                question_message_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                assigned_agent_keys TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'OPEN',
                answer_message_id INTEGER,
                answered_by_agent_key TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(question_message_id),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                FOREIGN KEY (question_message_id) REFERENCES messages(id) ON DELETE CASCADE,
                FOREIGN KEY (answer_message_id) REFERENCES messages(id) ON DELETE SET NULL
            );
            """
        )
        conn.execute(
            "INSERT OR REPLACE INTO schema_meta (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            ("thread_question_schema_version", "1"),
        )

    def _ensure_management_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS role_profiles (
                role_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                description TEXT NOT NULL,
                responsibilities TEXT NOT NULL DEFAULT '[]',
                restrictions TEXT NOT NULL DEFAULT '[]',
                schema_version TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS agent_profiles (
                agent_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                description TEXT NOT NULL,
                lifecycle_state TEXT NOT NULL,
                provider_id TEXT NOT NULL,
                persona_id TEXT,
                avatar_path TEXT,
                aliases TEXT NOT NULL DEFAULT '[]',
                full_name TEXT NOT NULL DEFAULT '',
                preferred_name TEXT NOT NULL DEFAULT '',
                informal_name TEXT NOT NULL DEFAULT '',
                communication_profile TEXT NOT NULL DEFAULT '{}',
                schema_version TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS agent_role_assignments (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                role_id TEXT NOT NULL,
                assigned_by TEXT NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(agent_id, role_id),
                FOREIGN KEY (agent_id) REFERENCES agent_profiles(agent_id),
                FOREIGN KEY (role_id) REFERENCES role_profiles(role_id)
            );

            CREATE TABLE IF NOT EXISTS agent_permissions (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                permission_id TEXT NOT NULL,
                granted_by TEXT NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(agent_id, permission_id),
                FOREIGN KEY (agent_id) REFERENCES agent_profiles(agent_id)
            );

            CREATE TABLE IF NOT EXISTS agent_permission_denies (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                permission_id TEXT NOT NULL,
                denied_by TEXT NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(agent_id, permission_id),
                FOREIGN KEY (agent_id) REFERENCES agent_profiles(agent_id)
            );

            CREATE TABLE IF NOT EXISTS management_audit_events (
                id TEXT PRIMARY KEY,
                actor TEXT NOT NULL,
                object_type TEXT NOT NULL,
                object_id TEXT NOT NULL,
                action TEXT NOT NULL,
                previous_value TEXT,
                new_value TEXT,
                files_changed TEXT NOT NULL DEFAULT '[]',
                database_changes TEXT NOT NULL DEFAULT '[]',
                affected_employees TEXT NOT NULL DEFAULT '[]',
                reason TEXT,
                approval TEXT,
                rollback_status TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        columns = {str(row["name"]) for row in conn.execute("PRAGMA table_info(agent_profiles)").fetchall()}
        if "aliases" not in columns:
            conn.execute("ALTER TABLE agent_profiles ADD COLUMN aliases TEXT NOT NULL DEFAULT '[]'")
        for name, definition in {
            "full_name": "TEXT NOT NULL DEFAULT ''",
            "preferred_name": "TEXT NOT NULL DEFAULT ''",
            "informal_name": "TEXT NOT NULL DEFAULT ''",
            "communication_profile": "TEXT NOT NULL DEFAULT '{}'",
        }.items():
            if name not in columns:
                conn.execute(f"ALTER TABLE agent_profiles ADD COLUMN {name} {definition}")
        conn.execute(
            "INSERT OR REPLACE INTO schema_meta (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            ("management_schema_version", "1.0"),
        )

    def _ensure_provider_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS provider_definitions (
                provider_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                provider_family TEXT NOT NULL,
                adapter_id TEXT NOT NULL,
                supported_os TEXT NOT NULL DEFAULT '[]',
                installation_strategy TEXT NOT NULL,
                authentication_strategy TEXT NOT NULL,
                executable_names TEXT NOT NULL DEFAULT '[]',
                minimum_supported_version TEXT,
                recommended_version TEXT,
                setup_instructions TEXT,
                known_limitations TEXT NOT NULL DEFAULT '[]',
                required_capabilities TEXT NOT NULL DEFAULT '[]',
                integration_type TEXT NOT NULL DEFAULT 'CLI',
                support_status TEXT NOT NULL DEFAULT 'CATALOG_ONLY',
                official_url TEXT NOT NULL DEFAULT '',
                install_command TEXT NOT NULL DEFAULT '[]',
                auth_command TEXT NOT NULL DEFAULT '[]',
                update_command TEXT NOT NULL DEFAULT '[]',
                uninstall_command TEXT NOT NULL DEFAULT '[]',
                capability_matrix TEXT NOT NULL DEFAULT '{}',
                credential_kind TEXT NOT NULL DEFAULT 'NONE',
                catalog_class TEXT NOT NULL DEFAULT 'UNSUPPORTED',
                last_verified TEXT NOT NULL DEFAULT '',
                provider_schema_version TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS provider_installations (
                installation_id TEXT PRIMARY KEY,
                provider_id TEXT NOT NULL,
                executable_path TEXT,
                detected_version TEXT,
                installation_status TEXT NOT NULL,
                operating_system TEXT,
                evidence TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (provider_id) REFERENCES provider_definitions(provider_id)
            );

            CREATE TABLE IF NOT EXISTS provider_accounts (
                account_id TEXT PRIMARY KEY,
                provider_id TEXT NOT NULL,
                account_label TEXT,
                credential_reference_id TEXT,
                authentication_status TEXT NOT NULL,
                last_verified_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (provider_id) REFERENCES provider_definitions(provider_id)
            );

            CREATE TABLE IF NOT EXISTS provider_capabilities (
                capability_profile_id TEXT PRIMARY KEY,
                provider_id TEXT NOT NULL,
                capabilities TEXT NOT NULL DEFAULT '[]',
                capability_status TEXT NOT NULL,
                evidence TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (provider_id) REFERENCES provider_definitions(provider_id)
            );

            CREATE TABLE IF NOT EXISTS provider_health_checks (
                id TEXT PRIMARY KEY,
                provider_id TEXT NOT NULL,
                detected_version TEXT,
                installation_status TEXT NOT NULL,
                authentication_status TEXT NOT NULL,
                access_status TEXT NOT NULL,
                health_status TEXT NOT NULL,
                capability_status TEXT NOT NULL,
                account_label TEXT,
                diagnostic TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (provider_id) REFERENCES provider_definitions(provider_id)
            );

            CREATE TABLE IF NOT EXISTS provider_install_events (
                id TEXT PRIMARY KEY,
                provider_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS provider_auth_events (
                id TEXT PRIMARY KEY,
                provider_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS agent_provider_assignments (
                assignment_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                provider_id TEXT NOT NULL,
                installation_id TEXT,
                account_id TEXT,
                capability_profile_id TEXT,
                execution_mode TEXT NOT NULL DEFAULT 'default',
                priority INTEGER NOT NULL DEFAULT 0,
                fallback_provider_id TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(agent_id, provider_id),
                FOREIGN KEY (agent_id) REFERENCES agent_profiles(agent_id),
                FOREIGN KEY (provider_id) REFERENCES provider_definitions(provider_id)
            );

            CREATE TABLE IF NOT EXISTS provisioning_sessions (
                provisioning_session_id TEXT PRIMARY KEY,
                target_employee_draft TEXT NOT NULL DEFAULT '{}',
                selected_provider TEXT NOT NULL,
                current_step TEXT NOT NULL,
                completed_steps TEXT NOT NULL DEFAULT '[]',
                pending_user_action TEXT,
                failure_details TEXT,
                install_plan_hash TEXT,
                started_at TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                recoverable INTEGER NOT NULL DEFAULT 1,
                cancellation_status TEXT
            );

            CREATE TABLE IF NOT EXISTS provisioning_steps (
                id TEXT PRIMARY KEY,
                provisioning_session_id TEXT NOT NULL,
                step_name TEXT NOT NULL,
                status TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (provisioning_session_id) REFERENCES provisioning_sessions(provisioning_session_id)
            );
            """
        )
        provider_columns = {str(row["name"]) for row in conn.execute("PRAGMA table_info(provider_definitions)").fetchall()}
        for name, definition in {
            "integration_type": "TEXT NOT NULL DEFAULT 'CLI'",
            "support_status": "TEXT NOT NULL DEFAULT 'CATALOG_ONLY'",
            "official_url": "TEXT NOT NULL DEFAULT ''",
            "install_command": "TEXT NOT NULL DEFAULT '[]'",
            "auth_command": "TEXT NOT NULL DEFAULT '[]'",
            "update_command": "TEXT NOT NULL DEFAULT '[]'",
            "uninstall_command": "TEXT NOT NULL DEFAULT '[]'",
            "capability_matrix": "TEXT NOT NULL DEFAULT '{}'",
            "credential_kind": "TEXT NOT NULL DEFAULT 'NONE'",
            "catalog_class": "TEXT NOT NULL DEFAULT 'UNSUPPORTED'",
            "last_verified": "TEXT NOT NULL DEFAULT ''",
        }.items():
            if name not in provider_columns:
                conn.execute(f"ALTER TABLE provider_definitions ADD COLUMN {name} {definition}")
        conn.execute(
            "INSERT OR REPLACE INTO schema_meta (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            ("provider_schema_version", "1.0"),
        )

    def _backup_before_phase1_migration(self, conn: sqlite3.Connection) -> None:
        row = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'tasks'").fetchone()
        if row is not None:
            return
        backup_path = self.path.with_name(f"{self.path.stem}.before_phase1.sqlite3")
        if self.path.exists() and not backup_path.exists():
            shutil.copyfile(self.path, backup_path)

    def create_conversation(self, title: str = "Новый диалог") -> int:
        with self.connect() as conn:
            cur = conn.execute("INSERT INTO conversations (title) VALUES (?)", (title,))
            return int(cur.lastrowid)

    def ensure_single_conversation(self, title: str = "Командный чат") -> int:
        self.initialize()
        with self.connect() as conn:
            rows = conn.execute("SELECT id FROM conversations ORDER BY id ASC").fetchall()
            if not rows:
                cur = conn.execute("INSERT INTO conversations (title) VALUES (?)", (title,))
                return int(cur.lastrowid)

            primary_id = int(rows[0]["id"])
            if len(rows) > 1:
                self._backup_before_single_dialog_migration()
                extra_ids = [int(row["id"]) for row in rows[1:]]
                placeholders = ",".join("?" for _ in extra_ids)
                conn.execute(
                    f"UPDATE messages SET conversation_id = ? WHERE conversation_id IN ({placeholders})",
                    (primary_id, *extra_ids),
                )
                conn.execute(
                    f"DELETE FROM conversations WHERE id IN ({placeholders})",
                    tuple(extra_ids),
                )
                conn.execute(
                    "INSERT INTO app_events (event_type, detail) VALUES (?, ?)",
                    ("single_conversation_migration", f"merged={extra_ids}; primary={primary_id}"),
                )
            conn.execute(
                "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (title, primary_id),
            )
            return primary_id

    def _backup_before_single_dialog_migration(self) -> None:
        backup_path = self.path.with_name(f"{self.path.stem}.before_single_dialog.sqlite3")
        if self.path.exists() and not backup_path.exists():
            shutil.copyfile(self.path, backup_path)

    def ensure_organization_conversations(self) -> None:
        """Ensure every organization workspace owns a unique conversation.

        Early builds attached every workspace to the single legacy conversation.
        Keep the first workspace on that history and give every other workspace
        a clean conversation so messages cannot cross organization boundaries.
        """
        self.initialize()
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT workspace.organization_id, workspace.conversation_id, organizations.name
                FROM organization_workspaces AS workspace
                JOIN organizations ON organizations.id = workspace.organization_id
                ORDER BY workspace.created_at ASC, workspace.organization_id ASC
                """
            ).fetchall()
            used: set[int] = set()
            for row in rows:
                conversation_id = row["conversation_id"]
                valid = conversation_id is not None and conn.execute(
                    "SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)
                ).fetchone() is not None
                if valid and int(conversation_id) not in used:
                    used.add(int(conversation_id))
                    continue
                cursor = conn.execute(
                    "INSERT INTO conversations (title) VALUES (?)",
                    (str(row["name"]),),
                )
                new_conversation_id = int(cursor.lastrowid)
                conn.execute(
                    """
                    UPDATE organization_workspaces
                    SET conversation_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE organization_id = ?
                    """,
                    (new_conversation_id, str(row["organization_id"])),
                )
                used.add(new_conversation_id)

    def ensure_organization_conversation(self, organization_id: str, title: str | None = None) -> int:
        self.ensure_organization_conversations()
        with self.connect() as conn:
            workspace = conn.execute(
                "SELECT conversation_id FROM organization_workspaces WHERE organization_id = ?",
                (organization_id,),
            ).fetchone()
            if workspace is not None and workspace["conversation_id"] is not None:
                conversation_id = int(workspace["conversation_id"])
                if conn.execute("SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)).fetchone() is not None:
                    return conversation_id
            organization = conn.execute(
                "SELECT name FROM organizations WHERE id = ?", (organization_id,)
            ).fetchone()
            if organization is None:
                raise ValueError("unknown_organization")
            cursor = conn.execute(
                "INSERT INTO conversations (title) VALUES (?)",
                (title or str(organization["name"]),),
            )
            conversation_id = int(cursor.lastrowid)
            if workspace is None:
                workspace_id = f"OWS-{uuid.uuid4().hex[:12].upper()}"
                conn.execute(
                    """
                    INSERT INTO organization_workspaces
                        (id, organization_id, conversation_id, workspace_path, routing_config, status, is_active)
                    VALUES (?, ?, ?, '', '{}', 'READY_EMPTY', 0)
                    """,
                    (workspace_id, organization_id, conversation_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE organization_workspaces
                    SET conversation_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE organization_id = ?
                    """,
                    (conversation_id, organization_id),
                )
            return conversation_id

    def ensure_general_conversation(self, title: str = "Общий чат") -> int:
        """Return a conversation that is not owned by an organization workspace."""
        self.initialize()
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id FROM conversations
                WHERE id NOT IN (SELECT conversation_id FROM organization_workspaces WHERE conversation_id IS NOT NULL)
                ORDER BY id ASC LIMIT 1
                """
            ).fetchone()
            if row is not None:
                return int(row["id"])
            cursor = conn.execute("INSERT INTO conversations (title) VALUES (?)", (title,))
            return int(cursor.lastrowid)

    def list_conversations(self) -> list[Conversation]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC, id DESC"
            ).fetchall()
        return [Conversation(**dict(row)) for row in rows]

    def delete_conversation(self, conversation_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))

    def add_message(self, conversation_id: int, role: str, content: str, status: str = "ok") -> int:
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO messages (conversation_id, role, content, created_at, status) VALUES (?, ?, ?, ?, ?)",
                (conversation_id, role, content, datetime.now().isoformat(timespec="seconds"), status),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (conversation_id,),
            )
            return int(cur.lastrowid)

    def list_messages(self, conversation_id: int, limit: int | None = None) -> list[Message]:
        sql = (
            "SELECT id, conversation_id, role, content, created_at, status "
            "FROM messages WHERE conversation_id = ? ORDER BY id ASC"
        )
        params: tuple[object, ...] = (conversation_id,)
        if limit is not None:
            sql = (
                "SELECT * FROM ("
                "SELECT id, conversation_id, role, content, created_at, status "
                "FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?"
                ") ORDER BY id ASC"
            )
            params = (conversation_id, limit)
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [Message(**dict(row)) for row in rows]

    def list_all_messages(self, limit: int | None = None) -> list[Message]:
        sql = (
            "SELECT id, conversation_id, role, content, created_at, status "
            "FROM messages ORDER BY id ASC"
        )
        params: tuple[object, ...] = ()
        if limit is not None:
            sql = (
                "SELECT * FROM ("
                "SELECT id, conversation_id, role, content, created_at, status "
                "FROM messages ORDER BY id DESC LIMIT ?"
                ") ORDER BY id ASC"
            )
            params = (limit,)
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [Message(**dict(row)) for row in rows]

    def add_memory(self, content: str) -> int:
        with self.connect() as conn:
            cur = conn.execute("INSERT INTO user_memories (content) VALUES (?)", (content,))
            return int(cur.lastrowid)

    def list_memories(self) -> list[UserMemory]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT id, content, created_at FROM user_memories ORDER BY created_at DESC, id DESC"
            ).fetchall()
        return [UserMemory(**dict(row)) for row in rows]

    def delete_memory(self, memory_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM user_memories WHERE id = ?", (memory_id,))

    def log_event(self, event_type: str, detail: str | None = None) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO app_events (event_type, detail) VALUES (?, ?)",
                (event_type, detail),
            )

    def upsert_artifact(
        self,
        *,
        task_id: str | None,
        project_id: str | None,
        relative_path: str,
        artifact_type: str = "",
        media_type: str = "",
        authoring_role: str = "",
        created_by_run_id: str | None = None,
        sha256: str | None = None,
        size: int | None = None,
        status: str = "DRAFT",
        validation_status: str = "UNKNOWN",
        last_modified_time: str | None = None,
        deleted: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        with self.connect() as conn:
            existing = conn.execute(
                """
                SELECT * FROM artifacts
                WHERE relative_path = ?
                  AND COALESCE(task_id, '') = COALESCE(?, '')
                ORDER BY rowid DESC
                LIMIT 1
                """,
                (relative_path, task_id),
            ).fetchone()
            artifact_id = str(existing["id"]) if existing is not None else f"ART-{uuid.uuid4().hex[:12].upper()}"
            revision_id = None
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO artifacts (
                        id, task_id, project_id, relative_path, artifact_type, media_type,
                        authoring_role, created_by_run_id, current_revision, sha256, size,
                        status, validation_status, last_modified_time, deleted
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        artifact_id,
                        task_id,
                        project_id,
                        relative_path,
                        artifact_type,
                        media_type,
                        authoring_role,
                        created_by_run_id,
                        None,
                        sha256,
                        size,
                        status,
                        validation_status,
                        last_modified_time,
                        1 if deleted else 0,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE artifacts
                    SET project_id = COALESCE(?, project_id),
                        artifact_type = COALESCE(NULLIF(?, ''), artifact_type),
                        media_type = COALESCE(NULLIF(?, ''), media_type),
                        authoring_role = COALESCE(NULLIF(?, ''), authoring_role),
                        created_by_run_id = COALESCE(?, created_by_run_id),
                        sha256 = COALESCE(?, sha256),
                        size = COALESCE(?, size),
                        status = ?,
                        validation_status = ?,
                        last_modified_time = COALESCE(?, last_modified_time),
                        deleted = ?
                    WHERE id = ?
                    """,
                    (
                        project_id,
                        artifact_type,
                        media_type,
                        authoring_role,
                        created_by_run_id,
                        sha256,
                        size,
                        status,
                        validation_status,
                        last_modified_time,
                        1 if deleted else 0,
                        artifact_id,
                    ),
                )
            if sha256:
                revision_id = f"AREV-{uuid.uuid4().hex[:12].upper()}"
                conn.execute(
                    """
                    INSERT INTO artifact_revisions (id, artifact_id, run_id, sha256, size, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (revision_id, artifact_id, created_by_run_id, sha256, size, self._json(metadata or {})),
                )
                conn.execute(
                    "UPDATE artifacts SET current_revision = ? WHERE id = ?",
                    (revision_id, artifact_id),
                )
        return artifact_id

    def list_artifacts(self, task_id: str | None = None, status: str | None = None, limit: int = 200) -> list[sqlite3.Row]:
        clauses: list[str] = []
        params: list[object] = []
        if task_id:
            clauses.append("task_id = ?")
            params.append(task_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        sql = "SELECT * FROM artifacts"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY relative_path ASC, id ASC LIMIT ?"
        params.append(limit)
        with self.connect() as conn:
            return conn.execute(sql, tuple(params)).fetchall()

    def get_artifact(self, artifact_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()

    def upsert_artifact_payload(
        self,
        *,
        artifact_id: str,
        title: str,
        content: str,
        source_agent_id: str | None = None,
        source_message_id: int | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO artifact_payloads (artifact_id, title, content, source_agent_id, source_message_id)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(artifact_id) DO UPDATE SET
                    title = excluded.title,
                    content = excluded.content,
                    source_agent_id = excluded.source_agent_id,
                    source_message_id = excluded.source_message_id
                """,
                (artifact_id, title, content, source_agent_id, source_message_id),
            )

    def get_artifact_payload(self, artifact_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM artifact_payloads WHERE artifact_id = ?", (artifact_id,)).fetchone()

    def get_active_work_context(self, conversation_id: int) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM active_work_contexts WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()

    def upsert_active_work_context(self, *, conversation_id: int, values: dict[str, Any]) -> None:
        fields = {
            "thread_id": str(values.get("thread_id") or f"conversation-{conversation_id}"),
            "task_id": values.get("task_id"),
            "task_title": str(values.get("task_title") or ""),
            "task_goal": str(values.get("task_goal") or ""),
            "current_owner_agent_id": values.get("current_owner_agent_id"),
            "previous_owner_agent_id": values.get("previous_owner_agent_id"),
            "active_artifact_ids": self._json(values.get("active_artifact_ids") or []),
            "primary_artifact_id": values.get("primary_artifact_id"),
            "artifact_type": str(values.get("artifact_type") or ""),
            "source_agent_id": values.get("source_agent_id"),
            "current_operation": str(values.get("current_operation") or "UNKNOWN"),
            "expected_output_type": str(values.get("expected_output_type") or ""),
            "unresolved_questions": self._json(values.get("unresolved_questions") or []),
            "last_completed_action": str(values.get("last_completed_action") or ""),
            "last_user_intent": str(values.get("last_user_intent") or "UNKNOWN"),
            "handoff_state": str(values.get("handoff_state") or "NONE"),
            "status": str(values.get("status") or "CURRENT"),
        }
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO active_work_contexts (
                    conversation_id, thread_id, task_id, task_title, task_goal,
                    current_owner_agent_id, previous_owner_agent_id, active_artifact_ids,
                    primary_artifact_id, artifact_type, source_agent_id, current_operation,
                    expected_output_type, unresolved_questions, last_completed_action,
                    last_user_intent, handoff_state, status, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(conversation_id) DO UPDATE SET
                    thread_id=excluded.thread_id, task_id=excluded.task_id, task_title=excluded.task_title,
                    task_goal=excluded.task_goal, current_owner_agent_id=excluded.current_owner_agent_id,
                    previous_owner_agent_id=excluded.previous_owner_agent_id, active_artifact_ids=excluded.active_artifact_ids,
                    primary_artifact_id=excluded.primary_artifact_id, artifact_type=excluded.artifact_type,
                    source_agent_id=excluded.source_agent_id, current_operation=excluded.current_operation,
                    expected_output_type=excluded.expected_output_type, unresolved_questions=excluded.unresolved_questions,
                    last_completed_action=excluded.last_completed_action, last_user_intent=excluded.last_user_intent,
                    handoff_state=excluded.handoff_state, status=excluded.status, updated_at=CURRENT_TIMESTAMP
                """,
                (
                    conversation_id,
                    fields["thread_id"], fields["task_id"], fields["task_title"], fields["task_goal"],
                    fields["current_owner_agent_id"], fields["previous_owner_agent_id"], fields["active_artifact_ids"],
                    fields["primary_artifact_id"], fields["artifact_type"], fields["source_agent_id"], fields["current_operation"],
                    fields["expected_output_type"], fields["unresolved_questions"], fields["last_completed_action"],
                    fields["last_user_intent"], fields["handoff_state"], fields["status"],
                ),
            )

    def create_work_handoff(self, *, values: dict[str, Any]) -> str:
        handoff_id = f"HANDOFF-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO work_handoffs (
                    id, conversation_id, task_id, from_agent_id, to_agent_id, artifact_ids,
                    requested_operation, expected_output, expected_output_type, user_instruction, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    handoff_id, values["conversation_id"], values.get("task_id"), values.get("from_agent_id"),
                    values["to_agent_id"], self._json(values.get("artifact_ids") or []),
                    values.get("requested_operation") or "UNKNOWN", values.get("expected_output") or "",
                    values.get("expected_output_type") or "", values.get("user_instruction") or "", values.get("status") or "PENDING",
                ),
            )
        return handoff_id

    def list_work_handoffs(self, conversation_id: int, limit: int = 20) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM work_handoffs WHERE conversation_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
                (conversation_id, limit),
            ).fetchall()

    def update_work_handoff_status(self, handoff_id: str, status: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE work_handoffs SET status = ?, superseded_at = CASE WHEN ? = 'SUPERSEDED' THEN CURRENT_TIMESTAMP ELSE superseded_at END WHERE id = ?",
                (status, status, handoff_id),
            )

    def create_execution_contract(self, *, values: dict[str, Any]) -> str:
        contract_id = f"CONTRACT-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO execution_contracts (
                    id, conversation_id, task_id, run_id, agent_id, role, user_instruction, intent,
                    input_artifact_ids, required_operation, expected_output, expected_output_type,
                    allowed_tools, required_evidence, completion_criteria, forbidden_substitutions,
                    clarification_required, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    contract_id, values["conversation_id"], values.get("task_id"), values.get("run_id"),
                    values["agent_id"], values.get("role") or "", values.get("user_instruction") or "",
                    values.get("intent") or "UNKNOWN", self._json(values.get("input_artifact_ids") or []),
                    values.get("required_operation") or "UNKNOWN", values.get("expected_output") or "",
                    values.get("expected_output_type") or "", self._json(values.get("allowed_tools") or []),
                    self._json(values.get("required_evidence") or []), self._json(values.get("completion_criteria") or []),
                    self._json(values.get("forbidden_substitutions") or []), 1 if values.get("clarification_required") else 0,
                    values.get("status") or "ACTIVE",
                ),
            )
        return contract_id

    def get_execution_contract(self, contract_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM execution_contracts WHERE id = ?", (contract_id,)).fetchone()

    def upsert_artifact_finding_link(
        self,
        *,
        artifact_id: str,
        finding_id: str,
        match_type: str,
        confidence: str,
        actor: str = "system",
    ) -> str:
        with self.connect() as conn:
            existing = conn.execute(
                """
                SELECT id, status, match_type, confidence
                FROM artifact_finding_links
                WHERE artifact_id = ? AND finding_id = ?
                """,
                (artifact_id, finding_id),
            ).fetchone()
            if existing is None:
                link_id = f"AFL-{uuid.uuid4().hex[:12].upper()}"
                conn.execute(
                    """
                    INSERT INTO artifact_finding_links (
                        id, artifact_id, finding_id, match_type, confidence, status
                    )
                    VALUES (?, ?, ?, ?, ?, 'ACTIVE')
                    """,
                    (link_id, artifact_id, finding_id, match_type, confidence),
                )
                self._insert_artifact_finding_link_event(conn, link_id, "CREATED", actor, f"{match_type}; {confidence}")
                return link_id

            link_id = str(existing["id"])
            changed = (
                str(existing["status"]) != "ACTIVE"
                or str(existing["match_type"]) != match_type
                or str(existing["confidence"]) != confidence
            )
            conn.execute(
                """
                UPDATE artifact_finding_links
                SET match_type = ?, confidence = ?, status = 'ACTIVE', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (match_type, confidence, link_id),
            )
            if changed:
                self._insert_artifact_finding_link_event(conn, link_id, "UPDATED", actor, f"{match_type}; {confidence}")
            return link_id

    def list_artifact_finding_links(
        self,
        *,
        artifact_id: str | None = None,
        finding_id: str | None = None,
        status: str | None = "ACTIVE",
        limit: int = 500,
    ) -> list[sqlite3.Row]:
        clauses: list[str] = []
        params: list[object] = []
        if artifact_id:
            clauses.append("artifact_id = ?")
            params.append(artifact_id)
        if finding_id:
            clauses.append("finding_id = ?")
            params.append(finding_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        sql = "SELECT * FROM artifact_finding_links"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at ASC, id ASC LIMIT ?"
        params.append(limit)
        with self.connect() as conn:
            return conn.execute(sql, tuple(params)).fetchall()

    def list_artifact_finding_link_events(self, link_id: str | None = None, limit: int = 200) -> list[sqlite3.Row]:
        clauses: list[str] = []
        params: list[object] = []
        if link_id:
            clauses.append("link_id = ?")
            params.append(link_id)
        sql = "SELECT * FROM artifact_finding_link_events"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at DESC, rowid DESC LIMIT ?"
        params.append(limit)
        with self.connect() as conn:
            return conn.execute(sql, tuple(params)).fetchall()

    def _insert_artifact_finding_link_event(
        self,
        conn: sqlite3.Connection,
        link_id: str,
        event_type: str,
        actor: str,
        detail: str | None,
    ) -> str:
        event_id = f"AFLE-{uuid.uuid4().hex[:12].upper()}"
        conn.execute(
            """
            INSERT INTO artifact_finding_link_events (id, link_id, event_type, actor, detail)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event_id, link_id, event_type, actor, detail),
        )
        return event_id

    def create_finding(
        self,
        *,
        task_id: str,
        description: str,
        severity: str,
        confidence: str,
        reviewer_run_id: str | None = None,
        affected_artifact: str = "",
        location: str = "",
        evidence: dict[str, Any] | list[Any] | str | None = None,
        impact: str = "",
        required_action: str = "",
        status: str = "OPEN",
        standard_id: str | None = None,
        finding_type: str = "QA_FINDING",
        repeat_key: str = "",
        actor: str = "owner",
    ) -> str:
        finding_id = f"FIND-{uuid.uuid4().hex[:12].upper()}"
        evidence_text = evidence if isinstance(evidence, str) else self._json(evidence or {})
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO findings (
                    id, task_id, reviewer_run_id, severity, confidence, affected_artifact,
                    location, evidence, description, impact, required_action, status,
                    standard_id, finding_type, repeat_key
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    finding_id,
                    task_id,
                    reviewer_run_id,
                    severity,
                    confidence,
                    affected_artifact,
                    location,
                    evidence_text,
                    description,
                    impact,
                    required_action,
                    status,
                    standard_id,
                    finding_type,
                    repeat_key,
                ),
            )
            self._insert_finding_event(conn, finding_id, "CREATED", actor, f"{severity}; {status}")
        return finding_id

    def list_findings(self, status: str | None = None, task_id: str | None = None, limit: int = 200) -> list[sqlite3.Row]:
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if task_id:
            clauses.append("task_id = ?")
            params.append(task_id)
        sql = "SELECT * FROM findings"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY updated_at DESC, created_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self.connect() as conn:
            return conn.execute(sql, tuple(params)).fetchall()

    def update_finding_status(
        self,
        finding_id: str,
        status: str,
        *,
        actor: str = "owner",
        resolution: str = "",
        resolved_by_run_id: str | None = None,
        independent_recheck_status: str | None = None,
    ) -> None:
        with self.connect() as conn:
            current = conn.execute("SELECT status FROM findings WHERE id = ?", (finding_id,)).fetchone()
            if current is None:
                raise ValueError(f"Finding not found: {finding_id}")
            conn.execute(
                """
                UPDATE findings
                SET status = ?,
                    resolution = COALESCE(NULLIF(?, ''), resolution),
                    resolved_by_run_id = COALESCE(?, resolved_by_run_id),
                    independent_recheck_status = COALESCE(?, independent_recheck_status),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, resolution, resolved_by_run_id, independent_recheck_status, finding_id),
            )
            self._insert_finding_event(
                conn,
                finding_id,
                "STATUS_CHANGED",
                actor,
                f"{current['status']} -> {status}; {resolution}".strip("; "),
            )

    def list_finding_events(self, finding_id: str | None = None, limit: int = 100) -> list[sqlite3.Row]:
        sql = "SELECT * FROM finding_events"
        params: tuple[object, ...] = ()
        if finding_id:
            sql += " WHERE finding_id = ?"
            params = (finding_id,)
        sql += " ORDER BY created_at DESC, rowid DESC LIMIT ?"
        params = (*params, limit)
        with self.connect() as conn:
            return conn.execute(sql, params).fetchall()

    def _insert_finding_event(
        self,
        conn: sqlite3.Connection,
        finding_id: str,
        event_type: str,
        actor: str,
        detail: str | None,
    ) -> str:
        event_id = f"FEV-{uuid.uuid4().hex[:12].upper()}"
        conn.execute(
            """
            INSERT INTO finding_events (id, finding_id, event_type, actor, detail)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event_id, finding_id, event_type, actor, detail),
        )
        return event_id

    def create_skill_package(
        self,
        *,
        name: str,
        purpose: str = "",
        supported_roles: list[str] | None = None,
        prerequisites: str = "",
        source_material: list[str] | None = None,
        instructions: str = "",
        tools: list[str] | None = None,
        expected_inputs: str = "",
        expected_outputs: str = "",
        prohibited_actions: str = "",
        validation_checklist: list[str] | None = None,
        examples: list[str] | None = None,
        negative_examples: list[str] | None = None,
        qualification_tasks: list[str] | None = None,
        version: str = "0.1.0",
        status: str = "DRAFT",
        actor: str = "owner",
    ) -> str:
        skill_id = f"SKILL-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO skill_packages (
                    id, name, purpose, supported_roles, prerequisites, source_material,
                    instructions, tools, expected_inputs, expected_outputs, prohibited_actions,
                    validation_checklist, examples, negative_examples, qualification_tasks,
                    version, status, created_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    skill_id,
                    name,
                    purpose,
                    self._json(supported_roles or []),
                    prerequisites,
                    self._json(source_material or []),
                    instructions,
                    self._json(tools or []),
                    expected_inputs,
                    expected_outputs,
                    prohibited_actions,
                    self._json(validation_checklist or []),
                    self._json(examples or []),
                    self._json(negative_examples or []),
                    self._json(qualification_tasks or []),
                    version,
                    status,
                    actor,
                ),
            )
            self._insert_skill_package_event(conn, skill_id, "CREATED", actor, f"status={status}")
        return skill_id

    def list_skill_packages(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT * FROM skill_packages
                ORDER BY updated_at DESC, created_at DESC, name ASC
                """
            ).fetchall()

    def get_skill_package(self, skill_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM skill_packages WHERE id = ?", (skill_id,)).fetchone()

    def update_skill_package_status(self, skill_id: str, status: str, actor: str = "owner", reason: str = "") -> None:
        with self.connect() as conn:
            current = conn.execute("SELECT status FROM skill_packages WHERE id = ?", (skill_id,)).fetchone()
            if current is None:
                raise ValueError(f"Skill package not found: {skill_id}")
            conn.execute(
                "UPDATE skill_packages SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, skill_id),
            )
            self._insert_skill_package_event(
                conn,
                skill_id,
                "STATUS_CHANGED",
                actor,
                f"{current['status']} -> {status}; {reason}".strip("; "),
            )

    def assign_skill_to_agent(
        self,
        *,
        agent_id: str,
        skill_id: str,
        state: str = "ASSIGNED",
        actor: str = "owner",
        reason: str = "",
    ) -> str:
        assignment_id = f"ESKILL-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            if conn.execute("SELECT 1 FROM skill_packages WHERE id = ?", (skill_id,)).fetchone() is None:
                raise ValueError(f"Skill package not found: {skill_id}")
            existing = conn.execute(
                "SELECT id, state FROM employee_skill_assignments WHERE agent_id = ? AND skill_id = ?",
                (agent_id, skill_id),
            ).fetchone()
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO employee_skill_assignments (id, agent_id, skill_id, state, assigned_by, evidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (assignment_id, agent_id, skill_id, state, actor, self._json({"reason": reason})),
                )
                event_detail = f"{agent_id}: {state}; {reason}".strip("; ")
            else:
                assignment_id = str(existing["id"])
                conn.execute(
                    """
                    UPDATE employee_skill_assignments
                    SET state = ?, assigned_by = ?, evidence = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (state, actor, self._json({"reason": reason}), assignment_id),
                )
                event_detail = f"{agent_id}: {existing['state']} -> {state}; {reason}".strip("; ")
            self._insert_skill_package_event(conn, skill_id, "ASSIGNED_TO_EMPLOYEE", actor, event_detail)
        return assignment_id

    def list_employee_skill_assignments(self, agent_id: str | None = None) -> list[sqlite3.Row]:
        sql = (
            """
            SELECT esa.*, sp.name, sp.status AS skill_status, sp.purpose, sp.version
            FROM employee_skill_assignments esa
            JOIN skill_packages sp ON sp.id = esa.skill_id
            """
        )
        params: tuple[object, ...] = ()
        if agent_id:
            sql += " WHERE esa.agent_id = ?"
            params = (agent_id,)
        sql += " ORDER BY esa.updated_at DESC, sp.name ASC"
        with self.connect() as conn:
            return conn.execute(sql, params).fetchall()

    def list_skill_package_events(self, skill_id: str | None = None, limit: int = 100) -> list[sqlite3.Row]:
        sql = "SELECT * FROM skill_package_events"
        params: tuple[object, ...] = ()
        if skill_id:
            sql += " WHERE skill_id = ?"
            params = (skill_id,)
        sql += " ORDER BY created_at DESC, rowid DESC LIMIT ?"
        params = (*params, limit)
        with self.connect() as conn:
            return conn.execute(sql, params).fetchall()

    def _insert_skill_package_event(
        self,
        conn: sqlite3.Connection,
        skill_id: str,
        event_type: str,
        actor: str,
        detail: str | None,
    ) -> str:
        event_id = f"SKLEV-{uuid.uuid4().hex[:12].upper()}"
        conn.execute(
            """
            INSERT INTO skill_package_events (id, skill_id, event_type, actor, detail)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event_id, skill_id, event_type, actor, detail),
        )
        return event_id

    def create_knowledge_card(
        self,
        *,
        title: str,
        summary: str = "",
        content: str = "",
        source_type: str = "internal_note",
        source_title: str = "",
        source_uri: str = "",
        source_authority: str = "UNVERIFIED",
        source_hash: str = "",
        role_ids: list[str] | None = None,
        tags: list[str] | None = None,
        status: str = "DRAFT",
        version: str = "0.1.0",
        review_notes: str = "",
        actor: str = "owner",
    ) -> str:
        knowledge_id = f"KNOW-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO knowledge_cards (
                    id, title, summary, content, source_type, source_title, source_uri,
                    source_authority, source_hash, role_ids, tags, status, version,
                    review_notes, created_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    knowledge_id,
                    title,
                    summary,
                    content,
                    source_type,
                    source_title,
                    source_uri,
                    source_authority,
                    source_hash,
                    self._json(role_ids or []),
                    self._json(tags or []),
                    status,
                    version,
                    review_notes,
                    actor,
                ),
            )
            self._insert_knowledge_card_event(conn, knowledge_id, "CREATED", actor, f"status={status}")
        return knowledge_id

    def list_knowledge_cards(self, status: str | None = None) -> list[sqlite3.Row]:
        sql = "SELECT * FROM knowledge_cards"
        params: tuple[object, ...] = ()
        if status:
            sql += " WHERE status = ?"
            params = (status,)
        sql += " ORDER BY updated_at DESC, created_at DESC, title ASC"
        with self.connect() as conn:
            return conn.execute(sql, params).fetchall()

    def get_knowledge_card(self, knowledge_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM knowledge_cards WHERE id = ?", (knowledge_id,)).fetchone()

    def update_knowledge_card_status(self, knowledge_id: str, status: str, actor: str = "owner", reason: str = "") -> None:
        with self.connect() as conn:
            current = conn.execute("SELECT status FROM knowledge_cards WHERE id = ?", (knowledge_id,)).fetchone()
            if current is None:
                raise ValueError(f"Knowledge card not found: {knowledge_id}")
            conn.execute(
                "UPDATE knowledge_cards SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, knowledge_id),
            )
            self._insert_knowledge_card_event(
                conn,
                knowledge_id,
                "STATUS_CHANGED",
                actor,
                f"{current['status']} -> {status}; {reason}".strip("; "),
            )

    def list_knowledge_card_events(self, knowledge_id: str | None = None, limit: int = 100) -> list[sqlite3.Row]:
        sql = "SELECT * FROM knowledge_card_events"
        params: tuple[object, ...] = ()
        if knowledge_id:
            sql += " WHERE knowledge_id = ?"
            params = (knowledge_id,)
        sql += " ORDER BY created_at DESC, rowid DESC LIMIT ?"
        params = (*params, limit)
        with self.connect() as conn:
            return conn.execute(sql, params).fetchall()

    def record_knowledge_usage(
        self,
        *,
        knowledge_id: str,
        role: str,
        usage_type: str,
        task_id: str | None = None,
        run_id: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> str:
        usage_id = f"KUSE-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO knowledge_usage (id, task_id, run_id, knowledge_id, role, usage_type, evidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (usage_id, task_id, run_id, knowledge_id, role, usage_type, self._json(evidence or {})),
            )
        return usage_id

    def list_knowledge_usage(self, limit: int = 100) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT * FROM knowledge_usage
                ORDER BY created_at DESC, rowid DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def _insert_knowledge_card_event(
        self,
        conn: sqlite3.Connection,
        knowledge_id: str,
        event_type: str,
        actor: str,
        detail: str | None,
    ) -> str:
        event_id = f"KNEV-{uuid.uuid4().hex[:12].upper()}"
        conn.execute(
            """
            INSERT INTO knowledge_card_events (id, knowledge_id, event_type, actor, detail)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event_id, knowledge_id, event_type, actor, detail),
        )
        return event_id

    def create_standard_card(
        self,
        *,
        code: str,
        title: str,
        requirement: str = "",
        scope: str = "",
        source_title: str = "",
        source_uri: str = "",
        source_hash: str = "",
        authority: str = "INTERNAL",
        mandatory_level: str = "GUIDANCE",
        role_ids: list[str] | None = None,
        tags: list[str] | None = None,
        status: str = "DRAFT",
        version: str = "0.1.0",
        review_notes: str = "",
        actor: str = "owner",
    ) -> str:
        standard_id = f"STD-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO standard_cards (
                    id, code, title, requirement, scope, source_title, source_uri,
                    source_hash, authority, mandatory_level, role_ids, tags, status,
                    version, review_notes, created_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    standard_id,
                    code,
                    title,
                    requirement,
                    scope,
                    source_title,
                    source_uri,
                    source_hash,
                    authority,
                    mandatory_level,
                    self._json(role_ids or []),
                    self._json(tags or []),
                    status,
                    version,
                    review_notes,
                    actor,
                ),
            )
            self._insert_standard_card_event(conn, standard_id, "CREATED", actor, f"status={status}")
        return standard_id

    def list_standard_cards(self, status: str | None = None) -> list[sqlite3.Row]:
        sql = "SELECT * FROM standard_cards"
        params: tuple[object, ...] = ()
        if status:
            sql += " WHERE status = ?"
            params = (status,)
        sql += " ORDER BY updated_at DESC, created_at DESC, code ASC"
        with self.connect() as conn:
            return conn.execute(sql, params).fetchall()

    def update_standard_card_status(self, standard_id: str, status: str, actor: str = "owner", reason: str = "") -> None:
        with self.connect() as conn:
            current = conn.execute("SELECT status FROM standard_cards WHERE id = ?", (standard_id,)).fetchone()
            if current is None:
                raise ValueError(f"Standard card not found: {standard_id}")
            conn.execute(
                "UPDATE standard_cards SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, standard_id),
            )
            self._insert_standard_card_event(
                conn,
                standard_id,
                "STATUS_CHANGED",
                actor,
                f"{current['status']} -> {status}; {reason}".strip("; "),
            )

    def list_standard_card_events(self, standard_id: str | None = None, limit: int = 100) -> list[sqlite3.Row]:
        sql = "SELECT * FROM standard_card_events"
        params: tuple[object, ...] = ()
        if standard_id:
            sql += " WHERE standard_id = ?"
            params = (standard_id,)
        sql += " ORDER BY created_at DESC, rowid DESC LIMIT ?"
        params = (*params, limit)
        with self.connect() as conn:
            return conn.execute(sql, params).fetchall()

    def record_standard_usage(
        self,
        *,
        standard_id: str,
        role: str,
        usage_type: str,
        task_id: str | None = None,
        run_id: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> str:
        usage_id = f"SUSE-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO standard_usage (id, task_id, run_id, standard_id, role, usage_type, evidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (usage_id, task_id, run_id, standard_id, role, usage_type, self._json(evidence or {})),
            )
        return usage_id

    def list_standard_usage(self, limit: int = 100) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT * FROM standard_usage
                ORDER BY created_at DESC, rowid DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def _insert_standard_card_event(
        self,
        conn: sqlite3.Connection,
        standard_id: str,
        event_type: str,
        actor: str,
        detail: str | None,
    ) -> str:
        event_id = f"STDEV-{uuid.uuid4().hex[:12].upper()}"
        conn.execute(
            """
            INSERT INTO standard_card_events (id, standard_id, event_type, actor, detail)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event_id, standard_id, event_type, actor, detail),
        )
        return event_id

    def ensure_project(self, project_id: str, title: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO projects (id, title) VALUES (?, ?)
                ON CONFLICT(id) DO UPDATE SET title = excluded.title, updated_at = CURRENT_TIMESTAMP
                """,
                (project_id, title),
            )

    def create_task(
        self,
        project_id: str,
        title: str,
        owner_message_id: int | None,
        state_machine_version: str,
    ) -> str:
        task_id = f"TASK-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO tasks (id, project_id, title, state, state_machine_version, owner_message_id)
                VALUES (?, ?, ?, 'NEW', ?, ?)
                """,
                (task_id, project_id, title, state_machine_version, owner_message_id),
            )
        return task_id

    def get_task(self, task_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()

    def list_tasks(self, limit: int = 200) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT id, project_id, title, state, created_at, updated_at
                FROM tasks
                ORDER BY updated_at DESC, created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    def record_task_transition(
        self,
        *,
        task_id: str,
        previous_state: str,
        next_state: str,
        actor: str,
        logical_role: str,
        reason: str,
        supporting_message_id: int | None,
        run_id: str | None,
        artifacts_affected: list[str],
        checks_performed: list[str],
        unresolved_risks: list[str],
        owner_approval_required: bool,
        created_at: str,
    ) -> str:
        transition_id = f"TRANS-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO task_transitions (
                    id, task_id, previous_state, next_state, actor, logical_role, created_at, reason,
                    supporting_message_id, run_id, artifacts_affected, checks_performed,
                    unresolved_risks, owner_approval_required
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    transition_id,
                    task_id,
                    previous_state,
                    next_state,
                    actor,
                    logical_role,
                    created_at,
                    reason,
                    supporting_message_id,
                    run_id,
                    self._json(artifacts_affected),
                    self._json(checks_performed),
                    self._json(unresolved_risks),
                    1 if owner_approval_required else 0,
                ),
            )
            conn.execute(
                "UPDATE tasks SET state = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (next_state, task_id),
            )
        return transition_id

    def task_has_blocking_findings(self, task_id: str) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT 1 FROM findings
                WHERE task_id = ?
                  AND severity IN ('CRITICAL', 'HIGH')
                  AND status NOT IN ('CLOSED', 'RESOLVED', 'ACCEPTED_RISK', 'REJECTED', 'DEFERRED')
                LIMIT 1
                """,
                (task_id,),
            ).fetchone()
        return row is not None

    def create_agent_run(
        self,
        *,
        task_id: str,
        agent_id: str,
        agent_key: str,
        logical_role: str,
        provider: str,
        prompt_hash: str | None,
        started_at: str,
    ) -> str:
        run_id = f"RUN-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_runs (
                    id, task_id, agent_id, agent_key, logical_role, provider, prompt_hash, started_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, task_id, agent_id, agent_key, logical_role, provider, prompt_hash, started_at),
            )
        return run_id

    def update_agent_run_status(self, run_id: str, status: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE agent_runs SET status = ? WHERE id = ?",
                (status, run_id),
            )

    def finish_agent_run(
        self,
        *,
        run_id: str,
        ok: bool,
        cancelled: bool,
        returncode: int | None,
        duration_seconds: float,
        error: str | None,
        raw_response: str,
        parsed_response: dict[str, Any] | None,
        parse_errors: list[str],
        finished_at: str,
        timed_out: bool = False,
    ) -> None:
        recovery_state = "CANCELLED" if cancelled else "TIMED_OUT" if timed_out else "FINISHED" if ok else "FAILED"
        status = "CANCELLED" if cancelled else "TIMED_OUT" if timed_out else "COMPLETED" if ok else "FAILED"
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE agent_runs
                SET finished_at = ?, ok = ?, cancelled = ?, returncode = ?, duration_seconds = ?,
                    error = ?, raw_response = ?, parsed_response = ?, parse_errors = ?, recovery_state = ?, status = ?
                WHERE id = ?
                """,
                (
                    finished_at,
                    1 if ok else 0,
                    1 if cancelled else 0,
                    returncode,
                    duration_seconds,
                    error,
                    raw_response,
                    self._json(parsed_response) if parsed_response is not None else None,
                    self._json(parse_errors),
                    recovery_state,
                    status,
                    run_id,
                ),
            )

    def get_agent_run(self, run_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM agent_runs WHERE id = ?", (run_id,)).fetchone()

    def list_task_transitions(self, task_id: str) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM task_transitions WHERE task_id = ? ORDER BY created_at ASC, id ASC",
                (task_id,),
            ).fetchall()

    def audit_event(self, event_type: str, task_id: str | None, detail: dict[str, Any] | None = None) -> str:
        event_id = f"AUDIT-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO audit_events (id, task_id, event_type, detail) VALUES (?, ?, ?, ?)",
                (event_id, task_id, event_type, self._json(detail or {})),
            )
        return event_id

    def record_routing_decision(
        self,
        *,
        message_id: int | None,
        thread_id: str | None,
        participation_mode: str,
        explicit_recipients: list[str],
        inferred_recipients: list[str],
        selected_responders: list[str],
        excluded_responders: dict[str, str],
        interruption_policy: str | None,
        reason: str,
        router_version: str,
        normalized_text: str = "",
        detected_recipient_tokens: list[str] | None = None,
        continuation_owner_before: list[str] | None = None,
        continuation_owner_after: list[str] | None = None,
        fallback_used: bool = False,
    ) -> str:
        decision_id = f"ROUTE-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO routing_decisions (
                    id, message_id, thread_id, participation_mode, explicit_recipients,
                    inferred_recipients, selected_responders, excluded_responders,
                    interruption_policy, reason, router_version, normalized_text,
                    detected_recipient_tokens, continuation_owner_before,
                    continuation_owner_after, fallback_used
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_id,
                    message_id,
                    thread_id,
                    participation_mode,
                    self._json(explicit_recipients),
                    self._json(inferred_recipients),
                    self._json(selected_responders),
                    self._json(excluded_responders),
                    interruption_policy,
                    reason,
                    router_version,
                    normalized_text,
                    self._json(detected_recipient_tokens or []),
                    self._json(continuation_owner_before or []),
                    self._json(continuation_owner_after or []),
                    1 if fallback_used else 0,
                ),
            )
        return decision_id

    def list_routing_decisions(self, limit: int | None = None) -> list[sqlite3.Row]:
        sql = "SELECT * FROM routing_decisions ORDER BY created_at DESC, id DESC"
        params: tuple[object, ...] = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (limit,)
        with self.connect() as conn:
            return conn.execute(sql, params).fetchall()

    def upsert_conversation_thread(
        self,
        *,
        thread_id: str,
        conversation_id: int,
        active_addressee_agent_id: str | None,
        active_task_id: str | None,
        active_topic: str | None,
        last_user_message_id: int | None,
        expected_next_actor: str | None,
        thread_status: str = "OPEN",
    ) -> str:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO conversation_threads (
                    id, conversation_id, active_addressee_agent_id, active_task_id,
                    active_topic, last_user_message_id, expected_next_actor, thread_status, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    active_addressee_agent_id = excluded.active_addressee_agent_id,
                    active_task_id = excluded.active_task_id,
                    active_topic = excluded.active_topic,
                    last_user_message_id = excluded.last_user_message_id,
                    expected_next_actor = excluded.expected_next_actor,
                    thread_status = excluded.thread_status,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    thread_id,
                    conversation_id,
                    active_addressee_agent_id,
                    active_task_id,
                    active_topic,
                    last_user_message_id,
                    expected_next_actor,
                    thread_status,
                ),
            )
        return thread_id

    def get_conversation_thread(self, thread_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM conversation_threads WHERE id = ?", (thread_id,)).fetchone()

    def get_active_conversation_thread(self, conversation_id: int) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT * FROM conversation_threads
                WHERE conversation_id = ? AND thread_status = 'OPEN'
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """,
                (conversation_id,),
            ).fetchone()

    def list_conversation_threads(self, limit: int | None = None) -> list[sqlite3.Row]:
        sql = "SELECT * FROM conversation_threads ORDER BY updated_at DESC, id DESC"
        params: tuple[object, ...] = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (limit,)
        with self.connect() as conn:
            return conn.execute(sql, params).fetchall()

    def create_thread_question(
        self,
        *,
        conversation_id: int,
        thread_id: str,
        question_message_id: int,
        question_text: str,
        assigned_agent_keys: list[str],
    ) -> str:
        question_id = f"QUESTION-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id FROM thread_questions WHERE question_message_id = ?",
                (question_message_id,),
            ).fetchone()
            if row is not None:
                return str(row["id"])
            conn.execute(
                """
                INSERT INTO thread_questions (
                    id, conversation_id, thread_id, question_message_id, question_text,
                    assigned_agent_keys, status, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 'OPEN', CURRENT_TIMESTAMP)
                """,
                (
                    question_id,
                    conversation_id,
                    thread_id,
                    question_message_id,
                    question_text,
                    self._json(assigned_agent_keys),
                ),
            )
        return question_id

    def mark_thread_questions_answered(
        self,
        *,
        question_ids: list[str],
        answer_message_id: int,
        answered_by_agent_key: str,
    ) -> None:
        if not question_ids:
            return
        with self.connect() as conn:
            conn.executemany(
                """
                UPDATE thread_questions
                SET status = 'ANSWERED',
                    answer_message_id = ?,
                    answered_by_agent_key = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'OPEN'
                """,
                [(answer_message_id, answered_by_agent_key, question_id) for question_id in question_ids],
            )

    def update_thread_question_status(self, question_id: str, status: str) -> bool:
        allowed = {"OPEN", "ANSWERED", "ACCEPTED"}
        if status not in allowed:
            raise ValueError(f"Unsupported thread question status: {status}")
        with self.connect() as conn:
            cur = conn.execute(
                """
                UPDATE thread_questions
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, question_id),
            )
            return cur.rowcount > 0

    def list_thread_questions(
        self,
        *,
        conversation_id: int | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[sqlite3.Row]:
        clauses: list[str] = []
        params: list[object] = []
        if conversation_id is not None:
            clauses.append("conversation_id = ?")
            params.append(conversation_id)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        sql = "SELECT * FROM thread_questions"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at DESC, id DESC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        with self.connect() as conn:
            return conn.execute(sql, tuple(params)).fetchall()

    def upsert_role_profile(self, role: RoleProfile) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO role_profiles (
                    role_id, display_name, description, responsibilities, restrictions, schema_version
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(role_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    description = excluded.description,
                    responsibilities = excluded.responsibilities,
                    restrictions = excluded.restrictions,
                    schema_version = excluded.schema_version,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    role.role_id,
                    role.display_name,
                    role.description,
                    self._json(role.responsibilities),
                    self._json(role.restrictions),
                    role.schema_version,
                ),
            )

    def get_agent_profile(self, agent_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM agent_profiles WHERE agent_id = ?", (agent_id,)).fetchone()

    def list_agent_profiles(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM agent_profiles ORDER BY display_name ASC").fetchall()

    def list_role_profiles(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM role_profiles ORDER BY role_id ASC").fetchall()

    def list_agent_roles(self, agent_id: str) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT role_id FROM agent_role_assignments WHERE agent_id = ? ORDER BY role_id ASC",
                (agent_id,),
            ).fetchall()
        return [str(row["role_id"]) for row in rows]

    def list_agent_permissions(self, agent_id: str) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT permission_id FROM agent_permissions WHERE agent_id = ? ORDER BY permission_id ASC",
                (agent_id,),
            ).fetchall()
        return [str(row["permission_id"]) for row in rows]

    def list_agent_permission_denies(self, agent_id: str) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT permission_id FROM agent_permission_denies WHERE agent_id = ? ORDER BY permission_id ASC",
                (agent_id,),
            ).fetchall()
        return [str(row["permission_id"]) for row in rows]

    def create_agent_profile(self, profile: AgentProfile, actor: str, reason: str) -> None:
        with self.connect() as conn:
            self._insert_agent_profile(conn, profile)
            self._insert_management_audit(
                conn,
                actor=actor,
                object_type="agent_profile",
                object_id=profile.agent_id,
                action="create",
                previous_value=None,
                new_value=self._json(profile.__dict__),
                database_changes=["agent_profiles"],
                affected_employees=[profile.agent_id],
                reason=reason,
            )

    def create_agent_profile_with_assignments(
        self,
        profile: AgentProfile,
        role_ids: list[str],
        permissions: list[str],
        actor: str,
        reason: str,
    ) -> None:
        with self.connect() as conn:
            self._insert_agent_profile(conn, profile)
            for role_id in role_ids:
                self._assign_role_to_agent(conn, profile.agent_id, role_id, actor, reason)
            for permission in permissions:
                self._grant_agent_permission(conn, profile.agent_id, permission, actor, reason)
            self._insert_management_audit(
                conn,
                actor=actor,
                object_type="agent_profile",
                object_id=profile.agent_id,
                action="create_with_assignments",
                previous_value=None,
                new_value=self._json(
                    {
                        "profile": profile.__dict__,
                        "roles": role_ids,
                        "permissions": permissions,
                    }
                ),
                database_changes=["agent_profiles", "agent_role_assignments", "agent_permissions"],
                affected_employees=[profile.agent_id],
                reason=reason,
            )

    def update_agent_profile(
        self,
        agent_id: str,
        *,
        display_name: str,
        description: str,
        provider_id: str,
        persona_id: str | None,
        avatar_path: str | None,
        expected_updated_at: str | None,
        actor: str,
        reason: str,
        aliases: list[str] | tuple[str, ...] | None = None,
        full_name: str = "",
        preferred_name: str = "",
        informal_name: str = "",
        communication_profile: dict[str, object] | None = None,
    ) -> None:
        with self.connect() as conn:
            previous = conn.execute("SELECT * FROM agent_profiles WHERE agent_id = ?", (agent_id,)).fetchone()
            if previous is None:
                raise ValueError(f"Unknown agent profile: {agent_id}")
            stored_aliases = previous["aliases"] if aliases is None and "aliases" in previous.keys() else self._json(list(aliases or []))
            if expected_updated_at is not None and str(previous["updated_at"]) != expected_updated_at:
                raise RuntimeError("optimistic_lock_conflict")
            conn.execute(
                """
                UPDATE agent_profiles
                SET display_name = ?, description = ?, provider_id = ?, persona_id = ?, avatar_path = ?, aliases = ?,
                    full_name = ?, preferred_name = ?, informal_name = ?, communication_profile = ?, updated_at = CURRENT_TIMESTAMP
                WHERE agent_id = ?
                """,
                (
                    display_name, description, provider_id, persona_id, avatar_path, stored_aliases,
                    full_name or display_name, preferred_name, informal_name, self._json(communication_profile or {}), agent_id,
                ),
            )
            self._insert_management_audit(
                conn,
                actor=actor,
                object_type="agent_profile",
                object_id=agent_id,
                action="edit",
                previous_value=self._json(dict(previous)),
                new_value=self._json(
                    {
                        "display_name": display_name,
                        "description": description,
                        "provider_id": provider_id,
                        "persona_id": persona_id,
                        "avatar_path": avatar_path,
                        "aliases": json.loads(stored_aliases) if isinstance(stored_aliases, str) else list(stored_aliases),
                        "full_name": full_name or display_name,
                        "preferred_name": preferred_name,
                        "informal_name": informal_name,
                        "communication_profile": communication_profile or {},
                    }
                ),
                database_changes=["agent_profiles"],
                affected_employees=[agent_id],
                reason=reason,
            )

    def replace_agent_roles(self, agent_id: str, role_ids: list[str], actor: str, reason: str) -> None:
        with self.connect() as conn:
            previous = [
                str(row["role_id"])
                for row in conn.execute(
                    "SELECT role_id FROM agent_role_assignments WHERE agent_id = ? ORDER BY role_id ASC",
                    (agent_id,),
                ).fetchall()
            ]
            conn.execute("DELETE FROM agent_role_assignments WHERE agent_id = ?", (agent_id,))
            for role_id in role_ids:
                self._assign_role_to_agent(conn, agent_id, role_id, actor, reason)
            self._insert_management_audit(
                conn,
                actor=actor,
                object_type="agent_profile",
                object_id=agent_id,
                action="replace_roles",
                previous_value=self._json(previous),
                new_value=self._json(role_ids),
                database_changes=["agent_role_assignments"],
                affected_employees=[agent_id],
                reason=reason,
            )

    def replace_agent_permission_overrides(
        self,
        agent_id: str,
        grants: list[str],
        denies: list[str],
        actor: str,
        reason: str,
    ) -> None:
        with self.connect() as conn:
            previous = {
                "grants": [
                    str(row["permission_id"])
                    for row in conn.execute(
                        "SELECT permission_id FROM agent_permissions WHERE agent_id = ? ORDER BY permission_id ASC",
                        (agent_id,),
                    ).fetchall()
                ],
                "denies": [
                    str(row["permission_id"])
                    for row in conn.execute(
                        "SELECT permission_id FROM agent_permission_denies WHERE agent_id = ? ORDER BY permission_id ASC",
                        (agent_id,),
                    ).fetchall()
                ],
            }
            conn.execute("DELETE FROM agent_permissions WHERE agent_id = ?", (agent_id,))
            conn.execute("DELETE FROM agent_permission_denies WHERE agent_id = ?", (agent_id,))
            for permission in grants:
                self._grant_agent_permission(conn, agent_id, permission, actor, reason)
            for permission in denies:
                self._deny_agent_permission(conn, agent_id, permission, actor, reason)
            self._insert_management_audit(
                conn,
                actor=actor,
                object_type="agent_profile",
                object_id=agent_id,
                action="replace_permission_overrides",
                previous_value=self._json(previous),
                new_value=self._json({"grants": grants, "denies": denies}),
                database_changes=["agent_permissions", "agent_permission_denies"],
                affected_employees=[agent_id],
                reason=reason,
            )

    def assign_role_to_agent(self, agent_id: str, role_id: str, actor: str, reason: str) -> None:
        with self.connect() as conn:
            self._assign_role_to_agent(conn, agent_id, role_id, actor, reason)

    def grant_agent_permission(self, agent_id: str, permission_id: str, actor: str, reason: str) -> None:
        with self.connect() as conn:
            self._grant_agent_permission(conn, agent_id, permission_id, actor, reason)

    def set_agent_lifecycle(self, agent_id: str, lifecycle_state: str, actor: str, reason: str) -> None:
        with self.connect() as conn:
            previous = conn.execute("SELECT * FROM agent_profiles WHERE agent_id = ?", (agent_id,)).fetchone()
            if previous is None:
                raise ValueError(f"Unknown agent profile: {agent_id}")
            conn.execute(
                "UPDATE agent_profiles SET lifecycle_state = ?, updated_at = CURRENT_TIMESTAMP WHERE agent_id = ?",
                (lifecycle_state, agent_id),
            )

    def delete_agent_profile(
        self,
        agent_id: str,
        actor: str = "SYSTEM",
        reason: str = "Delete agent profile",
    ) -> None:
        with self.connect() as conn:
            previous = conn.execute("SELECT * FROM agent_profiles WHERE agent_id = ?", (agent_id,)).fetchone()
            if previous is None:
                raise ValueError(f"Unknown agent profile: {agent_id}")
            agent_key = agent_id.removeprefix("agent-")
            display_name = str(previous["display_name"] or "сотрудник").replace("|", " ").strip()
            deleted_role = f"deleted:{agent_key}:{display_name}"
            conn.execute(
                "UPDATE messages SET role = ? WHERE role = ?",
                (deleted_role, agent_key),
            )
            # Keep shared history, runs, artifacts and audit evidence. Remove
            # only identity-owned configuration and runtime state.
            cleanup_tables = (
                "agent_role_assignments",
                "agent_permissions",
                "agent_permission_denies",
                "agent_provider_assignments",
                "employee_skill_assignments",
            )
            database_changes = ["messages(author preserved)", *cleanup_tables, "agent_profiles"]
            for table in cleanup_tables:
                conn.execute(f'DELETE FROM "{table}" WHERE agent_id = ?', (agent_id,))
            conn.execute(
                "UPDATE active_work_contexts SET current_owner_agent_id = NULL, previous_owner_agent_id = NULL, source_agent_id = NULL WHERE current_owner_agent_id = ? OR previous_owner_agent_id = ? OR source_agent_id = ?",
                (agent_id, agent_id, agent_id),
            )
            conn.execute(
                "UPDATE artifact_payloads SET source_agent_id = NULL WHERE source_agent_id = ?",
                (agent_id,),
            )
            conn.execute(
                "UPDATE work_handoffs SET from_agent_id = NULL WHERE from_agent_id = ?",
                (agent_id,),
            )
            conn.execute("DELETE FROM agent_profiles WHERE agent_id = ?", (agent_id,))
            self._insert_management_audit(
                conn,
                actor=actor,
                object_type="agent_profile",
                object_id=agent_id,
                action="delete",
                previous_value=self._json(dict(previous)),
                new_value=None,
                database_changes=database_changes,
                affected_employees=[agent_id],
                reason=reason,
            )

    def list_management_audit_events(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM management_audit_events ORDER BY created_at ASC, id ASC"
            ).fetchall()

    # U1 universal platform primitives. These methods intentionally keep
    # domain payloads structured as JSON while the relational identities stay stable.
    def create_profession(self, values: dict[str, Any]) -> str:
        profession_id = values.get("id") or f"PROF-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO professions (id, name, description, responsibilities, typical_results,
                    required_capabilities, initial_skills, recommended_tools, knowledge_sources,
                    qualification_method, status, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (profession_id, values["name"], values.get("description", ""), self._json(values.get("responsibilities", [])),
                 self._json(values.get("typical_results", [])), self._json(values.get("required_capabilities", [])),
                 self._json(values.get("initial_skills", [])), self._json(values.get("recommended_tools", [])),
                 self._json(values.get("knowledge_sources", [])), values.get("qualification_method", ""),
                 values.get("status", "ACTIVE"), values.get("created_by", "owner")),
            )
        return str(profession_id)

    def list_professions(self, status: str | None = None) -> list[sqlite3.Row]:
        sql = "SELECT * FROM professions"
        params: tuple[Any, ...] = ()
        if status:
            sql += " WHERE status = ?"
            params = (status,)
        sql += " ORDER BY name ASC"
        with self.connect() as conn:
            return conn.execute(sql, params).fetchall()

    def get_profession(self, profession_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM professions WHERE id = ?", (profession_id,)).fetchone()

    def create_management_model(self, values: dict[str, Any]) -> str:
        model_id = values.get("id") or f"MGMT-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO management_models (
                    id, name, description, category, structure_type, decision_model,
                    responsibility_model, workflow_style, recommended_team_size,
                    advantages, limitations, source_rationale, version, status, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    model_id, values["name"], values.get("description", ""), values.get("category", ""),
                    values.get("structure_type", ""), values.get("decision_model", ""),
                    values.get("responsibility_model", ""), values.get("workflow_style", ""),
                    values.get("recommended_team_size", ""), self._json(values.get("advantages", [])),
                    self._json(values.get("limitations", [])), values.get("source_rationale", ""),
                    values.get("version", "1.0.0"), values.get("status", "ACTIVE"), values.get("created_by", "owner"),
                ),
            )
        return str(model_id)

    def list_management_models(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM management_models ORDER BY name ASC").fetchall()

    def get_management_model(self, model_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM management_models WHERE id = ?", (model_id,)).fetchone()

    def create_responsibility_model(self, values: dict[str, Any]) -> str:
        model_id = values.get("id") or f"RESP-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO responsibility_models (id, name, description, accountabilities, source_rationale, version, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (model_id, values["name"], values.get("description", ""), self._json(values.get("accountabilities", [])),
                 values.get("source_rationale", ""), values.get("version", "1.0.0"), values.get("status", "ACTIVE")),
            )
        return str(model_id)

    def list_responsibility_models(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM responsibility_models ORDER BY name ASC").fetchall()

    def create_organization_department(self, values: dict[str, Any]) -> str:
        department_id = values.get("id") or f"DEPT-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO organization_departments (id, organization_id, name, description) VALUES (?, ?, ?, ?)",
                (department_id, values["organization_id"], values["name"], values.get("description", "")),
            )
        return str(department_id)

    def list_organization_departments(self, organization_id: str) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM organization_departments WHERE organization_id = ? ORDER BY name ASC", (organization_id,)
            ).fetchall()

    def create_organization_workspace(self, values: dict[str, Any]) -> str:
        workspace_id = values.get("id") or f"OWS-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO organization_workspaces (
                    id, organization_id, conversation_id, workspace_path, routing_config, status, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(organization_id) DO UPDATE SET conversation_id=excluded.conversation_id,
                    workspace_path=excluded.workspace_path, routing_config=excluded.routing_config,
                    status=excluded.status, is_active=excluded.is_active, updated_at=CURRENT_TIMESTAMP
                """,
                (workspace_id, values["organization_id"], values.get("conversation_id"), values.get("workspace_path", ""),
                 self._json(values.get("routing_config", {})), values.get("status", "READY"), 1 if values.get("is_active") else 0),
            )
        return str(workspace_id)

    def set_active_organization(self, organization_id: str) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE organization_workspaces SET is_active = 0, updated_at = CURRENT_TIMESTAMP")
            conn.execute(
                "UPDATE organization_workspaces SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE organization_id = ?",
                (organization_id,),
            )

    def get_active_organization_id(self) -> str | None:
        with self.connect() as conn:
            row = conn.execute("SELECT organization_id FROM organization_workspaces WHERE is_active = 1 LIMIT 1").fetchone()
        return str(row["organization_id"]) if row is not None else None

    def get_organization_workspace(self, organization_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM organization_workspaces WHERE organization_id = ?", (organization_id,)).fetchone()

    def set_organization_status(self, organization_id: str, status: str) -> None:
        status = str(status).upper().strip()
        if status not in {"DRAFT", "ACTIVE", "PAUSED", "ARCHIVED"}:
            raise ValueError("unknown_organization_status")
        with self.connect() as conn:
            updated = conn.execute(
                "UPDATE organizations SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, organization_id),
            ).rowcount
            if not updated:
                raise ValueError("unknown_organization")
            if status != "ACTIVE":
                conn.execute(
                    "UPDATE organization_workspaces SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE organization_id = ?",
                    (organization_id,),
                )

    def delete_organization(self, organization_id: str) -> None:
        with self.connect() as conn:
            workspace = conn.execute(
                "SELECT conversation_id FROM organization_workspaces WHERE organization_id = ?",
                (organization_id,),
            ).fetchone()
            conversation_id = int(workspace["conversation_id"]) if workspace and workspace["conversation_id"] is not None else None
            # Permanent organization deletion also removes membership rows;
            # employee profiles remain reusable in other organizations.
            conn.execute("DELETE FROM organization_members WHERE organization_id = ?", (organization_id,))
            deleted = conn.execute("DELETE FROM organizations WHERE id = ?", (organization_id,)).rowcount
            if not deleted:
                raise ValueError("unknown_organization")
            if conversation_id is not None:
                still_referenced = conn.execute(
                    "SELECT 1 FROM organization_workspaces WHERE conversation_id = ?",
                    (conversation_id,),
                ).fetchone()
                if still_referenced is None:
                    conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))

    def create_organization_activation_event(self, organization_id: str, event_type: str, status: str, detail: dict[str, Any] | None = None) -> str:
        event_id = f"OAE-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO organization_activation_events (id, organization_id, event_type, status, detail) VALUES (?, ?, ?, ?, ?)",
                (event_id, organization_id, event_type, status, self._json(detail or {})),
            )
        return event_id

    def list_organization_activation_events(self, organization_id: str) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM organization_activation_events WHERE organization_id = ? ORDER BY created_at ASC, id ASC",
                (organization_id,),
            ).fetchall()

    def organization_dashboard(self, organization_id: str) -> dict[str, Any]:
        with self.connect() as conn:
            employees = conn.execute(
                "SELECT COUNT(*) AS count FROM organization_members WHERE organization_id = ? AND status = 'ACTIVE'",
                (organization_id,),
            ).fetchone()["count"]
            active_tasks = conn.execute(
                "SELECT COUNT(*) AS count FROM tasks WHERE state IN ('OPEN', 'IN_PROGRESS', 'BLOCKED')"
            ).fetchone()["count"]
            findings = conn.execute(
                "SELECT COUNT(*) AS count FROM findings WHERE status IN ('OPEN', 'PENDING_REVIEW')"
            ).fetchone()["count"]
            org = conn.execute("SELECT * FROM organizations WHERE id = ?", (organization_id,)).fetchone()
        return {
            "organization_id": organization_id,
            "name": str(org["name"]) if org else "",
            "status": str(org["status"]) if org else "UNKNOWN",
            "employees": int(employees or 0),
            "active_tasks": int(active_tasks or 0),
            "pending_review": int(findings or 0),
        }

    def create_organization(self, values: dict[str, Any]) -> str:
        organization_id = values.get("id") or f"ORG-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO organizations (
                    id, name, purpose, description, status, created_by,
                    management_model_id, domain_package, responsibility_model_id, active_template_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (organization_id, values["name"], values.get("purpose", ""), values.get("description", ""),
                 values.get("status", "ACTIVE"), values.get("created_by", "owner"), values.get("management_model_id"),
                 values.get("domain_package", ""), values.get("responsibility_model_id"), values.get("active_template_id")),
            )
        return str(organization_id)

    def list_organizations(self, status: str | None = None) -> list[sqlite3.Row]:
        sql = "SELECT * FROM organizations"
        params: tuple[Any, ...] = ()
        if status:
            sql += " WHERE status = ?"
            params = (status,)
        sql += " ORDER BY name ASC"
        with self.connect() as conn:
            return conn.execute(sql, params).fetchall()

    def create_workflow(self, values: dict[str, Any], steps: list[dict[str, Any]]) -> str:
        workflow_id = values.get("id") or f"WF-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO workflows (id, name, version, description, status, created_by) VALUES (?, ?, ?, ?, ?, ?)",
                (workflow_id, values["name"], values.get("version", "1.0.0"), values.get("description", ""), values.get("status", "ACTIVE"), values.get("created_by", "owner")),
            )
            for index, step in enumerate(steps, start=1):
                conn.execute(
                    """
                    INSERT INTO workflow_steps (id, workflow_id, step_order, responsibility, operation,
                        required_inputs, expected_outputs, review_requirement, approval_requirement, next_step)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (f"WFS-{uuid.uuid4().hex[:12].upper()}", workflow_id, int(step.get("step_order", index)),
                     step.get("responsibility", ""), step.get("operation", ""), self._json(step.get("required_inputs", [])),
                     self._json(step.get("expected_outputs", [])), step.get("review_requirement", ""),
                     step.get("approval_requirement", ""), step.get("next_step")),
                )
        return str(workflow_id)

    def list_workflows(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM workflows ORDER BY name ASC").fetchall()

    def create_organization_template(self, values: dict[str, Any]) -> str:
        template_id = values.get("id") or f"TEMPLATE-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO organization_templates (
                    id, name, purpose, recommended_team_size, roles, hierarchy, workflow_id,
                    handoff_rules, review_rules, approval_rules, permissions, required_capabilities,
                    recommended_tools, learning_roles, quality_controls, source_rationale, version,
                    limitations, status, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (template_id, values["name"], values.get("purpose", ""), values.get("recommended_team_size", ""),
                 self._json(values.get("roles", [])), self._json(values.get("hierarchy", [])), values.get("workflow_id"),
                 self._json(values.get("handoff_rules", [])), self._json(values.get("review_rules", [])),
                 self._json(values.get("approval_rules", [])), self._json(values.get("permissions", [])),
                 self._json(values.get("required_capabilities", [])), self._json(values.get("recommended_tools", [])),
                 self._json(values.get("learning_roles", [])), self._json(values.get("quality_controls", [])),
                 values.get("source_rationale", ""), values.get("version", "1.0.0"), self._json(values.get("limitations", [])),
                 values.get("status", "ACTIVE"), values.get("created_by", "owner")),
            )
            conn.execute(
                """
                UPDATE organization_templates
                SET management_model_id = ?, domain_package = ?, responsibility_model_id = ?,
                    team_size_variants = ?, catalog_category = ?, review_required = ?,
                    research_required = ?, learning_support = ?
                WHERE id = ?
                """,
                (values.get("management_model_id"), values.get("domain_package", ""), values.get("responsibility_model_id"),
                 self._json(values.get("team_size_variants", {})), values.get("catalog_category", "Other"),
                 1 if values.get("review_required") else 0, 1 if values.get("research_required") else 0,
                 1 if values.get("learning_support") else 0, template_id),
            )
        return str(template_id)

    def list_organization_templates(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM organization_templates ORDER BY name ASC").fetchall()

    def get_organization_template(self, template_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM organization_templates WHERE id = ?", (template_id,)).fetchone()

    def create_organization_member(self, values: dict[str, Any]) -> str:
        member_id = values.get("id") or f"MEMBER-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO organization_members (id, organization_id, department_id, agent_id, profession_id,
                    role_id, position, responsibilities, status, provider_id, assignment_mode,
                    provisioning_status, missing_reason, functional_manager_member_id, project_manager_member_id,
                    required_capabilities, permissions, recommended_tools)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (member_id, values["organization_id"], values.get("department_id"), values.get("agent_id"), values.get("profession_id"),
                 values.get("role_id"), values.get("position", ""), self._json(values.get("responsibilities", [])), values.get("status", "ACTIVE"),
                 values.get("provider_id", "UNAVAILABLE"), values.get("assignment_mode", "AUTO_CREATE"), values.get("provisioning_status", "UNASSIGNED"),
                 values.get("missing_reason", ""), values.get("functional_manager_member_id"), values.get("project_manager_member_id"),
                 self._json(values.get("required_capabilities", [])), self._json(values.get("permissions", [])), self._json(values.get("recommended_tools", []))),
            )
        return str(member_id)

    def list_organization_members(self, organization_id: str) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM organization_members WHERE organization_id = ? ORDER BY id ASC", (organization_id,)).fetchall()

    def list_organization_agent_ids(self, organization_id: str) -> set[str]:
        return {
            str(row["agent_id"])
            for row in self.list_organization_members(organization_id)
            if row["agent_id"] and str(row["status"] or "ACTIVE").upper() == "ACTIVE"
        }

    def upsert_agent_runtime_state(self, agent_id: str, values: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_runtime_states (agent_id, organization_id, current_task_id, current_operation,
                    current_plan, active_artifact_ids, open_finding_ids, checkpoint, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(agent_id) DO UPDATE SET organization_id=excluded.organization_id,
                    current_task_id=excluded.current_task_id, current_operation=excluded.current_operation,
                    current_plan=excluded.current_plan, active_artifact_ids=excluded.active_artifact_ids,
                    open_finding_ids=excluded.open_finding_ids, checkpoint=excluded.checkpoint,
                    status=excluded.status, updated_at=CURRENT_TIMESTAMP
                """,
                (agent_id, values.get("organization_id"), values.get("current_task_id"), values.get("current_operation", ""),
                 self._json(values.get("current_plan", [])), self._json(values.get("active_artifact_ids", [])),
                 self._json(values.get("open_finding_ids", [])), self._json(values.get("checkpoint", {})), values.get("status", "IDLE")),
            )

    def get_agent_runtime_state(self, agent_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM agent_runtime_states WHERE agent_id = ?", (agent_id,)).fetchone()

    def create_learning_source(self, values: dict[str, Any]) -> str:
        source_id = values.get("id") or f"SOURCE-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO learning_sources (id, title, source_type, location, added_by, trust_metadata, processed_state) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (source_id, values["title"], values["source_type"], values.get("location", ""), values.get("added_by", "owner"), self._json(values.get("trust_metadata", {})), values.get("processed_state", "NEW")),
            )
        return str(source_id)

    def list_learning_sources(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM learning_sources ORDER BY title ASC").fetchall()

    def create_experience_record(self, values: dict[str, Any]) -> str:
        record_id = values.get("id") or f"EXP-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO experience_records (
                    id, agent_id, employee_name, organization_id, task_id, run_id,
                    summary, skills_used, errors_found, corrections, lessons_learned,
                    knowledge_created, evidence, outcome
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    values.get("agent_id"),
                    values.get("employee_name", ""),
                    values.get("organization_id"),
                    values.get("task_id"),
                    values.get("run_id"),
                    values.get("summary", ""),
                    self._json(values.get("skills_used", [])),
                    self._json(values.get("errors_found", [])),
                    self._json(values.get("corrections", [])),
                    self._json(values.get("lessons_learned", [])),
                    self._json(values.get("knowledge_created", [])),
                    self._json(values.get("evidence", {})),
                    values.get("outcome", "RECORDED"),
                ),
            )
        return str(record_id)

    def list_experience_records(self, agent_id: str | None = None) -> list[sqlite3.Row]:
        with self.connect() as conn:
            if agent_id:
                return conn.execute(
                    "SELECT * FROM experience_records WHERE agent_id = ? ORDER BY created_at DESC, id DESC",
                    (agent_id,),
                ).fetchall()
            return conn.execute("SELECT * FROM experience_records ORDER BY created_at DESC, id DESC").fetchall()

    def create_learning_queue_item(self, values: dict[str, Any]) -> str:
        item_id = values.get("id") or f"LEARN-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO learning_queue (
                    id, agent_id, employee_name, competence, reason, source_id,
                    status, practice_task, evidence, created_by, skill_id,
                    coordinator_agent_id, qualification_criteria
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    values.get("agent_id"),
                    values.get("employee_name", ""),
                    values["competence"],
                    values["reason"],
                    values.get("source_id"),
                    values.get("status", "PROPOSED"),
                    values.get("practice_task", ""),
                    self._json(values.get("evidence", {})),
                    values.get("created_by", "SYSTEM"),
                    values.get("skill_id"),
                    values.get("coordinator_agent_id"),
                    self._json(values.get("qualification_criteria", [])),
                ),
            )
        return str(item_id)

    def list_learning_queue(self, agent_id: str | None = None) -> list[sqlite3.Row]:
        with self.connect() as conn:
            if agent_id:
                return conn.execute(
                    "SELECT * FROM learning_queue WHERE agent_id = ? ORDER BY created_at DESC, id DESC",
                    (agent_id,),
                ).fetchall()
            return conn.execute("SELECT * FROM learning_queue ORDER BY created_at DESC, id DESC").fetchall()

    def update_learning_queue_status(self, item_id: str, status: str, evidence: dict[str, Any] | None = None) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE learning_queue SET status = ?, evidence = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, self._json(evidence or {}), item_id),
            )

    def get_learning_queue_item(self, item_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM learning_queue WHERE id = ?", (item_id,)).fetchone()

    def update_learning_queue_item(self, item_id: str, values: dict[str, Any]) -> None:
        allowed = {
            "status", "practice_task", "evidence", "skill_id", "coordinator_agent_id",
            "qualification_criteria", "practice_run_id", "review_run_id", "completed_at",
        }
        updates = {key: value for key, value in values.items() if key in allowed}
        for key in ("evidence", "qualification_criteria"):
            if key in updates and not isinstance(updates[key], str):
                updates[key] = self._json(updates[key])
        if not updates:
            return
        assignments = ", ".join(f"{key} = ?" for key in updates)
        with self.connect() as conn:
            conn.execute(
                f"UPDATE learning_queue SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (*updates.values(), item_id),
            )

    def record_skill_usage(
        self,
        *,
        skill_id: str,
        role: str,
        usage_type: str,
        task_id: str | None = None,
        run_id: str | None = None,
    ) -> str:
        usage_id = f"SKILLUSE-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO skill_usage (id, task_id, run_id, skill_id, role, usage_type) VALUES (?, ?, ?, ?, ?, ?)",
                (usage_id, task_id, run_id, skill_id, role, usage_type),
            )
        return usage_id

    def create_project_plan(self, values: dict[str, Any]) -> str:
        plan_id = values.get("id") or f"PLAN-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO project_plans (
                    id, organization_id, project_id, director_agent_id, goal, status,
                    clarification_questions, missing_roles, owner_approval_required,
                    owner_message_id, summary, max_rework_attempts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan_id,
                    values["organization_id"],
                    values["project_id"],
                    values["director_agent_id"],
                    values["goal"],
                    values.get("status", "DRAFT"),
                    self._json(values.get("clarification_questions", [])),
                    self._json(values.get("missing_roles", [])),
                    1 if values.get("owner_approval_required") else 0,
                    values.get("owner_message_id"),
                    values.get("summary", ""),
                    int(values.get("max_rework_attempts", 2)),
                ),
            )
        return str(plan_id)

    def get_project_plan(self, plan_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM project_plans WHERE id = ?", (plan_id,)).fetchone()

    def update_project_plan(self, plan_id: str, values: dict[str, Any]) -> None:
        allowed = {"status", "summary", "completed_at", "owner_approval_required", "max_rework_attempts"}
        updates = {key: value for key, value in values.items() if key in allowed}
        if not updates:
            return
        assignments = ", ".join(f"{key} = ?" for key in updates)
        with self.connect() as conn:
            conn.execute(
                f"UPDATE project_plans SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (*updates.values(), plan_id),
            )

    def list_project_plans(self, organization_id: str | None = None) -> list[sqlite3.Row]:
        with self.connect() as conn:
            if organization_id:
                return conn.execute(
                    "SELECT * FROM project_plans WHERE organization_id = ? ORDER BY created_at DESC, id DESC",
                    (organization_id,),
                ).fetchall()
            return conn.execute("SELECT * FROM project_plans ORDER BY created_at DESC, id DESC").fetchall()

    def create_work_assignment(self, values: dict[str, Any]) -> str:
        assignment_id = values.get("id") or f"ASSIGN-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO work_assignments (
                    id, plan_id, task_id, agent_id, role_id, position, sequence_no,
                    review_required, acceptance_criteria, status, assignment_type,
                    responsibility, depends_on_assignment_id, reviewed_assignment_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    assignment_id,
                    values["plan_id"],
                    values["task_id"],
                    values.get("agent_id"),
                    values.get("role_id"),
                    values.get("position", ""),
                    int(values.get("sequence_no", 0)),
                    1 if values.get("review_required") else 0,
                    self._json(values.get("acceptance_criteria", [])),
                    values.get("status", "ASSIGNED"),
                    values.get("assignment_type", "EXECUTION"),
                    values.get("responsibility", "RESPONSIBLE"),
                    values.get("depends_on_assignment_id"),
                    values.get("reviewed_assignment_id"),
                ),
            )
        return str(assignment_id)

    def get_work_assignment(self, assignment_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM work_assignments WHERE id = ?", (assignment_id,)).fetchone()

    def update_work_assignment(self, assignment_id: str, values: dict[str, Any]) -> None:
        allowed = {
            "status", "attempt_no", "result_run_id", "result_message_id", "result_summary",
            "evidence", "review_decision", "failure_reason", "started_at", "completed_at",
        }
        updates = {key: value for key, value in values.items() if key in allowed}
        if "evidence" in updates and not isinstance(updates["evidence"], str):
            updates["evidence"] = self._json(updates["evidence"])
        if not updates:
            return
        assignments = ", ".join(f"{key} = ?" for key in updates)
        with self.connect() as conn:
            conn.execute(
                f"UPDATE work_assignments SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (*updates.values(), assignment_id),
            )

    def list_work_assignments(self, plan_id: str) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM work_assignments WHERE plan_id = ? ORDER BY sequence_no ASC, id ASC",
                (plan_id,),
            ).fetchall()

    def record_director_workflow_event(
        self,
        plan_id: str,
        event_type: str,
        *,
        assignment_id: str | None = None,
        actor_agent_id: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> str:
        event_id = f"DIREVENT-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO director_workflow_events
                    (id, plan_id, assignment_id, event_type, actor_agent_id, detail)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event_id, plan_id, assignment_id, event_type, actor_agent_id, self._json(detail or {})),
            )
        return event_id

    def list_director_workflow_events(self, plan_id: str) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM director_workflow_events WHERE plan_id = ? ORDER BY created_at ASC, id ASC",
                (plan_id,),
            ).fetchall()

    def upsert_provider_definition(self, profile: ProviderProfile) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO provider_definitions (
                    provider_id, display_name, provider_family, adapter_id, supported_os,
                    installation_strategy, authentication_strategy, executable_names,
                    minimum_supported_version, recommended_version, setup_instructions,
                    known_limitations, required_capabilities, integration_type, support_status,
                    official_url, install_command, auth_command, update_command, uninstall_command,
                    capability_matrix, credential_kind, catalog_class, last_verified, provider_schema_version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    provider_family = excluded.provider_family,
                    adapter_id = excluded.adapter_id,
                    supported_os = excluded.supported_os,
                    installation_strategy = excluded.installation_strategy,
                    authentication_strategy = excluded.authentication_strategy,
                    executable_names = excluded.executable_names,
                    minimum_supported_version = excluded.minimum_supported_version,
                    recommended_version = excluded.recommended_version,
                    setup_instructions = excluded.setup_instructions,
                    known_limitations = excluded.known_limitations,
                    required_capabilities = excluded.required_capabilities,
                    integration_type = excluded.integration_type,
                    support_status = excluded.support_status,
                    official_url = excluded.official_url,
                    install_command = excluded.install_command,
                    auth_command = excluded.auth_command,
                    update_command = excluded.update_command,
                    uninstall_command = excluded.uninstall_command,
                    capability_matrix = excluded.capability_matrix,
                    credential_kind = excluded.credential_kind,
                    catalog_class = excluded.catalog_class,
                    last_verified = excluded.last_verified,
                    provider_schema_version = excluded.provider_schema_version,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    profile.provider_id,
                    profile.display_name,
                    profile.provider_family,
                    profile.adapter_id,
                    self._json(profile.supported_os),
                    profile.installation_strategy,
                    profile.authentication_strategy,
                    self._json(profile.executable_names),
                    profile.minimum_supported_version,
                    profile.recommended_version,
                    profile.setup_instructions,
                    self._json(profile.known_limitations),
                    self._json(profile.required_capabilities),
                    profile.integration_type,
                    profile.support_status,
                    profile.official_url,
                    self._json(profile.install_command),
                    self._json(profile.auth_command),
                    self._json(profile.update_command),
                    self._json(profile.uninstall_command),
                    self._json(profile.capability_matrix),
                    profile.credential_kind,
                    profile.catalog_class,
                    profile.last_verified,
                    profile.provider_schema_version,
                ),
            )

    def list_provider_definitions(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM provider_definitions ORDER BY provider_id ASC").fetchall()

    def record_provider_health_check(self, health: ProviderHealth) -> str:
        check_id = f"PHC-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO provider_health_checks (
                    id, provider_id, detected_version, installation_status, authentication_status,
                    access_status, health_status, capability_status, account_label, diagnostic
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    check_id,
                    health.provider_id,
                    health.detected_version,
                    health.installation_status,
                    health.authentication_status,
                    health.access_status,
                    health.health_status,
                    health.capability_status,
                    health.account_label,
                    self._redact_secrets(health.diagnostic),
                ),
            )
            self._insert_management_audit(
                conn,
                actor="SYSTEM",
                object_type="provider",
                object_id=health.provider_id,
                action="PROVIDER_ACCESS_CHECKED",
                previous_value=None,
                new_value=self._json(
                    {
                        "installation_status": health.installation_status,
                        "authentication_status": health.authentication_status,
                        "access_status": health.access_status,
                        "health_status": health.health_status,
                        "capability_status": health.capability_status,
                    }
                ),
                database_changes=["provider_health_checks"],
                affected_employees=[],
                reason="lightweight provider health check",
            )
        return check_id

    def get_latest_provider_health(self, provider_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT * FROM provider_health_checks
                WHERE provider_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (provider_id,),
            ).fetchone()

    def record_provider_capabilities(self, provider_id: str, capabilities: list[str], status: str, evidence: dict[str, Any]) -> str:
        profile_id = f"PCAP-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO provider_capabilities (capability_profile_id, provider_id, capabilities, capability_status, evidence)
                VALUES (?, ?, ?, ?, ?)
                """,
                (profile_id, provider_id, self._json(sorted(set(capabilities))), status, self._json(evidence)),
            )
        return profile_id

    def get_latest_provider_capabilities(self, provider_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT * FROM provider_capabilities
                WHERE provider_id = ?
                ORDER BY created_at DESC, capability_profile_id DESC LIMIT 1
                """,
                (provider_id,),
            ).fetchone()

    def upsert_agent_provider_assignment(self, agent_id: str, provider_id: str, status: str) -> str:
        assignment_id = f"APA-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_provider_assignments (assignment_id, agent_id, provider_id, status)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(agent_id, provider_id) DO UPDATE SET
                    status = excluded.status,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (assignment_id, agent_id, provider_id, status),
            )
        return assignment_id

    def list_agent_provider_assignments(self, agent_id: str | None = None) -> list[sqlite3.Row]:
        with self.connect() as conn:
            if agent_id is None:
                return conn.execute("SELECT * FROM agent_provider_assignments ORDER BY agent_id ASC").fetchall()
            return conn.execute(
                "SELECT * FROM agent_provider_assignments WHERE agent_id = ? ORDER BY priority ASC",
                (agent_id,),
            ).fetchall()

    def create_provisioning_session(
        self,
        *,
        target_employee_draft: dict[str, Any],
        provider_id: str,
        current_step: str,
        install_plan_hash: str | None,
        recoverable: bool,
        started_at: str,
    ) -> str:
        session_id = f"PROV-{uuid.uuid4().hex[:12].upper()}"
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO provisioning_sessions (
                    provisioning_session_id, target_employee_draft, selected_provider,
                    current_step, install_plan_hash, started_at, recoverable
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    self._json(target_employee_draft),
                    provider_id,
                    current_step,
                    install_plan_hash,
                    started_at,
                    1 if recoverable else 0,
                ),
            )
        return session_id

    def _insert_agent_profile(self, conn: sqlite3.Connection, profile: AgentProfile) -> None:
        conn.execute(
            """
            INSERT INTO agent_profiles (
                agent_id, display_name, description, lifecycle_state, provider_id,
                persona_id, avatar_path, aliases, full_name, preferred_name, informal_name,
                communication_profile, schema_version
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile.agent_id,
                profile.display_name,
                profile.description,
                profile.lifecycle_state,
                profile.provider_id,
                profile.persona_id,
                profile.avatar_path,
                self._json(list(profile.aliases)),
                profile.full_name or profile.display_name,
                profile.preferred_name,
                profile.informal_name,
                self._json(profile.communication_profile),
                profile.schema_version,
            ),
        )

    def _assign_role_to_agent(
        self,
        conn: sqlite3.Connection,
        agent_id: str,
        role_id: str,
        actor: str,
        reason: str,
    ) -> None:
        assignment_id = f"AROLE-{uuid.uuid4().hex[:12].upper()}"
        conn.execute(
            """
            INSERT OR IGNORE INTO agent_role_assignments (id, agent_id, role_id, assigned_by, reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            (assignment_id, agent_id, role_id, actor, reason),
        )

    def _grant_agent_permission(
        self,
        conn: sqlite3.Connection,
        agent_id: str,
        permission_id: str,
        actor: str,
        reason: str,
    ) -> None:
        permission_row_id = f"APERM-{uuid.uuid4().hex[:12].upper()}"
        conn.execute(
            """
            INSERT OR IGNORE INTO agent_permissions (id, agent_id, permission_id, granted_by, reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            (permission_row_id, agent_id, permission_id, actor, reason),
        )

    def _deny_agent_permission(
        self,
        conn: sqlite3.Connection,
        agent_id: str,
        permission_id: str,
        actor: str,
        reason: str,
    ) -> None:
        permission_row_id = f"ADENY-{uuid.uuid4().hex[:12].upper()}"
        conn.execute(
            """
            INSERT OR IGNORE INTO agent_permission_denies (id, agent_id, permission_id, denied_by, reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            (permission_row_id, agent_id, permission_id, actor, reason),
        )

    def _insert_management_audit(
        self,
        conn: sqlite3.Connection,
        *,
        actor: str,
        object_type: str,
        object_id: str,
        action: str,
        previous_value: str | None,
        new_value: str | None,
        database_changes: list[str],
        affected_employees: list[str],
        reason: str,
        files_changed: list[str] | None = None,
        approval: str | None = None,
        rollback_status: str | None = None,
    ) -> str:
        event_id = f"MGMT-{uuid.uuid4().hex[:12].upper()}"
        conn.execute(
            """
            INSERT INTO management_audit_events (
                id, actor, object_type, object_id, action, previous_value, new_value,
                files_changed, database_changes, affected_employees, reason, approval, rollback_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                actor,
                object_type,
                object_id,
                action,
                previous_value,
                new_value,
                self._json(files_changed or []),
                self._json(database_changes),
                self._json(affected_employees),
                reason,
                approval,
                rollback_status,
            ),
        )
        return event_id

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def loads(value: str | None, default: Any) -> Any:
        if not value:
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default

    @staticmethod
    def _redact_secrets(value: str | None) -> str:
        if not value:
            return ""
        text = str(value)
        for marker in ("api_key", "token", "secret", "authorization", "GEMINI_API_KEY"):
            text = text.replace(marker, "[REDACTED]")
        return text
