import hashlib

from fastapi.testclient import TestClient


def test_admin_center_is_real_read_model_and_rejects_member(tmp_path, monkeypatch):
    monkeypatch.setenv("TEAM2050_HOME", str(tmp_path / "profile"))
    import services.api.app as app_module

    isolated = app_module.WebCore()
    monkeypatch.setattr(app_module, "core", isolated)
    client = TestClient(app_module.app)
    assert client.get("/api/admin/access").json()["allowed"] is True
    assert client.get("/api/admin/dashboard").json()["source"] == "database"
    assert client.get("/api/admin/providers").status_code == 200
    assert client.get("/api/admin/users").status_code == 200
    assert client.get("/api/admin/advanced").status_code == 200
    assert client.get("/api/admin/audit").status_code == 200
    assert client.get("/api/admin/health").json()["foreign_keys"] == 0
    assert client.get("/api/admin/security").json()["rbac"] == "authenticated account role"
    assert client.get("/api/admin/plans").status_code == 200
    assert client.get("/api/admin/dashboard", headers={"X-User-Role": "member"}).status_code == 403


def test_telemetry_persists_and_feeds_activation_funnel(tmp_path, monkeypatch):
    monkeypatch.setenv("TEAM2050_HOME", str(tmp_path / "profile"))
    import services.api.app as app_module

    isolated = app_module.WebCore()
    monkeypatch.setattr(app_module, "core", isolated)
    client = TestClient(app_module.app)
    for event_type in ("visit", "iris_opened", "goal_created"):
        response = client.post("/api/telemetry", json={"event_type": event_type, "user_id": "test-user"})
        assert response.status_code == 200
    dashboard = client.get("/api/admin/dashboard").json()
    counts = dashboard["counts"]
    assert counts["visits"] == 1
    assert {item["stage"] for item in dashboard["activation"]} >= {"visit", "iris_opened", "goal_created"}
    assert client.post("/api/telemetry", json={"event_type": "secret", "user_id": "x"}).status_code == 422


def test_admin_provider_actions_are_guarded_and_never_return_credentials(tmp_path, monkeypatch):
    monkeypatch.setenv("TEAM2050_HOME", str(tmp_path / "profile"))
    import services.api.app as app_module

    isolated = app_module.WebCore()
    monkeypatch.setattr(app_module, "core", isolated)
    client = TestClient(app_module.app)
    provider = isolated.provider_registry.profiles()[0].provider_id
    check = client.post(f"/api/admin/providers/{provider}/check")
    assert check.status_code == 200
    assert "credential" not in check.json()
    assert client.post(f"/api/admin/providers/{provider}/check", headers={"X-User-Role": "member"}).status_code == 403


def test_phase2_analytics_periods_accounts_and_provider_policy_are_persistent(tmp_path, monkeypatch):
    monkeypatch.setenv("TEAM2050_HOME", str(tmp_path / "profile"))
    import services.api.app as app_module

    isolated = app_module.WebCore()
    monkeypatch.setattr(app_module, "core", isolated)
    client = TestClient(app_module.app)
    for event_type in ("visit", "registration", "login", "iris_opened", "provider_call", "runtime_execution", "fallback"):
        assert client.post("/api/telemetry", json={"event_type": event_type, "user_id": "acct-1"}).status_code == 200

    dashboard = client.get("/api/admin/analytics?period=7d").json()
    assert dashboard["period"] == "7d"
    assert dashboard["counts"]["visits"] == 1
    assert dashboard["usage"]["fallbacks"] == 1
    assert client.get("/api/admin/analytics?period=bad").status_code == 422

    assert client.get("/api/admin/access", headers={"X-Account-Id": "acct-1"}).status_code == 403
    isolated.database.upsert_admin_user({"user_id": "acct-admin", "display_name": "Admin", "role": "admin", "organization_id": None, "language": "ru"})
    assert client.get("/api/admin/access", headers={"X-Account-Id": "acct-admin"}).status_code == 200
    provider = isolated.provider_registry.profiles()[0].provider_id
    policy = client.patch(f"/api/admin/providers/{provider}/policy", json={"priority": 2, "timeout_seconds": 45, "retries": 2, "enabled": True})
    assert policy.status_code == 200
    assert policy.json()["priority"] == 2
    controls = client.patch("/api/admin/advanced", json={"retention_days": 180, "maintenance_mode": True})
    assert controls.status_code == 200
    assert controls.json()["controls"]["retention_days"] == 180
    assert controls.json()["controls"]["maintenance_mode"] is True
    assert any(item["object"] in {"provider_policy", "admin_settings"} for item in client.get("/api/admin/audit").json())
    revoke = client.post("/api/admin/users/acct-1/revoke-sessions", json={"confirm": True})
    assert revoke.status_code == 200
    assert client.get("/api/admin/users/acct-1").json()["session_revoked_at"] is not None


