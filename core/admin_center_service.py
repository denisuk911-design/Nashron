from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from .database import Database


class AdminAccessError(PermissionError):
    """Raised when a non-owner/non-admin reaches the owner console."""


class PolicyDeniedError(PermissionError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class AdminCenterService:
    """Owner-console read models and audited administrative mutations.

    The service deliberately composes existing Core tables and services. It
    never fabricates product counts and never returns credentials.
    """

    ADMIN_ROLES = {"owner", "admin", "organization_owner", "organization_admin"}

    def __init__(self, database: Database, *, settings: dict[str, Any], management: Any, providers: Any, health: Any, credentials: Any | None = None) -> None:
        self.database = database
        self.settings = settings
        self.management = management
        self.providers = providers
        self.provider_health = health
        self.credentials = credentials

    @classmethod
    def authorize(cls, role: str | None, *, require_explicit: bool = False) -> str:
        normalized = str(role or ("" if require_explicit else "owner")).strip().lower()
        if normalized not in cls.ADMIN_ROLES:
            raise AdminAccessError("admin_access_required")
        return normalized

    def authorize_account(self, account_id: str | None, role: str | None, *, require_explicit: bool = False) -> str:
        """Prefer the durable account role when an account identity is supplied."""
        if account_id:
            with self.database.connect() as conn:
                row = conn.execute("SELECT role, status FROM admin_accounts WHERE account_id = ?", (account_id,)).fetchone()
            if row is None or str(row["status"]).upper() != "ACTIVE":
                raise AdminAccessError("admin_account_not_found_or_blocked")
            return self.authorize(str(row["role"]), require_explicit=True)
        return self.authorize(role, require_explicit=require_explicit)

    def touch_user(self, user_id: str, *, display_name: str, role: str, organization_id: str | None, language: str) -> None:
        self.database.upsert_admin_user({
            "user_id": user_id,
            "display_name": display_name,
            "role": role,
            "organization_id": organization_id,
            "language": language,
        })

    def dashboard(self, period: str = "30d", *, since: str | None = None, until: str | None = None) -> dict[str, Any]:
        if period not in {"today", "7d", "30d", "custom"}:
            raise ValueError("unsupported_analytics_period")
        if period == "today":
            since = datetime.now(timezone.utc).strftime("%Y-%m-%d 00:00:00")
        elif period in {"7d", "30d"}:
            since = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            days = 7 if period == "7d" else 30
            from datetime import timedelta
            since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        metrics = self.database.list_telemetry_metrics(since=since, until=until)
        with self.database.connect() as conn:
            counts = {
                "users": int(conn.execute("SELECT COUNT(*) FROM admin_accounts").fetchone()[0]),
                "visits": metrics.get("visit", 0),
                "registrations": metrics.get("registration", 0),
                "sessions": metrics.get("session_started", 0),
                "goals": int(conn.execute("SELECT COUNT(*) FROM project_plans").fetchone()[0]),
                "artifacts": int(conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]),
                "evidence": int(conn.execute("SELECT COUNT(*) FROM tool_evidence").fetchone()[0]),
                "errors": int(conn.execute("SELECT COUNT(*) FROM app_events WHERE event_type LIKE '%error%' OR event_type LIKE '%failure%'").fetchone()[0]),
                "active_users": int(conn.execute("SELECT COUNT(*) FROM admin_accounts WHERE status = 'ACTIVE'").fetchone()[0]),
                "unique_visitors": self._unique_event_users(conn, "visit", since, until),
                "goals_completed": int(conn.execute("SELECT COUNT(*) FROM project_plans WHERE status IN ('COMPLETED', 'COMPLETE')").fetchone()[0]),
            }
            for window, days in (("dau", 1), ("wau", 7), ("mau", 30)):
                counts[window] = int(conn.execute("SELECT COUNT(DISTINCT user_id) FROM product_telemetry_events WHERE datetime(created_at) >= datetime('now', ?)", (f"-{days} days",)).fetchone()[0])
            usage_rows = conn.execute("SELECT provider, COUNT(*) AS total, SUM(CASE WHEN ok = 1 THEN 1 ELSE 0 END) AS succeeded, AVG(duration_seconds) AS avg_latency, SUM(CASE WHEN error IS NOT NULL AND error <> '' THEN 1 ELSE 0 END) AS errors FROM agent_runs GROUP BY provider ORDER BY total DESC").fetchall()
            usage_filter = []
            usage_params: list[Any] = []
            if since:
                usage_filter.append("datetime(created_at) >= datetime(?)"); usage_params.append(since)
            if until:
                usage_filter.append("datetime(created_at) < datetime(?)"); usage_params.append(until)
            usage_where = " WHERE " + " AND ".join(usage_filter) if usage_filter else ""
            usage_events = conn.execute(
                f"SELECT provider_id, model_id, runtime, COUNT(*) AS requests, SUM(COALESCE(input_tokens, 0)) AS input_tokens, SUM(COALESCE(output_tokens, 0)) AS output_tokens, SUM(COALESCE(cost, 0)) AS cost, COUNT(cost) AS priced_requests, AVG(latency_ms) AS latency_ms, SUM(fallback) AS fallbacks FROM provider_usage_events{usage_where} GROUP BY provider_id, model_id, runtime ORDER BY requests DESC",
                usage_params,
            ).fetchall()
            events = conn.execute(
                "SELECT event_type, COUNT(*) AS total FROM product_telemetry_events GROUP BY event_type ORDER BY total DESC"
            ).fetchall()
        provider_rows = self.providers.profiles()
        provider_health = []
        for profile in provider_rows:
            current = self.provider_health.latest_health(profile.provider_id)
            provider_health.append({
                "name": profile.display_name,
                "state": current.health_status if current else "UNKNOWN",
                "configured": bool(self.credentials.is_configured(profile.provider_id)) if self.credentials is not None else bool(self.settings.get("active_provider_id") == profile.provider_id),
            })
        return {
            "counts": counts,
            "activation": self._activation_funnel(since=since, until=until),
            "event_types": [{"name": str(row["event_type"]), "count": int(row["total"])} for row in events],
            "providers": provider_health,
            "runtime_usage": [{"provider": str(row["provider"]), "runs": int(row["total"]), "succeeded": int(row["succeeded"] or 0), "errors": int(row["errors"] or 0), "avg_latency_seconds": round(float(row["avg_latency"] or 0), 3)} for row in usage_rows],
            "usage": {"provider_calls": metrics.get("provider_call", 0), "runtime_executions": metrics.get("runtime_execution", 0), "errors": metrics.get("error", 0), "fallbacks": metrics.get("fallback", 0), "tokens": {"status": "unavailable", "reason": "token telemetry is not configured"}, "latency": "from agent_runs"},
            "metered_usage": [{"provider": str(row["provider_id"]), "model": str(row["model_id"] or "unknown"), "runtime": str(row["runtime"] or "unknown"), "requests": int(row["requests"]), "input_tokens": int(row["input_tokens"] or 0), "output_tokens": int(row["output_tokens"] or 0), "cost": float(row["cost"] or 0) if int(row["priced_requests"] or 0) else None, "cost_status": "known" if int(row["priced_requests"] or 0) else "unavailable", "latency_ms": round(float(row["latency_ms"] or 0), 2), "fallbacks": int(row["fallbacks"] or 0)} for row in usage_events],
            "cost": {"status": "unavailable", "reason": "cost telemetry is not configured"},
            "period": period,
            "range": {"since": since, "until": until},
            "source": "database",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _unique_event_users(conn: Any, event_type: str, since: str | None, until: str | None) -> int:
        clauses = ["event_type = ?"]
        params: list[Any] = [event_type]
        if since:
            clauses.append("datetime(created_at) >= datetime(?)")
            params.append(since)
        if until:
            clauses.append("datetime(created_at) < datetime(?)")
            params.append(until)
        return int(conn.execute(f"SELECT COUNT(DISTINCT user_id) FROM product_telemetry_events WHERE {' AND '.join(clauses)}", params).fetchone()[0])

    def _activation_funnel(self, *, since: str | None = None, until: str | None = None) -> list[dict[str, Any]]:
        order = ["visit", "registration", "iris_opened", "constellation_opened", "goal_created", "goal_completed"]
        clauses = [f"event_type IN ({','.join('?' for _ in order)})"]
        params: list[Any] = list(order)
        if since:
            clauses.append("datetime(created_at) >= datetime(?)")
            params.append(since)
        if until:
            clauses.append("datetime(created_at) < datetime(?)")
            params.append(until)
        with self.database.connect() as conn:
            rows = conn.execute(f"SELECT event_type, COUNT(*) AS total FROM product_telemetry_events WHERE {' AND '.join(clauses)} GROUP BY event_type", params).fetchall()
        values = {str(row["event_type"]): int(row["total"]) for row in rows}
        return [{"stage": stage, "count": values.get(stage, 0)} for stage in order]

    def provider_read_model(self) -> list[dict[str, Any]]:
        result = []
        policies = {str(row["provider_id"]): row for row in self.database.list_provider_admin_policies()}
        for profile in self.providers.profiles():
            if profile.provider_id not in policies:
                self.database.upsert_provider_admin_policy(profile.provider_id)
                policies = {str(row["provider_id"]): row for row in self.database.list_provider_admin_policies()}
            current = self.provider_health.latest_health(profile.provider_id)
            policy = policies.get(profile.provider_id)
            result.append({
                "id": profile.provider_id,
                "name": profile.display_name,
                "family": profile.provider_family,
                "support": profile.support_status,
                "health": current.health_status if current else "UNKNOWN",
                "authentication": current.authentication_status if current else "NOT_CHECKED",
                "capabilities": list(profile.capability_matrix),
                "active": self.settings.get("active_provider_id") == profile.provider_id,
                "credential_saved": bool(self.credentials.is_configured(profile.provider_id)) if self.credentials is not None else False,
                "priority": int(policy["priority"]) if policy else 100,
                "fallback": None if not policy or not policy["fallback_provider_id"] else str(policy["fallback_provider_id"]),
                "limits": {"max_requests": policy["max_requests"] if policy else None, "timeout_seconds": int(policy["timeout_seconds"]) if policy else 180, "retries": int(policy["retries"]) if policy else 1},
                "enabled": bool(policy["enabled"]) if policy else True,
                "allowed_models": self.database.loads(policy["allowed_models"], []) if policy else [],
                "default_model": policy["default_model"] if policy else None,
                "quota": {"daily_requests": policy["daily_request_limit"] if policy else None, "monthly_requests": policy["monthly_request_limit"] if policy else None, "daily_tokens": policy["daily_token_limit"] if policy else None, "monthly_tokens": policy["monthly_token_limit"] if policy else None, "daily_cost": policy["daily_cost_limit"] if policy else None, "monthly_cost": policy["monthly_cost_limit"] if policy else None},
            })
        return result

    def users(self, query: str = "") -> list[dict[str, Any]]:
        return [
            {"account_id": row["account_id"], "user_id": row["account_id"], "display_name": row["display_name"], "role": row["role"], "organization_id": row["organization_id"], "language": row["language"], "plan": row["plan"], "status": row["status"], "usage_count": int(row["usage_count"]), "created_at": row["created_at"], "last_activity_at": row["last_activity_at"], "last_login": row["last_login"], "session_revoked_at": row["session_revoked_at"]}
            for row in self.database.list_admin_accounts(query)
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
        persisted = self.database.list_admin_settings()
        return {"settings": {key: persisted.get(key, self.settings.get(key)) for key in sorted(allowed)}, "storage": "local durable database", "secrets": "masked", "controls": {"retention_days": persisted.get("retention_days", 90), "registration_enabled": persisted.get("registration_enabled", True), "session_ttl_hours": persisted.get("session_ttl_hours", 24), "rate_limit_per_minute": persisted.get("rate_limit_per_minute", 60), "maintenance_mode": persisted.get("maintenance_mode", False)}}

    def health(self) -> dict[str, Any]:
        with self.database.connect() as conn:
            integrity = str(conn.execute("PRAGMA integrity_check").fetchone()[0])
            foreign_keys = len(conn.execute("PRAGMA foreign_key_check").fetchall())
        return {"database": "OK" if integrity.lower() == "ok" else "ERROR", "foreign_keys": foreign_keys, "runtime": "available", "status": "READY" if integrity.lower() == "ok" and foreign_keys == 0 else "DEGRADED"}

    def security(self) -> dict[str, Any]:
        return {"credential_storage": "protected", "secret_response": "never returned", "audit": "enabled", "rbac": "owner/admin", "recent": self.audit(40)}

    def plans(self) -> dict[str, Any]:
        plans = []
        with self.database.connect() as conn:
            counts = {str(row["plan"]): int(row["total"]) for row in conn.execute("SELECT plan, COUNT(*) AS total FROM admin_accounts GROUP BY plan").fetchall()}
        for row in self.database.list_admin_plans():
            plans.append({"id": str(row["plan_id"]), "name": str(row["display_name"]), "users": counts.get(str(row["plan_id"]), 0), "quotas": self.database.loads(row["quotas"], {})})
        return {"plans": plans, "source": "database", "enforcement": "safe hooks only; unsupported quotas remain read-only"}

    def pricing(self) -> list[dict[str, Any]]:
        return [
            {"provider": str(row["provider_id"]), "model": str(row["model_id"]), "input_price_per_million": row["input_price_per_million"], "output_price_per_million": row["output_price_per_million"], "effective_from": str(row["effective_from"]), "currency": str(row["currency"]), "source_note": str(row["source_note"]), "version": str(row["version"]), "active": bool(row["active"])}
            for row in self.database.list_provider_pricing()
        ]

    def save_pricing(self, values: dict[str, Any], actor: str) -> dict[str, Any]:
        if self.providers.get(str(values["provider_id"])) is None:
            raise ValueError("provider_not_found")
        pricing_id = self.database.upsert_provider_pricing(
            provider_id=str(values["provider_id"]), model_id=str(values["model_id"]),
            input_price_per_million=values.get("input_price_per_million"),
            output_price_per_million=values.get("output_price_per_million"),
            effective_from=str(values["effective_from"]), currency=str(values.get("currency") or "USD"),
            source_note=str(values.get("source_note") or ""), version=str(values.get("version") or "1"),
        )
        with self.database.connect() as conn:
            conn.execute(
                "INSERT INTO management_audit_events (id, actor, object_type, object_id, action, new_value, reason) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"ADMIN-{uuid.uuid4().hex[:12].upper()}", actor, "provider_pricing", pricing_id, "upserted", json.dumps({"provider_id": values["provider_id"], "model_id": values["model_id"], "version": values.get("version", "1")}), "Pricing registry action"),
            )
        return {"pricing_id": pricing_id, "status": "saved"}

    def set_user_status(self, user_id: str, status: str, actor: str) -> bool:
        if status not in {"ACTIVE", "BLOCKED"}:
            raise ValueError("unsupported_user_status")
        changed = self.database.update_admin_account(user_id, status=status)
        self.database.update_admin_user(user_id, status=status)
        if changed:
            detail = {"actor": actor, "user_id": user_id, "status": status}
            self.database.log_event("admin_user_status_changed", json.dumps(detail))
            with self.database.connect() as conn:
                conn.execute(
                    "INSERT INTO management_audit_events (id, actor, object_type, object_id, action, new_value, reason) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (f"ADMIN-{uuid.uuid4().hex[:12].upper()}", actor, "admin_user", user_id, "status_changed", json.dumps({"status": status}), "Owner Center action"),
                )
        return changed

    def update_account(self, account_id: str, actor: str, *, role: str | None = None, plan: str | None = None,
                       revoke_sessions: bool = False) -> bool:
        if role is not None and role.lower() not in {"owner", "admin", "member"}:
            raise ValueError("unsupported_account_role")
        if plan is not None and not any(str(row["plan_id"]) == plan for row in self.database.list_admin_plans()):
            raise ValueError("unsupported_plan")
        changed = self.database.update_admin_account(account_id, role=role.lower() if role else None, plan=plan, revoke_sessions=revoke_sessions)
        if changed:
            with self.database.connect() as conn:
                conn.execute(
                    "INSERT INTO management_audit_events (id, actor, object_type, object_id, action, new_value, reason) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (f"ADMIN-{uuid.uuid4().hex[:12].upper()}", actor, "account", account_id, "updated", json.dumps({"role": role, "plan": plan, "revoke_sessions": revoke_sessions}), "Admin account action"),
                )
        return changed

    def update_provider_policy(self, provider_id: str, *, priority: int, fallback_provider_id: str | None,
                               max_requests: int | None, timeout_seconds: int, retries: int,
                               enabled: bool, actor: str, allowed_models: list[str] | None = None,
                               default_model: str | None = None, daily_request_limit: int | None = None,
                               monthly_request_limit: int | None = None, daily_token_limit: int | None = None,
                               monthly_token_limit: int | None = None, daily_cost_limit: float | None = None,
                               monthly_cost_limit: float | None = None) -> bool:
        if self.providers.get(provider_id) is None:
            return False
        if fallback_provider_id and self.providers.get(fallback_provider_id) is None:
            raise ValueError("fallback_provider_not_found")
        if fallback_provider_id == provider_id:
            raise ValueError("provider_cannot_fallback_to_itself")
        self.database.upsert_provider_admin_policy(
            provider_id, priority=priority, fallback_provider_id=fallback_provider_id,
            max_requests=max_requests, timeout_seconds=timeout_seconds, retries=retries, enabled=enabled,
            allowed_models=allowed_models, default_model=default_model,
            daily_request_limit=daily_request_limit, monthly_request_limit=monthly_request_limit,
            daily_token_limit=daily_token_limit, monthly_token_limit=monthly_token_limit,
            daily_cost_limit=daily_cost_limit, monthly_cost_limit=monthly_cost_limit,
        )
        with self.database.connect() as conn:
            conn.execute(
                "INSERT INTO management_audit_events (id, actor, object_type, object_id, action, new_value, reason) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"ADMIN-{uuid.uuid4().hex[:12].upper()}", actor, "provider_policy", provider_id, "updated", json.dumps({"priority": priority, "fallback": fallback_provider_id, "max_requests": max_requests, "timeout_seconds": timeout_seconds, "retries": retries, "enabled": enabled}), "Admin provider policy action"),
            )
        return True

    def save_advanced_controls(self, values: dict[str, Any], actor: str) -> dict[str, Any]:
        allowed = {"retention_days", "registration_enabled", "session_ttl_hours", "rate_limit_per_minute", "maintenance_mode"}
        for key, value in values.items():
            if key not in allowed:
                raise ValueError("unsupported_admin_setting")
            self.database.save_admin_setting(key, value)
        with self.database.connect() as conn:
            conn.execute(
                "INSERT INTO management_audit_events (id, actor, object_type, object_id, action, new_value, reason) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"ADMIN-{uuid.uuid4().hex[:12].upper()}", actor, "admin_settings", "global", "updated", json.dumps(values), "Admin settings action"),
            )
        return self.advanced()

    def enforce_provider_policy(self, account_id: str, provider_id: str, *, model_id: str | None = None,
                                requested_capabilities: set[str] | None = None) -> dict[str, Any]:
        profile = self.providers.get(provider_id)
        if profile is None:
            raise PolicyDeniedError("provider_not_found")
        with self.database.connect() as conn:
            account = conn.execute("SELECT status, plan FROM admin_accounts WHERE account_id = ?", (account_id,)).fetchone()
        if account is not None and str(account["status"]).upper() != "ACTIVE":
            raise PolicyDeniedError("account_blocked")
        policy = next((row for row in self.database.list_provider_admin_policies() if str(row["provider_id"]) == provider_id), None)
        if policy is not None and not bool(policy["enabled"]):
            raise PolicyDeniedError("provider_disabled")
        allowed_models = self.database.loads(policy["allowed_models"], []) if policy else []
        effective_model = model_id or (str(policy["default_model"]) if policy and policy["default_model"] else None)
        if allowed_models and effective_model not in allowed_models:
            raise PolicyDeniedError("model_not_allowed")
        if requested_capabilities and not requested_capabilities.issubset(set(profile.capability_matrix)):
            raise PolicyDeniedError("capability_not_allowed")
        with self.database.connect() as conn:
            daily_requests = int(conn.execute("SELECT COALESCE(SUM(request_count),0) FROM provider_usage_events WHERE account_id = ? AND provider_id = ? AND datetime(created_at) >= datetime('now','-1 day')", (account_id, provider_id)).fetchone()[0])
            monthly_requests = int(conn.execute("SELECT COALESCE(SUM(request_count),0) FROM provider_usage_events WHERE account_id = ? AND provider_id = ? AND datetime(created_at) >= datetime('now','-30 days')", (account_id, provider_id)).fetchone()[0])
            daily_tokens = int(conn.execute("SELECT COALESCE(SUM(input_tokens),0)+COALESCE(SUM(output_tokens),0) FROM provider_usage_events WHERE account_id = ? AND provider_id = ? AND datetime(created_at) >= datetime('now','-1 day')", (account_id, provider_id)).fetchone()[0])
            monthly_tokens = int(conn.execute("SELECT COALESCE(SUM(input_tokens),0)+COALESCE(SUM(output_tokens),0) FROM provider_usage_events WHERE account_id = ? AND provider_id = ? AND datetime(created_at) >= datetime('now','-30 days')", (account_id, provider_id)).fetchone()[0])
            daily_cost = float(conn.execute("SELECT COALESCE(SUM(cost),0) FROM provider_usage_events WHERE account_id = ? AND provider_id = ? AND datetime(created_at) >= datetime('now','-1 day')", (account_id, provider_id)).fetchone()[0])
            monthly_cost = float(conn.execute("SELECT COALESCE(SUM(cost),0) FROM provider_usage_events WHERE account_id = ? AND provider_id = ? AND datetime(created_at) >= datetime('now','-30 days')", (account_id, provider_id)).fetchone()[0])
            plan_row = conn.execute("SELECT quotas FROM admin_plans WHERE plan_id = ?", (str(account["plan"]) if account else "",)).fetchone()
            monthly_account_requests = int(conn.execute("SELECT COALESCE(SUM(request_count),0) FROM provider_usage_events WHERE account_id = ? AND datetime(created_at) >= datetime('now','-30 days')", (account_id,)).fetchone()[0])
        checks = (("daily_request_limit", daily_requests), ("monthly_request_limit", monthly_requests), ("daily_token_limit", daily_tokens), ("monthly_token_limit", monthly_tokens), ("daily_cost_limit", daily_cost), ("monthly_cost_limit", monthly_cost))
        for limit_name, current in checks:
            limit = policy[limit_name] if policy else None
            if limit is not None and current >= int(limit):
                raise PolicyDeniedError(f"quota_exceeded:{limit_name}")
        if plan_row is not None:
            quotas = self.database.loads(plan_row["quotas"], {})
            plan_limit = quotas.get("ai_requests")
            if plan_limit is not None and monthly_account_requests >= int(plan_limit):
                raise PolicyDeniedError("plan_quota_exceeded:ai_requests")
        return {"provider_id": provider_id, "model_id": effective_model, "status": "allowed"}

    def audit_policy_denial(self, account_id: str, reason: str, provider_id: str, actor: str = "system") -> None:
        with self.database.connect() as conn:
            conn.execute(
                "INSERT INTO management_audit_events (id, actor, object_type, object_id, action, new_value, reason) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"ADMIN-{uuid.uuid4().hex[:12].upper()}", actor, "execution_policy", account_id, "denied", json.dumps({"provider_id": provider_id, "reason": reason}), "Policy enforcement denial"),
            )
