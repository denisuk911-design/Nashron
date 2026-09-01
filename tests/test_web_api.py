from __future__ import annotations

import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient


def test_web_health_and_openapi():
    from services.api.app import app

    client = TestClient(app)
    assert client.get("/api/health").json()["product"] == "Luminifera"
    assert client.get("/api/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/api/organizations" in schema["paths"]
    assert "/api/executions" in schema["paths"]


def test_product_shell_and_assets_are_served_by_fastapi():
    from services.api.app import app

    client = TestClient(app)
    assert client.get("/").status_code == 200
    assert client.get("/app").status_code == 200
    assert client.get("/assets/app.css").status_code == 200
    assert client.get("/assets/v3/app.js").status_code == 200
    assert client.get("/assets/v3/config.js").status_code == 200


def test_runtime_neutral_execution_endpoint_uses_iris_boundary(tmp_path, monkeypatch):
    monkeypatch.setenv("TEAM2050_HOME", str(tmp_path / "profile"))
    import services.api.app as app_module
    from core.agent_directory import ChatAgent
    from core.runtime_contracts import ExecutionResult, RuntimeEvent, RuntimeEventType

    isolated = app_module.WebCore()
    monkeypatch.setattr(app_module, "core", isolated)
    organization = isolated.universal.create_organization("Execution API")
    employee = ChatAgent(
        key="worker", agent_id="employee-1", display_name="Worker", provider_id="CODEX_CLI",
        roles=["DESIGN_ENGINEER"], persona_id=None, description="", avatar_path=None,
    )
    monkeypatch.setattr(app_module, "list_chat_agents", lambda database, organization_id: [employee])
    seen = {}

    def fake_execute(context, objective, employees, policy, *, preferred_runtime=""):
        seen.update({"organization_id": context.organization_id, "objective": objective, "policy": policy})
        return ExecutionResult(
            True, context.organization_id, "native", "done", context.conversation_id,
            events=(RuntimeEvent(RuntimeEventType.EXECUTION_COMPLETED, context.organization_id),),
        )

    monkeypatch.setattr(isolated.iris_orchestration, "execute", fake_execute)
    response = TestClient(app_module.app).post(
        "/api/executions",
        headers={"X-Organization-Id": organization.organization_id},
        json={"objective": "Say hello", "policy": "conversational"},
    )
    assert response.status_code == 200
    assert response.json()["summary"] == "done"
    assert response.json()["runtime_id"] == "native"
    assert response.json()["data"] == {}
    assert isinstance(seen["organization_id"], str)
    assert seen == {"organization_id": organization.organization_id, "objective": "Say hello", "policy": "conversational"}


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


def test_websocket_events_are_scoped_to_the_subscribed_organization():
    from services.api.app import ConnectionHub

    class FakeSocket:
        def __init__(self):
            self.payloads = []

        async def accept(self):
            return None

        async def send_text(self, payload):
            self.payloads.append(payload)

    hub = ConnectionHub()
    first, second = FakeSocket(), FakeSocket()
    asyncio.run(hub.add(first, "org-a"))
    asyncio.run(hub.add(second, "org-b"))
    asyncio.run(hub.publish({"type": "goal.created", "data": {"organization_id": "org-a"}}))

    assert len(first.payloads) == 1
    assert second.payloads == []


def test_web_event_contract_stamps_real_event_time():
    from services.api.events import EventEnvelope

    event = EventEnvelope.create("goal.created", {"goal": "test"})
    assert event.type == "goal.created"
    assert event.occurred_at.endswith("+00:00")


def test_web_iris_state_is_scoped_and_product_safe(tmp_path, monkeypatch):
    monkeypatch.setenv("TEAM2050_HOME", str(tmp_path / "profile"))
    import services.api.app as app_module

    isolated = app_module.WebCore()
    monkeypatch.setattr(app_module, "core", isolated)
    organization = isolated.universal.create_organization("Iris state")
    response = TestClient(app_module.app).get(
        "/api/iris", headers={"X-Organization-Id": organization.organization_id}
    )
    assert response.status_code == 200
    assert response.json()["state"] in {"idle", "listening", "planning", "working", "waiting_for_user", "attention", "warning", "complete"}
    assert "agent_id" not in response.json()


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


def test_web_skill_creation_and_lifecycle_are_organization_scoped(tmp_path, monkeypatch):
    monkeypatch.setenv("TEAM2050_HOME", str(tmp_path / "profile"))
    import services.api.app as app_module

    isolated = app_module.WebCore()
    monkeypatch.setattr(app_module, "core", isolated)
    organization_a = isolated.universal.create_organization("Skills A")
    organization_b = isolated.universal.create_organization("Skills B")
    client = TestClient(app_module.app)
    headers_a = {"X-Organization-Id": organization_a.organization_id}
    headers_b = {"X-Organization-Id": organization_b.organization_id}

    response = client.post(
        "/api/skills",
        headers=headers_a,
        json={"name": "PCB review", "purpose": "Review a board", "supported_roles": ["QA_ENGINEER"]},
    )
    assert response.status_code == 200
    skill_id = response.json()["id"]
    assert any(item["id"] == skill_id for item in client.get("/api/skills", headers=headers_a).json())
    assert all(item["id"] != skill_id for item in client.get("/api/skills", headers=headers_b).json())
    assert client.patch(f"/api/skills/{skill_id}/status", headers=headers_b, json={"status": "ACTIVE"}).status_code == 404
    assert client.patch(f"/api/skills/{skill_id}/status", headers=headers_a, json={"status": "PRACTICED"}).status_code == 200


def test_web_knowledge_promotion_requires_scoped_real_run(tmp_path, monkeypatch):
    monkeypatch.setenv("TEAM2050_HOME", str(tmp_path / "profile"))
    import services.api.app as app_module

    isolated = app_module.WebCore()
    monkeypatch.setattr(app_module, "core", isolated)
    organization = isolated.universal.create_organization("Knowledge API")
    response = TestClient(app_module.app).post(
        "/api/knowledge",
        headers={"X-Organization-Id": organization.organization_id},
        json={
            "source_run_id": "RUN-MISSING",
            "competence": "Evidence review",
            "title": "Review rule",
            "content": "Only verified evidence becomes reusable knowledge.",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "run_not_found"


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
