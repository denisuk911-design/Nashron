from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.beta_recovery_service import BetaRecoveryService, SimulatedUpdateCrash


def _run(exe: Path, profile: Path, report: Path) -> dict:
    env = os.environ.copy()
    env.update(
        {
            "TEAM2050_PREVIEW": "1",
            "TEAM2050_PREVIEW_HOME": str(profile),
            "TEAM2050_PREVIEW_SMOKE": "1",
            "TEAM2050_PREVIEW_SMOKE_DEMO": "1",
            "TEAM2050_PREVIEW_SMOKE_REPORT": str(report),
        }
    )
    result = subprocess.run([str(exe)], cwd=str(exe.parent), env=env, timeout=60, check=False)
    if not report.is_file():
        return {"returncode": result.returncode, "report": "missing"}
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["returncode"] = result.returncode
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Beta install, update, restart and uninstall without losing the profile.")
    parser.add_argument("--source", default=str(ROOT / "dist" / "Team2050"))
    parser.add_argument("--work-dir", default=str(ROOT / ".tmp_beta_install_smoke"))
    parser.add_argument("--evidence", default=str(ROOT / "QA" / "Task057" / "beta_install_smoke.json"))
    args = parser.parse_args()
    source = Path(args.source).resolve()
    work = Path(args.work_dir).resolve()
    install = work / "install" / "Team2050"
    profile = work / "profile"
    legacy = work / "legacy-Roman2050"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    legacy.mkdir()

    # Clean install: only the versioned application directory is copied; the profile starts empty.
    install.parent.mkdir(parents=True)
    shutil.copytree(source, install)
    manifest_v1 = {"product": "Team2050", "channel": "beta", "version": "2.6.0-beta.1"}
    (install / "team2050-release.json").write_text(json.dumps(manifest_v1, indent=2), encoding="utf-8")
    first = _run(install / "Team2050.exe", profile, work / "first.json")

    # A crash after copying files must be recoverable from the rollback snapshot.
    update_stage = work / "update-stage"
    shutil.copytree(source, update_stage)
    manifest_v2 = {"product": "Team2050", "channel": "beta", "version": "2.6.0-beta.2"}
    recovery = BetaRecoveryService(install)
    try:
        recovery.update(update_stage, manifest_v2["version"], simulate_crash=True)
    except SimulatedUpdateCrash:
        pass
    recovered = recovery.recover()
    manifest_after_recovery = json.loads((install / "team2050-release.json").read_text(encoding="utf-8"))
    rollback_ok = recovered and manifest_after_recovery.get("version") == manifest_v1["version"]
    recovery.update(update_stage, manifest_v2["version"])
    second = _run(install / "Team2050.exe", profile, work / "second.json")
    restarted = _run(install / "Team2050.exe", profile, work / "restart.json")
    profile_database = profile / "team2050.sqlite3"
    profile_settings = profile / "data" / "app_settings.json"
    profile_before_uninstall = profile_database.is_file() and profile_settings.is_file()
    support_bundle = recovery.create_support_bundle(profile, work / "support-bundle.zip")
    with zipfile.ZipFile(support_bundle) as bundle:
        support_report = json.loads(bundle.read("support-report.json").decode("utf-8"))
    support_text = json.dumps(support_report, ensure_ascii=False)

    # Uninstall removes the application bundle only. User data is deliberately retained.
    shutil.rmtree(install)
    payload = {
        "install": first,
        "update": second,
        "restart": restarted,
        "versions": [manifest_v1["version"], manifest_v2["version"]],
        "install_removed": not install.exists(),
        "profile_preserved": profile_before_uninstall and profile_database.is_file() and profile_settings.is_file(),
        "legacy_not_imported": not (profile / "Roman2050.sqlite3").exists() and legacy.is_dir(),
        "rollback_after_failed_update": rollback_ok,
        "support_bundle": str(support_bundle),
        "support_bundle_secret_free": support_report.get("secrets_included") is False and not any(
            marker in support_text for marker in ("AQ.", "ghp_", "sk-", "BEGIN PRIVATE KEY")
        ),
        "legacy_path": str(legacy),
    }
    payload["checks_passed"] = (
        all(item.get("checks_passed") is True and item.get("returncode") == 0 for item in (first, second, restarted))
        and first.get("database_name") == "team2050.sqlite3"
        and second.get("database_name") == "team2050.sqlite3"
        and restarted.get("database_name") == "team2050.sqlite3"
        and first.get("user_avatar_path") == second.get("user_avatar_path") == restarted.get("user_avatar_path")
        and payload["install_removed"]
        and payload["profile_preserved"]
        and payload["legacy_not_imported"]
        and payload["rollback_after_failed_update"]
        and payload["support_bundle_secret_free"]
    )
    evidence = Path(args.evidence).resolve()
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
