from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .database import Database


class AdminAccessError(PermissionError):
    """Raised when a non-owner/non-admin reaches the owner console."""


class AdminCenterService:
    """Owner-console read models and audited administrative mutations.

    The service deliberately composes existing Core tables and services. It
    never fabricates product counts and never returns credentials.
    """

    ADMIN_ROLES = {"owner", "admin", "organization_owner", "organization_admin"}

    def __init__(self, database: Database, *, settings: dict[str, Any], management: Any, providers: Any, health: Any) -> None:
        self.database = database
        self.settings = settings
        self.management = management
        self.providers = providers
        self.health = health

    @classmethod
    def authorize(cls, role: str | None, *, require_explicit: bool = False) -> str:
        normalized = str(role or ("" if require_explicit else "owner")).strip().lower()
        if normalized not in cls.ADMIN_ROLES:
            raise AdminAccessError("admin_access_required")
        return normalized

    def touch_user(self, user_id: str, *, display_name: str, role: str, organization_id: str | None, language: str) -> None:
        self.database.upsert_admin_user({
            "user_id": user_id,
            "display_name": display_name,
            "role": role,
            "organization_id": organization_id,
            "language": language,
        })

    def dashboard(self) -> dict[str, Any]:
        with self.database.connect() as conn:
            counts = {
                "users": int(conn.execute("SELECT COUNT(*) FROM admin_users").fetchone()[0]),
                "visits": int(conn.execute("SELECT COUNT(*) FROM product_telemetry_events WHERE event_type = 'visit'").fetchone()[0]),
                "registrations": int(conn.execute("SELECT COUNT(*) FROM product_telemetry_events WHERE event_type = 'registration'").fetchone()[0]),
                "sessions": int(conn.execute("SELECT COUNT(*) FROM product_telemetry_events WHERE event_type = 'session_started'").fetchone()[0]),
                "goals": int(conn.execute("SELECT COUNT(*) FROM project_plans").fetchone()[0]),
                "artifacts": int(conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]),
                "evidence": int(conn.execute("SELECT COUNT(*) FROM tool_evidence").fetchone()[0]),
                "errors": int(conn.execute("SELECT COUNT(*) FROM app_events WHERE event_type LIKE '%error%' OR event_type LIKE '%failure%'").fetchone()[0]),
            }
            events = conn.execute(
                "SELECT event_type, COUNT(*) AS total FROM product_telemetry_events GROUP BY event_type ORDER BY total DESC"
            ).fetchall()
        provider_rows = self.providers.profiles()
        provider_health = []
        for profile in provider_rows:
            current = self.health.latest_health(profile.provider_id)
            provider_health.append({
                "name": profile.display_name,
                "state": current.health_status if current else "UNKNOWN",
                "configured": bool(self.settings.get("active_provider_id") == profile.provider_id),
            })
        return {
            "counts": counts,
            "activation": self._activation_funnel(),
            "event_types": [{"name": str(row["event_type"]), "count": int(row["total"])} for row in events],
            "providers": provider_health,
            "source": "database",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _activation_funnel(self) -> list[dict[str, Any]]:
        order = ["visit", "registration", "iris_opened", "constellation_opened", "goal_created", "goal_completed"]
        with self.database.connect() as conn:
            rows = conn.execute(
                "SELECT event_type, COUNT(*) AS total FROM product_telemetry_events WHERE event_type IN (%s) GROUP BY event_type"
                % ",".join("?" for _ in order), order,
            ).fetchall()
        values = {str(row["event_type"]): int(row["total"]) for row in rows}
        return [{"stage": stage, "count": values.get(stage, 0)} for stage in order]

    def provider_read_model(self) -> list[dict[str, Any]]:
        result = []
        for profile in self.providers.profiles():
            current = self.health.latest_health(profile.provider_id)
            result.append({
                "name": profile.display_name,
                "family": profile.provider_family,
                "support": profile.support_status,
                "health": current.health_status if current else "UNKNOWN",
                "authentication": current.authentication_status if current else "NOT_CHECKED",
                "capabilities": list(profile.capability_matrix),
                "active": self.settings.get("active_provider_id") == profile.provider_id,
                "credential_saved": bool(self.settings.get("active_provider_id") == profile.provider_id),
            })
        return result

    def users(self, query: str = "") -> list[dict[str, Any]]:
        return [
            {key: row[key] for key in ("user_id", "display_name", "role", "organization_id", "language", "plan", "status", "usage_count", "created_at", "last_activity_at")}
            for row in self.database.list_admin_users(query)
        ]

    def audit(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.database.connect() as conn:
            rows = conn.execute(
                "SELECT actor, object_type, action, reason, created_at FROM management_audit_events ORDER BY created_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            telemetry = conn.execute(
                "SELECT user_id, event_type, created_at FROM product_telemetry_events ORDER BY created_at DESC, event_id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {"actor": str(row["actor"]), "object": str(row["object_type"]), "action": str(row["action"]), "detail": str(row["reason"] or ""), "created_at": str(row["created_at"])}
            for row in rows
        ] + [
            {"actor": str(row["user_id"]), "object": "telemetry", "action": str(row["event_type"]), "detail": "", "created_at": str(row["created_at"])}
            for row in telemetry
        ]

    def advanced(self) -> dict[str, Any]:
        allowed = {"theme", "interface_language", "message_sounds_enabled", "reduce_motion", "runtime_engine", "codex_timeout_seconds", "response_timeout_seconds", "goal_turn_limit"}
        return {"settings": {key: self.settings.get(key) for key in sorted(allowed)}, "storage": "local durable database", "secrets": "masked"}

    def set_user_status(self, user_id: str, status: str, actor: str) -> bool:
        if status not in {"ACTIVE", "BLOCKED"}:
            raise ValueError("unsupported_user_status")
        changed = self.database.update_admin_user(user_id, status=status)
        if changed:
            self.database.log_event("admin_user_status_changed", json.dumps({"actor": actor, "user_id": user_id, "status": status}))
        return changed
