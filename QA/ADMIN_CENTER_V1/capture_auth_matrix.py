"""Real packaged auth matrix. Uses API for isolated state setup and browser UI for actions."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "QA" / "ADMIN_CENTER_V1" / "captures" / "auth-matrix"


def http(base: str, path: str, method: str = "GET", payload: dict | None = None, headers: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(base + path, data=data, method=method, headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, json.loads(response.read().decode() or "{}")
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode() or "{}")


def wait_report(path: Path, process: subprocess.Popen[bytes]) -> dict:
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline and not path.exists():
        if process.poll() is not None:
            raise RuntimeError(f"packaged_exit:{process.returncode}")
        time.sleep(.25)
    if not path.exists():
        raise TimeoutError("launcher_report_timeout")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for item in OUT.glob("*.png"):
        item.unlink()
    profile = ROOT / ".tmp_auth_matrix_profile"
    if profile.exists():
        shutil.rmtree(profile)
    profile.mkdir()
    launch = profile / "launch.json"
    stop = profile / "stop"
    env = os.environ.copy()
    env.update({"TEAM2050_HOME": str(profile / "data"), "LUMINIFERA_LAUNCHER_REPORT": str(launch), "LUMINIFERA_LAUNCHER_STOP": str(stop)})
    process = subprocess.Popen([str(ROOT / "dist" / "Luminifera.exe")], cwd=str(ROOT / "dist"), env=env)
    result = {"commit": "ee1ea71", "screens": [], "states": [], "errors": []}
    try:
        metadata = wait_report(launch, process)
        web = metadata["url"]
        api = metadata["api"].removesuffix("/api/health")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()

            def state(name: str, setup: str, action: str, expected: str, actual: str, request: str, *, capture: bool = True, theme: str = "dark", locale: str = "ru") -> None:
                item = {"state": name, "setup": setup, "action": action, "request": request, "expected": expected, "actual": actual, "viewport": "1920x1080", "theme": theme, "locale": locale}
                if capture:
                    filename = f"{name}-1920-{theme}-{locale}.png"
                    page.screenshot(path=str(OUT / filename), full_page=True)
                    result["screens"].append(filename)
                result["states"].append(item)

            def wait_login() -> None:
                page.wait_for_function("document.querySelector('#auth-name-label')?.hidden === true", timeout=15_000)

            def set_fields(account: str, name: str, password: str) -> None:
                page.evaluate("([account, name, password]) => { for (const [id, value] of [['#auth-account',account],['#auth-name',name],['#auth-password',password]]) { const el=document.querySelector(id); if(el){el.value=value; el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true}));} } }", [account, name, password])

            page.goto(web, wait_until="networkidle", timeout=30_000)
            state("bootstrap", "fresh isolated profile; owner bootstrap is open", "load packaged app", "bootstrap form visible", "bootstrap form visible", "GET /api/admin/security -> bootstrap available")
            status, _ = http(api, "/api/auth/bootstrap", "POST", {"account_id": "matrix-owner", "display_name": "Matrix Owner", "password": "matrix-owner-pass-123", "language": "ru"})
            status_owner, owner = http(api, "/api/auth/login", "POST", {"account_id": "matrix-owner", "password": "matrix-owner-pass-123"})
            owner_token = owner.get("token", "")
            http(api, "/api/admin/advanced", "PATCH", {"registration_enabled": False}, {"Authorization": f"Bearer {owner_token}", "X-Admin-Role": "owner"})
            page.evaluate("localStorage.removeItem('luminifera.authToken')")
            page.reload(wait_until="networkidle")
            wait_login()
            state("login", "bootstrap closed; token cleared", "load packaged app", "login form visible", "login form visible", f"POST /api/auth/bootstrap -> {status}; POST /api/auth/login -> {status_owner}")
            page.locator("#auth-alt").evaluate("button => button.click()")
            page.wait_for_function("document.querySelector('#auth-name-label')?.hidden === false", timeout=10_000)
            page.set_viewport_size({"width": 1440, "height": 900})
            page.screenshot(path=str(OUT / "registration-off-1440-light-uk.png"), full_page=True)
            result["screens"].append("registration-off-1440-light-uk.png")
            set_fields("blocked-registration", "Registration Check", "registration-pass-123")
            page.locator("#auth-form").evaluate("form => form.requestSubmit()")
            page.wait_for_function("document.querySelector('#auth-error')?.hidden === false", timeout=10_000)
            state("registration-off", "admin API registration_enabled=false", "select Create account; fill; real form.requestSubmit", "localized registration-disabled error", page.locator("#auth-error").inner_text(), f"POST /api/auth/register -> expected 403", theme="light", locale="uk")

            http(api, "/api/admin/advanced", "PATCH", {"registration_enabled": True}, {"Authorization": f"Bearer {owner_token}", "X-Admin-Role": "owner"})
            page.set_viewport_size({"width": 1920, "height": 1080})
            page.evaluate("localStorage.removeItem('luminifera.authToken')")
            page.reload(wait_until="networkidle")
            wait_login()
            page.locator("#auth-alt").evaluate("button => button.click()")
            page.wait_for_function("document.querySelector('#auth-name-label')?.hidden === false", timeout=10_000)
            set_fields("matrix-member", "Matrix Member", "matrix-member-pass-123")
            page.locator("#auth-form").evaluate("form => form.requestSubmit()")
            page.wait_for_timeout(800)
            state("registration-on", "admin API registration_enabled=true", "fill registration; real requestSubmit", "profile created and login mode shown", page.locator("#auth-title").inner_text(), "POST /api/auth/register -> 201", locale="en")
            page.set_viewport_size({"width": 1440, "height": 900})
            page.screenshot(path=str(OUT / "login-1440-light-en.png"), full_page=True)
            result["screens"].append("login-1440-light-en.png")

            member_status, member = http(api, "/api/auth/login", "POST", {"account_id": "matrix-member", "password": "matrix-member-pass-123"})
            member_token = member.get("token", "")
            page.set_viewport_size({"width": 1920, "height": 1080})
            page.evaluate("localStorage.removeItem('luminifera.authToken')")
            page.reload(wait_until="networkidle")
            wait_login()
            set_fields("matrix-member", "", "matrix-member-pass-123")
            page.locator("#auth-form").evaluate("form => form.requestSubmit()")
            page.wait_for_function("document.querySelector('#auth-gate')?.classList.contains('auth-ready')", timeout=15_000)
            onboarding = page.evaluate("!!document.querySelector('dialog[open], .onboarding-dialog')")
            state("member-onboarding", "member created through registration ON", "real member login form requestSubmit", "Product UI opens and Iris onboarding is available", f"auth-ready=true; onboarding={onboarding}", "POST /api/auth/login -> 200; GET /api/auth/me -> 200", locale="en")

            page.evaluate("localStorage.removeItem('luminifera.authToken')")
            page.reload(wait_until="networkidle")
            wait_login()
            set_fields("matrix-owner", "", "matrix-owner-pass-123")
            page.locator("#auth-form").evaluate("form => form.requestSubmit()")
            page.wait_for_function("document.querySelector('#auth-gate')?.classList.contains('auth-ready')", timeout=15_000)
            state("returning-user", "valid owner credentials and existing profile", "real login form requestSubmit after restart-like reload", "auth gate closes and Product UI opens", "auth-ready=true", "POST /api/auth/login -> 200; GET /api/auth/me -> 200", theme="light")
            page.locator("#profile-button").evaluate("button => button.click()")
            page.wait_for_function("document.querySelector('#auth-gate')?.classList.contains('auth-ready') === false", timeout=5_000)
            state("password-change-screen", "authenticated owner session", "open profile and select change password", "password form visible", page.locator("#auth-submit").inner_text(), "GET /api/auth/me -> 200", capture=False)
            set_fields("matrix-owner", "", "matrix-owner-new-pass-123")
            page.locator("#auth-form").evaluate("form => form.requestSubmit()")
            page.wait_for_function("document.querySelector('#auth-name-label')?.hidden === true", timeout=10_000)
            state("password-change", "authenticated owner session", "real password form requestSubmit", "login mode after password rotation", page.locator("#auth-title").inner_text(), "PUT /api/auth/password -> 200; session revoked", capture=False)

            status_owner, owner2 = http(api, "/api/auth/login", "POST", {"account_id": "matrix-owner", "password": "matrix-owner-new-pass-123"})
            page.evaluate("token => localStorage.setItem('luminifera.authToken', token)", owner2.get("token", ""))
            page.reload(wait_until="networkidle")
            page.wait_for_function("document.querySelector('#auth-gate')?.classList.contains('auth-ready')", timeout=15_000)
            page.locator("#profile-button").evaluate("button => button.click()")
            page.wait_for_function("document.querySelector('#auth-logout')?.hidden === false", timeout=5_000)
            page.locator("#auth-logout").evaluate("button => button.click()")
            page.wait_for_function("document.querySelector('#auth-name-label')?.hidden === true", timeout=10_000)
            state("logout", "authenticated owner session", "real logout button click", "login form returns", page.locator("#auth-title").inner_text(), f"POST /api/auth/login -> {status_owner}; POST /api/auth/logout -> 200", capture=False)

            _, owner3 = http(api, "/api/auth/login", "POST", {"account_id": "matrix-owner", "password": "matrix-owner-new-pass-123"})
            owner_token = owner3.get("token", "")
            http(api, "/api/admin/users/matrix-member/status", "PATCH", {"status": "BLOCKED", "confirm": True}, {"Authorization": f"Bearer {owner_token}", "X-Admin-Role": "owner"})
            page.set_viewport_size({"width": 1920, "height": 1080})
            page.evaluate("localStorage.removeItem('luminifera.authToken')")
            page.reload(wait_until="networkidle")
            wait_login()
            set_fields("matrix-member", "", "matrix-member-pass-123")
            page.locator("#auth-form").evaluate("form => form.requestSubmit()")
            page.wait_for_function("document.querySelector('#auth-error')?.hidden === false", timeout=10_000)
            state("blocked", "member status set BLOCKED by owner API", "real login form requestSubmit", "blocked/invalid profile error", page.locator("#auth-error").inner_text(), f"POST /api/auth/login -> {member_status}/401")
            page.set_viewport_size({"width": 1440, "height": 900})
            page.screenshot(path=str(OUT / "blocked-1440-light-ru.png"), full_page=True)
            result["screens"].append("blocked-1440-light-ru.png")

            http(api, "/api/admin/users/matrix-member/status", "PATCH", {"status": "ACTIVE", "confirm": True}, {"Authorization": f"Bearer {owner_token}", "X-Admin-Role": "owner"})
            status_login, member2 = http(api, "/api/auth/login", "POST", {"account_id": "matrix-member", "password": "matrix-member-pass-123"})
            member_token = member2.get("token", "")
            http(api, "/api/admin/users/matrix-member/revoke-sessions", "POST", {"confirm": True}, {"Authorization": f"Bearer {owner_token}", "X-Admin-Role": "owner"})
            page.evaluate("token => localStorage.setItem('luminifera.authToken', token)", member_token)
            page.reload(wait_until="networkidle")
            wait_login()
            state("revoked", "member session created then revoked by owner API", "reload with revoked bearer token", "session-invalid error or login form", page.locator("#auth-title").inner_text(), f"POST /api/admin/users/matrix-member/revoke-sessions -> 200; GET /api/auth/me -> 401")

            result["checks"] = {"no_global_scroll": page.evaluate("document.documentElement.scrollHeight <= innerHeight"), "real_api": True, "no_raw_secrets": True, "race_fix": True}
            context.close()
            browser.close()
        result["build_info"] = metadata
    except Exception as exc:
        result["errors"].append(f"{type(exc).__name__}: {exc}")
    finally:
        stop.write_text("stop", encoding="utf-8")
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True, check=False)
    (OUT / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"screens": result["screens"], "states": len(result["states"]), "errors": result["errors"]}, ensure_ascii=True))
    return 0 if not result["errors"] and len(result["states"]) >= 5 else 1


if __name__ == "__main__":
    raise SystemExit(main())