def test_phase4_auth_pricing_and_quota_denial_are_real(tmp_path, monkeypatch):
    monkeypatch.setenv("TEAM2050_HOME", str(tmp_path / "profile"))
    import services.api.app as app_module

    isolated = app_module.WebCore()
    monkeypatch.setattr(app_module, "core", isolated)
    client = TestClient(app_module.app)
    assert client.get("/api/admin/access").status_code == 200
    credential = client.put("/api/admin/users/owner/credential", json={"password": "phase4-pass-123", "confirm": True})
    assert credential.status_code == 200
    login = client.post("/api/auth/login", json={"account_id": "owner", "password": "phase4-pass-123"})
    assert login.status_code == 200
    token = login.json()["token"]
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["account_id"] == "owner"
    assert client.get("/api/admin/access", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    provider = isolated.provider_registry.profiles()[0].provider_id
    price = client.put("/api/admin/pricing", json={"provider_id": provider, "model_id": "phase4-model", "input_price_per_million": 1.0, "output_price_per_million": 2.0, "effective_from": "2026-01-01T00:00:00Z", "source_note": "test registry"})
    assert price.status_code == 200
    usage = client.post("/api/usage", json={"account_id": "owner", "provider_id": provider, "model_id": "phase4-model", "input_tokens": 1000, "output_tokens": 500})
    assert usage.status_code == 200
    assert client.get("/api/admin/analytics").json()["metered_usage"][0]["cost_status"] == "known"
    policy = client.patch(f"/api/admin/providers/{provider}/policy", json={"daily_request_limit": 1, "enabled": True})
    assert policy.status_code == 200
    with __import__("pytest").raises(Exception, match="quota_exceeded:daily_request_limit"):
        isolated.admin.enforce_provider_policy("owner", provider)
    blocked = client.patch("/api/admin/users/owner/status", json={"status": "BLOCKED", "confirm": True})
    assert blocked.status_code == 200
    assert client.get("/api/admin/access", headers={"X-Account-Id": "owner"}).status_code == 403
    assert client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"}).json()["revoked"] is True
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_phase5_public_auth_gate_rate_limit_and_security_read_model(tmp_path, monkeypatch):
    monkeypatch.setenv("TEAM2050_HOME", str(tmp_path / "profile"))
    import services.api.app as app_module

    isolated = app_module.WebCore()
    monkeypatch.setattr(app_module, "core", isolated)
    client = TestClient(app_module.app)
    assert client.post("/api/auth/register", json={"account_id": "new-user", "display_name": "New User", "password": "safe-pass-123"}).status_code == 403
    assert client.get("/api/admin/security").json()["registration"] == "disabled by default"
    assert client.patch("/api/admin/advanced", json={"registration_enabled": True, "rate_limit_per_minute": 2}).status_code == 200
    created = client.post("/api/auth/register", json={"account_id": "new-user", "display_name": "New User", "password": "safe-pass-123", "language": "en"})
    assert created.status_code == 201
    assert client.post("/api/auth/register", json={"account_id": "new-user", "display_name": "Again", "password": "safe-pass-123"}).status_code == 409
    assert client.post("/api/auth/login", json={"account_id": "new-user", "password": "wrong-pass-123"}).status_code == 401
    assert client.post("/api/auth/login", json={"account_id": "new-user", "password": "wrong-pass-123"}).status_code == 401
    assert client.post("/api/auth/login", json={"account_id": "new-user", "password": "safe-pass-123"}).json().get("token") is None
    security = client.get("/api/admin/security").json()
    assert security["failed_logins_last_15m"] >= 2
    assert security["registration"] == "enabled"
    assert client.get("/api/health").headers["X-Content-Type-Options"] == "nosniff"


def test_phase6_first_owner_bootstrap_password_rotation_and_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("TEAM2050_HOME", str(tmp_path / "profile"))
    import services.api.app as app_module

    isolated = app_module.WebCore()
    monkeypatch.setattr(app_module, "core", isolated)
    client = TestClient(app_module.app)
    bootstrap = client.post("/api/auth/bootstrap", json={"account_id": "first-owner", "display_name": "First Owner", "password": "owner-pass-123", "language": "en"})
    assert bootstrap.status_code == 201
    assert client.post("/api/auth/bootstrap", json={"account_id": "second-owner", "display_name": "Second", "password": "owner-pass-123"}).status_code == 409
    login = client.post("/api/auth/login", json={"account_id": "first-owner", "password": "owner-pass-123"})
    assert login.status_code == 200
    token = login.json()["token"]
    assert client.patch("/api/admin/users/first-owner", headers={"Authorization": f"Bearer {token}"}, json={"role": "member"}).status_code == 422
    rotated = client.put("/api/auth/password", headers={"Authorization": f"Bearer {token}"}, json={"password": "rotated-pass-456"})
    assert rotated.status_code == 200
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    new_login = client.post("/api/auth/login", json={"account_id": "first-owner", "password": "rotated-pass-456"})
    assert new_login.status_code == 200
    new_token = new_login.json()["token"]
    assert client.post("/api/auth/logout", headers={"Authorization": f"Bearer {new_token}"}).json()["revoked"] is True
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_token}"}).status_code == 401
    expired_login = client.post("/api/auth/login", json={"account_id": "first-owner", "password": "rotated-pass-456"})
    assert expired_login.status_code == 200
    expired_token = expired_login.json()["token"]
    with isolated.database.connect() as conn:
        conn.execute("UPDATE admin_sessions SET expires_at = ? WHERE token_hash = ?", ("2000-01-01T00:00:00+00:00", hashlib.sha256(expired_token.encode()).hexdigest()))
    expired_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert expired_response.status_code == 401
    assert expired_response.json()["detail"] == "session_expired"
    assert client.get("/api/admin/security").json()["owner_bootstrap"] == "closed"
    restarted = app_module.WebCore()
    assert restarted.admin.security()["owner_bootstrap"] == "closed"


def test_public_bootstrap_status_is_available_without_admin_headers(tmp_path, monkeypatch):
    monkeypatch.setenv("TEAM2050_HOME", str(tmp_path / "profile"))
    import services.api.app as app_module

    isolated = app_module.WebCore()
    monkeypatch.setattr(app_module, "core", isolated)
    client = TestClient(app_module.app)
    status = client.get("/api/auth/bootstrap-status")
    assert status.status_code == 200
    assert status.json() == {"owner_bootstrap": "available for fresh install", "registration_enabled": False}
    created = client.post("/api/auth/bootstrap", json={"account_id": "owner@example.com", "display_name": "Owner", "password": "owner-pass-123", "language": "uk"})
    assert created.status_code == 201
    assert client.get("/api/auth/bootstrap-status").json()["owner_bootstrap"] == "closed"
