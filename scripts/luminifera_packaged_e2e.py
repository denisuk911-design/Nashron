"""Bounded E2E for the packaged Luminifera product shell and real API boundary."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def request(base: str, path: str, method: str = "GET", payload: dict | None = None, organization: str | None = None) -> dict | list:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if organization:
        headers["X-Organization-Id"] = organization
    req = urllib.request.Request(f"{base}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"http_{exc.code}:{method}:{path}:{exc.read().decode(errors='replace')[:300]}") from exc


def launch(exe: Path, profile: Path, report: Path, stop: Path) -> tuple[subprocess.Popen[bytes], str, str]:
    report.unlink(missing_ok=True)
    stop.unlink(missing_ok=True)
    environment = os.environ.copy()
    environment.update({"TEAM2050_HOME": str(profile), "LUMINIFERA_LAUNCHER_REPORT": str(report), "LUMINIFERA_LAUNCHER_STOP": str(stop)})
    process = subprocess.Popen([str(exe)], cwd=str(exe.parent), env=environment)
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline and not report.is_file():
        if process.poll() is not None:
            raise RuntimeError(f"packaged_exit:{process.returncode}")
        time.sleep(0.25)
    if not report.is_file():
        process.kill()
        raise TimeoutError("packaged_launcher_report_timeout")
    metadata = json.loads(report.read_text(encoding="utf-8"))
    api_health = str(metadata["api"])
    return process, api_health.removesuffix("/api/health"), str(metadata["url"])


def stop(process: subprocess.Popen[bytes], marker: Path) -> None:
    marker.write_text("stop", encoding="utf-8")
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", default=str(ROOT / "dist" / "Luminifera.exe"))
    parser.add_argument("--work-dir", default=str(ROOT / ".tmp_luminifera_packaged_e2e"))
    parser.add_argument("--report", default=str(ROOT / "QA" / "PHASE6_LUMINIFERA_PACKAGED_E2E.json"))
    args = parser.parse_args()
    exe, work, report = Path(args.exe).resolve(), Path(args.work_dir).resolve(), Path(args.report).resolve()
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    profile, launch_report, stop_marker = work / "profile", work / "launch.json", work / "stop"
    checks: dict[str, object] = {"exe": str(exe), "checks": {}, "errors": []}
    process = None
    try:
        process, api, web = launch(exe, profile, launch_report, stop_marker)
        checks["first_url"] = web
        checks["checks"]["health"] = request(api, "/api/health")
        team = request(api, "/api/teams", "POST", {"brief": "Packaged Luminifera product verification", "organization_name": "Packaged E2E", "team_size": "MINI"})
        organization = str(team["organization"]["organization_id"])
        checks["organization_id"] = organization
        headers_checks = checks["checks"]
        headers_checks["team_created"] = len(team["activation"]["employee_ids"]) >= 2
        headers_checks["iris_chat"] = bool(request(api, "/api/chat", "POST", {"content": "Коротко подтверди связь"}, organization).get("result"))
        goal = request(api, "/api/goals", "POST", {"objective": "Проверить packaged Goal execution"}, organization)
        headers_checks["goal_created"] = bool(goal.get("plan_id"))
        started = request(api, f"/api/goals/{goal['plan_id']}/start", "POST", organization=organization)
        headers_checks["goal_started"] = started.get("ok") is True and started.get("artifacts", 0) >= 1 and started.get("evidence", 0) >= 1
        work_state = request(api, "/api/work", organization=organization)
        headers_checks["work_state"] = isinstance(work_state, dict)
        headers_checks["review_state"] = isinstance(request(api, "/api/work/review", organization=organization), list)
        headers_checks["files_state"] = isinstance(request(api, "/api/files", organization=organization), list)
        settings = request(api, "/api/settings")
        changed = request(api, "/api/settings", "PATCH", {"interface_language": settings.get("interface_language", "ru"), "theme": settings.get("theme", "dark")})
        headers_checks["settings_persisted"] = changed.get("interface_language") == settings.get("interface_language", "ru")
        stop(process, stop_marker)
        process = None
        process, api2, web2 = launch(exe, profile, launch_report, stop_marker)
        checks["second_url"] = web2
        organizations = request(api2, "/api/organizations")
        headers_checks["restart_persistence"] = any(str(item.get("id")) == organization for item in organizations)
        checks["passed"] = all(bool(value) for value in headers_checks.values())
    except (OSError, RuntimeError, TimeoutError, urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
        checks["errors"].append(f"{type(exc).__name__}: {exc}")
        checks["passed"] = False
    finally:
        if process is not None:
            stop(process, stop_marker)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(checks, ensure_ascii=False))
    return 0 if checks.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
