from __future__ import annotations

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
