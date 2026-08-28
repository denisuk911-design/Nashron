from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.finalize_beta_release import build, verify


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the final Team2050 Beta release acceptance matrix.")
    parser.add_argument("--source", default=str(ROOT / "dist" / "Team2050"))
    parser.add_argument("--work-dir", default=str(ROOT / ".tmp_task059_release"))
    parser.add_argument("--evidence", default=str(ROOT / "QA" / "Task059" / "release_acceptance.json"))
    args = parser.parse_args()
    work = Path(args.work_dir).resolve()
    target, archive = build(Path(args.source).resolve(), work / "package" / "Team2050-Beta", "2.6.0-beta.2")
    smoke = work / "beta-smoke.json"
    result = subprocess.run(
        [sys.executable, "scripts/beta_install_smoke.py", "--source", str(target), "--work-dir", str(work / "lifecycle"), "--evidence", str(smoke)],
        cwd=ROOT,
        check=False,
    )
    smoke_payload = json.loads(smoke.read_text(encoding="utf-8")) if smoke.is_file() else {}
    payload = {
        "package_integrity": verify(target),
        "archive_exists": archive.is_file(),
        "lifecycle": smoke_payload,
        "lifecycle_exit_code": result.returncode,
        "checks_passed": verify(target) and archive.is_file() and result.returncode == 0 and smoke_payload.get("checks_passed") is True,
    }
    evidence = Path(args.evidence).resolve()
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
