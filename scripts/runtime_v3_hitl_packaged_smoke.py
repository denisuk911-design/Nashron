from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXE = PROJECT_ROOT / "dist" / "Team2050" / "Team2050.exe"
WORK_DIR = PROJECT_ROOT / ".tmp_runtime_v3_hitl_packaged_smoke"


def main() -> int:
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    report = WORK_DIR / "hitl.json"
    environment = os.environ.copy()
    environment.update({
        "ROMAN2050_HOME": str(WORK_DIR / "profile"),
        "TEAM2050_RUNTIME_V3_HITL_SMOKE": "1",
        "TEAM2050_RUNTIME_V3_HITL_SMOKE_REPORT": str(report),
        "TEAM2050_RUNTIME_V3_GUI_SMOKE_WORKSPACE": str(WORK_DIR / "workspace"),
    })
    result = subprocess.run([str(EXE)], cwd=str(EXE.parent), env=environment, capture_output=True, text=True, timeout=60, check=False)
    payload = json.loads(report.read_text(encoding="utf-8")) if report.exists() else {"checks_passed": False, "error": "report_not_created"}
    payload["returncode"] = result.returncode
    payload["exe"] = str(EXE)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if result.returncode == 0 and payload.get("checks_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
