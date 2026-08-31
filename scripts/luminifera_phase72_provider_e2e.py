"""Packaged provider selection/status smoke without reading or overwriting secrets."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from luminifera_packaged_e2e import launch, request, stop

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    work = ROOT / ".tmp_luminifera_phase72_provider"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    result = {"checks": {}, "errors": [], "configured_provider_count": None}
    process = None
    try:
        process, api, _web = launch(ROOT / "dist" / "Luminifera.exe", work / "profile", work / "launch.json", work / "stop")
        providers = request(api, "/api/providers")
        result["configured_provider_count"] = sum(bool(item.get("configured")) for item in providers)
        result["checks"]["provider_catalog_is_real"] = bool(providers) and all("id" in item and "state" in item for item in providers)
        for provider in providers:
            checked = request(api, f"/api/providers/{provider['id']}/check", "POST")
            result["checks"][f"check_{provider['id']}"] = checked.get("id") == provider["id"] and "state" in checked
        if providers:
            selected = providers[0]
            saved = request(api, "/api/settings", "PATCH", {"active_provider_id": selected["id"], "active_model_id": selected.get("model_id", "")})
            result["checks"]["selection_saved"] = saved.get("active_provider_id") == selected["id"]
        stop(process, work / "stop")
        process = None
        process, api, _web = launch(ROOT / "dist" / "Luminifera.exe", work / "profile", work / "launch-restart.json", work / "stop-restart")
        settings = request(api, "/api/settings")
        result["checks"]["selection_survives_restart"] = bool(settings.get("active_provider_id"))
        result["checks"]["fallback_is_explicit"] = all(item.get("state") in {"Ready", "Login required", "Unavailable", "Busy", "Error"} for item in providers)
        result["passed"] = all(result["checks"].values())
    except Exception as exc:
        result["errors"].append(f"{type(exc).__name__}: {exc}")
        result["passed"] = False
    finally:
        if process is not None:
            stop(process, work / "stop-final")
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
