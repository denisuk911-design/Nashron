from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXE = PROJECT_ROOT / "dist" / "Team2050" / "Team2050.exe"
DEFAULT_WORK_DIR = PROJECT_ROOT / ".tmp_runtime_v3_packaged_gui_smoke"
DEFAULT_EVIDENCE_DIR = PROJECT_ROOT / "QA" / "HybridRuntimeV3"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run packaged Team2050 Runtime V3 GUI golden smoke.")
    parser.add_argument("--exe", default=str(DEFAULT_EXE), help="Path to packaged Team2050.exe.")
    parser.add_argument("--work-dir", default=str(DEFAULT_WORK_DIR), help="Smoke output directory.")
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE_DIR), help="Directory for compact report/screenshot evidence.")
    parser.add_argument("--timeout", type=int, default=45, help="Process timeout in seconds.")
    parser.add_argument("--keep-profile", action="store_true", help="Keep previous smoke profile data.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    exe = Path(args.exe).resolve()
    work_dir = Path(args.work_dir).resolve()
    profile_dir = work_dir / "profile"
    workspace_dir = work_dir / "workspace"
    report_path = work_dir / "runtime_v3_gui_smoke.json"
    if not exe.exists():
        print(json.dumps({"ok": False, "error": f"exe_not_found: {exe}"}, ensure_ascii=False, indent=2))
        return 2
    if work_dir.exists() and not args.keep_profile:
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "TEAM2050_HOME": str(profile_dir),
            "TEAM2050_RUNTIME_V3_GUI_SMOKE": "1",
            "TEAM2050_RUNTIME_V3_GUI_SMOKE_REPORT": str(report_path),
            "TEAM2050_RUNTIME_V3_GUI_SMOKE_WORKSPACE": str(workspace_dir),
        }
    )
    completed = subprocess.run([str(exe)], cwd=str(exe.parent), env=env, text=True, capture_output=True, timeout=args.timeout, check=False)
    if not report_path.exists():
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "report_not_created",
                    "returncode": completed.returncode,
                    "stdout": completed.stdout[-2000:],
                    "stderr": completed.stderr[-4000:],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["returncode"] = completed.returncode
    payload["exe"] = str(exe)
    payload["work_dir"] = str(work_dir)
    evidence_dir = Path(args.evidence_dir).resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_report = evidence_dir / "runtime_v3_packaged_gui_smoke.json"
    evidence_screenshot = evidence_dir / "runtime_v3_packaged_gui_smoke.png"
    screenshot = Path(str(payload.get("screenshot") or ""))
    if screenshot.exists():
        shutil.copyfile(screenshot, evidence_screenshot)
        payload["evidence_screenshot"] = str(evidence_screenshot)
    evidence_report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["evidence_report"] = str(evidence_report)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if completed.returncode == 0 and payload.get("checks_passed") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
