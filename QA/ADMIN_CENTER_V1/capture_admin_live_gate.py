"""Capture the real owner center against a live Luminifera deployment."""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE = os.environ.get("LUMINIFERA_LIVE_URL", "https://nashron.onrender.com")
ACCOUNT = os.environ["LUMINIFERA_LIVE_ACCOUNT"]
PASSWORD = os.environ["LUMINIFERA_LIVE_PASSWORD"]
OUT = Path(__file__).resolve().parent / "captures" / "admin-live-gate"
TABS = ("dashboard", "analytics", "users", "providers", "plans", "audit", "security", "health", "advanced")
THEMES = tuple(item.strip() for item in os.environ.get("LUMINIFERA_LIVE_THEMES", "dark,light").split(",") if item.strip())


def api(path: str, method: str = "GET", payload: dict | None = None, headers: dict | None = None) -> dict | list:
    body = json.dumps(payload).encode() if payload is not None else None
    for attempt in range(3):
        request = urllib.request.Request(BASE + path, data=body, method=method, headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return json.loads(response.read().decode() or "{}")
        except urllib.error.HTTPError as error:
            if error.code not in {502, 503, 504} or attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {"base": BASE, "tabs": [], "errors": [], "checks": {}}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        try:
            try:
                login = api("/api/auth/login", "POST", {"account_id": ACCOUNT, "password": PASSWORD})
            except urllib.error.HTTPError as error:
                if error.code != 401:
                    raise
                api("/api/auth/bootstrap", "POST", {"account_id": ACCOUNT, "display_name": "Live Gate Owner", "password": PASSWORD, "language": "ru"})
                login = api("/api/auth/login", "POST", {"account_id": ACCOUNT, "password": PASSWORD})
            admin_headers = {"Authorization": f"Bearer {login['token']}"}
            # Build one real, isolated staging activity chain before reading the owner center.
            organizations = api("/api/organizations")
            if not organizations:
                organization = api("/api/organizations", "POST", {"name": "Luminifera Live Gate", "purpose": "Owner Center populated visual verification"})
                organization_id = str(organization["organization_id"])
                roles = api("/api/roles")
                role_ids = {str(item["id"]): item for item in roles}
                for display_name, role_id in (("Live Supervisor", "PROJECT_MANAGER"), ("Live Design Engineer", "DESIGN_ENGINEER"), ("Live Technical Reviewer", "QA_ENGINEER")):
                    if role_id in role_ids:
                        api(f"/api/organizations/{organization_id}/employees", "POST", {"display_name": display_name, "role_id": role_id, "description": "Live staging verification role", "provider_id": "GEMINI_CLI"})
                try:
                    goal = api("/api/goals", "POST", {"objective": "Live owner center evidence verification"}, {"X-Organization-Id": organization_id})
                    api(f"/api/goals/{goal['plan_id']}/start", "POST", None, {"X-Organization-Id": organization_id})
                except urllib.error.HTTPError:
                    pass
                telemetry_headers = {"X-Organization-Id": organization_id, "X-Account-Id": ACCOUNT}
                for event_type in ("visit", "registration", "login", "session_started", "iris_opened", "constellation_opened", "goal_created", "runtime_execution", "evidence_created", "error", "fallback", "feedback_submitted"):
                    api("/api/telemetry", "POST", {"event_type": event_type, "user_id": ACCOUNT, "detail": {"source": "live-admin-gate", "observed": "staging workflow"}}, telemetry_headers)
                api("/api/usage", "POST", {"account_id": ACCOUNT, "provider_id": "GEMINI_CLI", "organization_id": organization_id, "model_id": "gemini-3.5-flash-lite", "runtime": "NATIVE", "input_tokens": 0, "output_tokens": 0, "latency_ms": 4200, "fallback": True, "cost_status": "unavailable"}, {"X-Account-Id": ACCOUNT})
            page.goto(BASE + "/app?phase=auth-gate", wait_until="networkidle", timeout=60_000)
            page.evaluate("token => localStorage.setItem('luminifera.authToken', token)", login["token"])
            page.reload(wait_until="networkidle", timeout=60_000)
            page.wait_for_timeout(2_000)
            if not page.evaluate("document.querySelector('#auth-gate')?.classList.contains('auth-ready')"):
                page.screenshot(path=str(OUT / "auth-debug.png"), full_page=False)
                token_present = page.evaluate("Boolean(localStorage.getItem('luminifera.authToken'))")
                title = page.locator("#auth-title").inner_text() if page.locator("#auth-title").count() else "missing"
                raise RuntimeError(f"auth_gate_not_ready: token_present={token_present}; title={title}")
            page.evaluate("document.querySelector('.onboarding-dialog')?.close()")
            for theme in THEMES:
                api("/api/settings", "PATCH", {"theme": theme})
                page.reload(wait_until="networkidle", timeout=60_000)
                page.wait_for_function("document.querySelector('#auth-gate')?.classList.contains('auth-ready')", timeout=20_000)
                page.evaluate("document.querySelector('.onboarding-dialog')?.close()")
                for viewport in ((1920, 1080), (1440, 900)):
                    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
                    page.locator("#admin-entry").click()
                    page.wait_for_function("document.querySelector('.admin-dialog')?.open === true", timeout=10_000)
                    for tab in TABS:
                        page.locator(f"[data-admin-tab='{tab}']").click()
                        page.wait_for_timeout(500)
                        page.wait_for_function("document.querySelector('#admin-content')?.textContent.trim().length > 0 && !document.querySelector('#admin-content')?.textContent.includes('Загрузка')", timeout=15_000)
                        filename = f"{tab}-{viewport[0]}-{viewport[1]}-{theme}.png"
                        page.screenshot(path=str(OUT / filename), full_page=False)
                        text = page.locator(".admin-dialog").inner_text()
                        manifest["tabs"].append({"tab": tab, "viewport": f"{viewport[0]}x{viewport[1]}", "theme": theme, "png": filename, "text_length": len(text)})
                    page.locator(".admin-close").click()
                    page.wait_for_function("document.querySelector('.admin-dialog')?.open !== true", timeout=5_000)
                page.set_viewport_size({"width": 1920, "height": 1080})
            dashboard = api("/api/admin/dashboard?period=30d", headers=admin_headers)
            users = api("/api/admin/users", headers=admin_headers)
            providers = api("/api/admin/providers", headers=admin_headers)
            manifest["live_data"] = {
                "dashboard_counts": dashboard.get("counts", {}),
                "activation": dashboard.get("activation", []),
                "users": len(users),
                "provider_statuses": [{"name": item.get("name"), "health": item.get("health"), "configured": item.get("credential_saved")} for item in providers],
                "source": dashboard.get("source"),
            }
            manifest["checks"] = {
                "no_global_scroll": page.evaluate("document.documentElement.scrollHeight <= innerHeight"),
                "no_white_native_ui": page.evaluate("![...document.querySelectorAll('dialog')].some(d => d.open && getComputedStyle(d).backgroundColor === 'rgb(255, 255, 255)')"),
                "no_raw_internal_copy": not bool(re.search(r"ADVISORY_BOARD|provider_id|runtime_id|organization_id", page.locator("body").inner_text(), re.I)),
            }
        except Exception as error:
            manifest["errors"].append(f"{type(error).__name__}: {error}")
        finally:
            context.close()
            browser.close()
    captured = []
    for path in sorted(OUT.glob("*.png")):
        match = re.fullmatch(r"(.+)-(\d+)-(\d+)-(dark|light)\.png", path.name)
        if match:
            captured.append({"png": path.name, "tab": match.group(1), "viewport": f"{match.group(2)}x{match.group(3)}", "theme": match.group(4)})
    manifest["all_captures"] = captured
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"tabs": len(manifest["tabs"]), "errors": manifest["errors"], "checks": manifest["checks"]}, ensure_ascii=True))
    return 0 if not manifest["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
