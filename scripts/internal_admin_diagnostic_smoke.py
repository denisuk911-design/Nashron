from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.database import Database
from core.internal_assistant_service import Team2050InternalAssistant
from core.provider_service import ProviderHealthService, ProviderRegistry


def main() -> int:
    root = Path(".tmp_internal_admin_smoke").resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = Database(root / "team2050.sqlite3")
    database.initialize()
    registry = ProviderRegistry(database)
    registry.ensure_defaults()
    assistant = Team2050InternalAssistant(ProviderHealthService(database, registry, {}))
    answer = assistant.explain_employee_unavailable("CODEX_CLI")
    with sqlite3.connect(root / "team2050.sqlite3") as connection:
        fk = connection.execute("PRAGMA foreign_key_check").fetchall()
    payload = {"answer": answer, "goals": 0, "work_items": 0, "supervisor_runs": 0, "foreign_keys": fk}
    payload["ok"] = bool(answer) and not fk
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
