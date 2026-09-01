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
    assert client.get("/api/admin/security").json()["rbac"] == "owner/admin"
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
