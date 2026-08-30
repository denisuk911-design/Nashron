from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient


def test_web_health_and_openapi():
    from services.api.app import app

    client = TestClient(app)
    assert client.get("/api/health").json()["product"] == "Luminifera"
    assert client.get("/api/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/api/organizations" in schema["paths"]


def test_web_unknown_organization_is_rejected():
    from services.api.app import app

    client = TestClient(app)
    response = client.get("/api/organizations/missing/home")
    assert response.status_code == 404


def test_websocket_event_contract_is_available():
    from services.api.app import app

    client = TestClient(app)
    with client.websocket_connect("/api/events") as socket:
        socket.send_text("ping")


def test_web_event_contract_stamps_real_event_time():
    from services.api.events import EventEnvelope

    event = EventEnvelope.create("goal.created", {"goal": "test"})
    assert event.type == "goal.created"
    assert event.occurred_at.endswith("+00:00")


def test_unknown_provider_check_is_rejected():
    from services.api.app import app

    client = TestClient(app)
    assert client.post("/api/providers/not-real/check").status_code == 404


def test_web_work_items_is_a_safe_product_read_model():
    from services.api.app import app

    client = TestClient(app)
    response = client.get("/api/work/items")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_web_review_is_a_safe_product_read_model():
    from services.api.app import app

    response = TestClient(app).get("/api/work/review")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_web_timeline_is_a_safe_product_read_model():
    from services.api.app import app

    response = TestClient(app).get("/api/work/timeline")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_web_file_preview_and_download_are_scoped():
    from services.api.app import app

    client = TestClient(app)
    assert client.get("/api/files/not-real/preview").status_code == 404
    assert client.get("/api/files/not-real/download").status_code == 404


def test_web_goal_requires_an_assigned_director_without_server_error():
    from services.api.app import app

    client = TestClient(app)
    organization = client.post(
        "/api/organizations",
        json={"name": f"No director {uuid4().hex}", "purpose": "API error contract"},
    )
    response = client.post(
        "/api/goals",
        headers={"X-Organization-Id": organization.json()["organization_id"]},
        json={"objective": "Verify the API error contract"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "director_not_assigned"


def test_web_goal_detail_is_scoped_and_hides_runtime_assignment_ids(tmp_path, monkeypatch):
    monkeypatch.setenv("TEAM2050_HOME", str(tmp_path / "profile"))
    import services.api.app as app_module

    isolated = app_module.WebCore()
    monkeypatch.setattr(app_module, "core", isolated)
    client = TestClient(app_module.app)
    template = next(item for item in isolated.universal.list_templates() if item.name == "PCB_ENGINEERING_TEAM")
    organization = isolated.universal.activate_template(template.template_id, "Goal detail", team_size="STANDARD").organization
    plan = isolated.supervisor.director(organization.organization_id, "Expose a safe goal view")
    plan_id = plan.plan_id
    headers = {"X-Organization-Id": organization.organization_id}
    response = client.get(f"/api/goals/{plan_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["plan_id"] == plan_id
    assert "director_agent_id" not in response.json()
    assert client.get(f"/api/goals/{plan_id}", headers={"X-Organization-Id": "missing"}).status_code == 404


def test_web_organization_memory_and_competence_are_server_scoped(tmp_path, monkeypatch):
    monkeypatch.setenv("TEAM2050_HOME", str(tmp_path / "profile"))
    import services.api.app as app_module

    isolated = app_module.WebCore()
    monkeypatch.setattr(app_module, "core", isolated)
    organization_a = isolated.universal.create_organization("Memory A")
    organization_b = isolated.universal.create_organization("Memory B")
    entry_id = isolated.database.create_organization_memory_entry(
        {
            "organization_id": organization_a.organization_id,
            "title": "Reviewed routing rule",
            "content": "Route independent review to a qualified reviewer.",
            "lifecycle_state": "VERIFIED",
            "source_employee_name": "Reviewer",
            "evidence": {"artifact_ids": ["ART-1"]},
        }
    )
    isolated.database.upsert_organization_competence_node(
        {
            "organization_id": organization_a.organization_id,
            "employee_name": "Reviewer",
            "competence": "Independent review",
            "source_memory_id": entry_id,
            "evidence": {"artifact_ids": ["ART-1"]},
        }
    )

    client = TestClient(app_module.app)
    headers_a = {"X-Organization-Id": organization_a.organization_id}
    headers_b = {"X-Organization-Id": organization_b.organization_id}
    memory_a = client.get("/api/knowledge", headers=headers_a)
    competence_a = client.get("/api/competence", headers=headers_a)

    assert memory_a.status_code == 200
    assert memory_a.json() == [
        {
            "id": entry_id,
            "title": "Reviewed routing rule",
            "summary": "Route independent review to a qualified reviewer.",
            "status": "VERIFIED",
            "source": "Reviewer",
            "verified": True,
        }
    ]
    assert competence_a.status_code == 200
    assert competence_a.json()[0]["growth_points"] == 1
    assert client.get("/api/knowledge", headers=headers_b).json() == []
    assert client.get("/api/competence", headers=headers_b).json() == []
    with isolated.database.connect() as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_web_owner_profile_and_avatar_are_persisted_and_validated(tmp_path, monkeypatch):
    monkeypatch.setenv("TEAM2050_HOME", str(tmp_path / "profile"))
    import services.api.app as app_module

    isolated = app_module.WebCore()
    monkeypatch.setattr(app_module, "core", isolated)
    client = TestClient(app_module.app)
    avatars = client.get("/api/profile/avatars")
    assert avatars.status_code == 200
    assert avatars.json()
    selected = avatars.json()[0]["name"]

    response = client.patch("/api/profile", json={"display_name": "Василий", "avatar": selected})
    assert response.status_code == 200
    assert response.json() == {"display_name": "Василий", "avatar": selected}
    assert client.get("/api/profile").json() == {"display_name": "Василий", "avatar": selected}
    assert client.get(f"/api/profile/avatars/{selected}").status_code == 200
    assert client.patch("/api/profile", json={"display_name": "Василий", "avatar": "missing.png"}).status_code == 422

    restarted = app_module.WebCore()
    assert restarted.settings["owner_display_name"] == "Василий"
    assert restarted.settings["user_avatar_path"].endswith(selected)


def test_web_profile_backup_is_generated_by_core_service(tmp_path, monkeypatch):
    monkeypatch.setenv("TEAM2050_HOME", str(tmp_path / "profile"))
    import services.api.app as app_module

    isolated = app_module.WebCore()
    monkeypatch.setattr(app_module, "core", isolated)
    response = TestClient(app_module.app).get("/api/profile/backup")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")
    assert response.content.startswith(b"PK")


def test_web_team_controls_are_idempotent_after_dom_rerenders():
    from pathlib import Path

    source = (Path(__file__).parents[1] / "apps" / "web" / "static" / "actions.js").read_text(encoding="utf-8")
    assert "data-employee-actions" in source
    assert "if (row.querySelector('[data-employee-actions]')) return;" in source
