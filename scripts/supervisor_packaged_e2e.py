from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the packaged Supervisor owner-chat E2E smoke.")
    parser.add_argument("--exe", default=str(ROOT / "dist" / "Team2050" / "Team2050.exe"))
    parser.add_argument("--work-dir", default=str(ROOT / ".tmp_supervisor_packaged_e2e"))
    parser.add_argument("--evidence-dir", default=str(ROOT / "QA" / "Task066E2E"))
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()

    exe = Path(args.exe).resolve()
    work_dir = Path(args.work_dir).resolve()
    if not exe.is_file():
        print(json.dumps({"checks_passed": False, "error": "exe_not_found"}))
        return 2
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)
    report = work_dir / "supervisor_e2e.json"
    environment = os.environ.copy()
    environment.update({
        "TEAM2050_HOME": str(work_dir),
        "TEAM2050_SUPERVISOR_E2E_SMOKE": "1",
        "TEAM2050_SUPERVISOR_E2E_SMOKE_REPORT": str(report),
    })
    completed = subprocess.run(
        [str(exe)], cwd=str(exe.parent), env=environment,
        timeout=args.timeout, check=False,
    )
    if not report.is_file():
        payload = {"checks_passed": False, "error": "report_not_created", "returncode": completed.returncode}
    else:
        payload = json.loads(report.read_text(encoding="utf-8"))
        payload["returncode"] = completed.returncode
        payload["exe"] = str(exe)
    evidence_dir = Path(args.evidence_dir).resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence = evidence_dir / "supervisor_packaged_e2e.json"
    evidence.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    # Windows GUI launches may inherit a legacy code page; keep console output
    # portable while the evidence file remains UTF-8 and human-readable.
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0 if completed.returncode == 0 and payload.get("checks_passed") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
