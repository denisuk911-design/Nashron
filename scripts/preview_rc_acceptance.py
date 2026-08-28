from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Team2050 Preview RC acceptance matrix.")
    parser.add_argument("--exe", default=str(ROOT / "release" / "Team2050-Preview-RC" / "Team2050.exe"))
    parser.add_argument("--work-dir", default=str(ROOT / ".tmp_preview_rc_acceptance"))
    parser.add_argument("--evidence-dir", default=str(ROOT / "QA" / "PreviewRC"))
    args = parser.parse_args()
    tests = [
        "tests/test_startup_bootstrap.py",
        "tests/test_organization_activation.py",
        "tests/test_team2050_conversation_modes.py",
        "tests/test_runtime_v3_intent_boundary.py",
        "tests/runtime_v3/test_outcome_engine.py",
        "tests/test_phase2a_director_console.py",
        "tests/test_profession_workspace_service.py",
        "tests/test_demo_sandbox_service.py",
    ]
    test_result = subprocess.run([sys.executable, "-m", "pytest", "-q", *tests], cwd=ROOT, check=False)
    if test_result.returncode:
        return test_result.returncode
    return subprocess.run(
        [sys.executable, "scripts/packaged_preview_smoke.py", "--exe", args.exe, "--work-dir", args.work_dir, "--evidence-dir", args.evidence_dir],
        cwd=ROOT,
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
