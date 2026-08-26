from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"


def _run(script: str) -> dict:
    completed = subprocess.run(
        [str(PYTHON), str(ROOT / "scripts" / script)], cwd=ROOT, text=True, capture_output=True, timeout=360, check=False
    )
    lines = completed.stdout.strip().splitlines()
    if completed.returncode:
        raise RuntimeError(f"{script} failed: {completed.stdout[-2000:]} {completed.stderr[-2000:]}")
    return json.loads("\n".join(lines))


def _foreign_keys_clean() -> bool:
    for root in (ROOT / ".tmp_runtime_v3_packaged_gui_smoke", ROOT / ".tmp_runtime_v3_hitl_packaged_smoke"):
        for database in root.rglob("*.sqlite3"):
            with sqlite3.connect(database) as connection:
                if connection.execute("PRAGMA foreign_key_check").fetchall():
                    return False
    return True


def main() -> int:
    golden = _run("runtime_v3_packaged_gui_smoke.py")
    hitl = _run("runtime_v3_hitl_packaged_smoke.py")
    checks = {
        "golden_complete": golden.get("checks_passed") is True,
        "autonomous_plan": golden.get("work_items", 0) >= 3 and golden.get("handoffs", 0) >= 1,
        "real_execution": golden.get("provider_actions", 0) >= 2 and golden.get("artifacts", 0) >= 3 and golden.get("evidence", 0) >= 4,
        "review_rework": golden.get("review_actions", 0) >= 2 and golden.get("rework_artifacts", 0) >= 1,
        "failover": "FAILED" in golden.get("provider_run_statuses", []) and "SUCCEEDED" in golden.get("provider_run_statuses", []),
        "hitl_restart_resume": hitl.get("checks_passed") is True and hitl.get("pending_interrupts") == 0,
        "foreign_keys": _foreign_keys_clean(),
    }
    payload = {"checks": checks, "checks_passed": all(checks.values()), "golden": golden, "hitl": hitl}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
