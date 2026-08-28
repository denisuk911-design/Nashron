from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a packaged Team2050 Preview profile across restart.")
    parser.add_argument("--exe", default=str(ROOT / "dist" / "Team2050" / "Team2050.exe"))
    parser.add_argument("--work-dir", default=str(ROOT / ".tmp_packaged_preview_smoke"))
    parser.add_argument("--evidence-dir", default=str(ROOT / "QA" / "Preview"))
    args = parser.parse_args()
    exe = Path(args.exe).resolve()
    work_dir = Path(args.work_dir).resolve()
    profile_dir = work_dir / "profile"
    if not exe.is_file():
        print(json.dumps({"checks_passed": False, "error": "exe_not_found"}))
        return 2
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)
    reports: list[dict[str, object]] = []
    for launch in ("first", "second"):
        report_path = work_dir / f"{launch}.json"
        environment = os.environ.copy()
        environment.update(
            {
                "TEAM2050_PREVIEW": "1",
                "TEAM2050_PREVIEW_HOME": str(profile_dir),
                "TEAM2050_PREVIEW_SMOKE": "1",
                "TEAM2050_PREVIEW_SMOKE_REPORT": str(report_path),
            }
        )
        completed = subprocess.run([str(exe)], cwd=str(exe.parent), env=environment, timeout=45, check=False)
        if not report_path.is_file():
            print(json.dumps({"checks_passed": False, "error": f"missing_{launch}_report", "returncode": completed.returncode}))
            return 1
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["returncode"] = completed.returncode
        reports.append(report)
    first, second = reports
    checks_passed = (
        all(item.get("checks_passed") is True and item.get("returncode") == 0 for item in reports)
        and first["user_avatar_path"] == second["user_avatar_path"]
        and first["background_path"] == second["background_path"]
    )
    evidence_dir = Path(args.evidence_dir).resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence = evidence_dir / "packaged_preview_smoke.json"
    payload = {"checks_passed": checks_passed, "first": first, "second": second, "exe": str(exe)}
    evidence.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if checks_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
