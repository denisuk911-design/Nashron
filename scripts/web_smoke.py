from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a deterministic Luminifera Web API smoke scenario.")
    parser.add_argument("--profile", required=True, help="Isolated Team2050 profile directory")
    parser.add_argument("--report", required=True, help="JSON report path")
    args = parser.parse_args()
    os.environ["TEAM2050_HOME"] = str(Path(args.profile).resolve())

    from fastapi.testclient import TestClient
    from services.api.app import WebCore, app

    client = TestClient(app)
    team = client.post(
        "/api/teams",
        json={
            "brief": "Software product verification with an independent review",
            "organization_name": "Web Smoke",
            "team_size": "MINI",
        },
    )
    team.raise_for_status()
    organization_id = team.json()["organization"]["organization_id"]
    headers = {"X-Organization-Id": organization_id}
    chat = client.post("/api/chat", headers=headers, json={"content": "Hello, Iris"})
    chat.raise_for_status()
    goal = client.post(
        "/api/goals",
        headers=headers,
        json={"objective": "Prepare a Web API verification plan"},
    )
    goal.raise_for_status()
    started = client.post(
        f"/api/goals/{goal.json()['plan_id']}/start",
        headers=headers,
    )
    started.raise_for_status()
    started_payload = started.json()

    restarted = WebCore()
    persisted = any(item.organization_id == organization_id for item in restarted.universal.list_organizations())
    payload = {
        "organization_id": organization_id,
        "team_member_count": len(team.json()["activation"]["employee_ids"]),
        "chat_result": chat.json()["result"]["ok"],
        "goal_id": goal.json()["plan_id"],
        "goal_start_result": started_payload,
        "persistence_after_webcore_restart": persisted,
        "checks_passed": bool(
            persisted
            and chat.status_code == 200
            and goal.status_code == 200
            and started_payload.get("ok") is True
            and started_payload.get("work_items", 0) >= 2
            and started_payload.get("artifacts", 0) >= 1
            and started_payload.get("evidence", 0) >= 1
            and started_payload.get("receipt_ready") is True
        ),
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload["checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
