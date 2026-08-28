from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _count_rows(database: Path, table: str) -> int:
    if not database.is_file():
        return 0
    with sqlite3.connect(database) as connection:
        return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def main() -> int:
    parser = argparse.ArgumentParser(description="Create and verify an isolated clean Team2050 Test Build.")
    parser.add_argument("--source", default=str(ROOT / "dist" / "Team2050"))
    parser.add_argument("--output", default=str(ROOT / "dist" / "Team2050-TestBuild"))
    parser.add_argument("--profile", default=str(ROOT / ".tmp_team2050_testbuild" / "profile"))
    parser.add_argument("--evidence-dir", default=str(ROOT / "QA" / "Task068"))
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()

    source = Path(args.source).resolve()
    output = Path(args.output).resolve()
    profile = Path(args.profile).resolve()
    evidence_dir = Path(args.evidence_dir).resolve()
    exe = output / "Team2050.exe"
    if not (source / "Team2050.exe").is_file():
        payload = {"checks_passed": False, "error": "source_exe_not_found"}
        print(json.dumps(payload, ensure_ascii=False))
        return 2
    for path in (output, profile):
        if path.exists():
            shutil.rmtree(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    profile.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, output)
    initial_profile_absent = not profile.exists()

    launches: list[dict[str, object]] = []
    for name in ("first_run", "restart"):
        report = profile.parent / f"{name}.json"
        environment = os.environ.copy()
        environment.update({"TEAM2050_HOME": str(profile)})
        if name == "first_run":
            environment.update({"TEAM2050_SUPERVISOR_E2E_SMOKE": "1", "TEAM2050_SUPERVISOR_E2E_SMOKE_REPORT": str(report)})
        else:
            environment.update({"TEAM2050_TEST_BUILD_RESTART_SMOKE": "1", "TEAM2050_TEST_BUILD_RESTART_REPORT": str(report)})
        completed = subprocess.run([str(exe)], cwd=str(output), env=environment, timeout=args.timeout, check=False)
        if not report.is_file():
            payload = {"checks_passed": False, "error": f"missing_{name}_report", "returncode": completed.returncode}
            print(json.dumps(payload, ensure_ascii=False))
            return 1
        result = json.loads(report.read_text(encoding="utf-8"))
        result["returncode"] = completed.returncode
        launches.append(result)

    database = profile / "team2050.sqlite3"
    model_manifest = output / "_internal" / "vendor" / "local_supervisor" / "MODEL_MANIFEST.json"
    worker = output / "Team2050LocalWorker.exe"
    build_info = output / "_internal" / "data" / "build_info.json"
    manifest_ok = model_manifest.is_file() and worker.is_file()
    version = json.loads(build_info.read_text(encoding="utf-8")) if build_info.is_file() else {}
    checks_passed = (
        initial_profile_absent
        and exe.is_file()
        and manifest_ok
        and len(launches) == 2
        and all(item.get("checks_passed") is True and item.get("returncode") == 0 for item in launches)
        and _count_rows(database, "organizations") >= 1
        and _count_rows(database, "project_plans") >= 1
    )
    payload = {
        "checks_passed": checks_passed,
        "build": {"exe": str(exe), "version": version, "profile": str(profile)},
        "clean_first_run": {"profile_absent_before_launch": initial_profile_absent, "organizations_before_launch": 0, "employees_before_launch": 0},
        "launches": launches,
        "persistence": {"database": str(database), "organizations": _count_rows(database, "organizations"), "project_plans": _count_rows(database, "project_plans")},
        "bundled_local_level1": {"worker": str(worker), "model_manifest": str(model_manifest), "present": manifest_ok},
    }
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "test_build.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0 if checks_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
