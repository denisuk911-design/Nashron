"""Minimal live OpenAI packaged E2E; never prints credential material."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from luminifera_packaged_e2e import launch, request, stop

ROOT = Path(__file__).resolve().parents[1]


def run_live(work: Path) -> dict[str, object]:
    process = None
    try:
        process, api, _web = launch(ROOT / "dist" / "Luminifera.exe", work / "profile", work / "launch.json", work / "stop")
        providers = request(api, "/api/providers")
        openai = next((item for item in providers if item.get("id") == "OPENAI_API"), None)
        if not openai or not openai.get("configured"):
            return {"status": "BLOCKED", "reason": "OPENAI_API credential is not configured", "secret_leaks": False}
        saved = request(api, "/api/settings", "PATCH", {"active_provider_id": "OPENAI_API", "active_model_id": "gpt-4o-mini"})
        team = request(api, "/api/teams", "POST", {"brief": "Minimal live OpenAI provider route verification", "organization_name": "Luminifera live provider gate", "team_size": "MINI"})
        organization = str(team["organization"]["organization_id"])
        result = request(api, "/api/executions", "POST", {"objective": "Return a short WORK classification for this provider route.", "policy": "direct_action", "preferred_runtime": "openai-agents"}, organization)
        return {"status": "PASS" if result.get("runtime_id") == "openai-agents" and result.get("ok") else "FAIL", "provider": openai["id"], "model_selected": saved.get("active_model_id"), "runtime_id": result.get("runtime_id"), "ok": result.get("ok"), "artifact_count": len(result.get("artifacts", [])), "evidence_count": len(result.get("evidence", [])), "organization_scoped": result.get("organization_id") == organization, "secret_leaks": False}
    finally:
        if process is not None:
            stop(process, work / "stop-final")


def run_no_credential(work: Path) -> dict[str, object]:
    process = None
    try:
        os.environ["TEAM2050_TEST_CREDENTIAL_STORE"] = str(work / "isolated-credentials.json")
        process, api, _web = launch(ROOT / "dist" / "Luminifera.exe", work / "profile", work / "launch.json", work / "stop")
        team = request(api, "/api/teams", "POST", {"brief": "No credential fallback verification", "organization_name": "Luminifera isolated fallback", "team_size": "MINI"})
        organization = str(team["organization"]["organization_id"])
        result = request(api, "/api/executions", "POST", {"objective": "Return a short WORK classification without credentials.", "policy": "direct_action", "preferred_runtime": "openai-agents"}, organization)
        data = result.get("data") or {}
        return {"status": "PASS" if result.get("runtime_id") == "native" and data.get("fallback_from") == "openai-agents" else "FAIL", "runtime_id": result.get("runtime_id"), "fallback_from": data.get("fallback_from"), "secret_leaks": False}
    finally:
        if process is not None:
            stop(process, work / "stop-final")


def main() -> int:
    work = ROOT / ".tmp_luminifera_phase74_live"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    result = {"live": {}, "fallback": {}}
    try:
        os.environ.pop("TEAM2050_TEST_CREDENTIAL_STORE", None)
        result["live"] = run_live(work / "live")
        result["fallback"] = run_no_credential(work / "fallback")
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["passed"] = result.get("live", {}).get("status") == "PASS" and result.get("fallback", {}).get("status") == "PASS"
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
