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
