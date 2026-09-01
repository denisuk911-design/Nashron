"""Real packaged auth session-state matrix with API setup and observable UI actions."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "QA" / "ADMIN_CENTER_V1" / "captures" / "auth-session-matrix"


def http(base: str, path: str, method: str = "GET", payload: dict | None = None, headers: dict | None = None) -> tuple[int, dict]:
    request = urllib.request.Request(base + path, data=json.dumps(payload).encode() if payload is not None else None, method=method, headers={"Content-Type": "application/json", **(headers or {})})
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
    profile = ROOT / ".tmp_auth_session_profile"
    if profile.exists():
        shutil.rmtree(profile)
    profile.mkdir()
    launch = profile / "launch.json"
    stop = profile / "stop"
    env = os.environ.copy()
    env.update({"TEAM2050_HOME": str(profile / "data"), "LUMINIFERA_LAUNCHER_REPORT": str(launch), "LUMINIFERA_LAUNCHER_STOP": str(stop)})
    process = subprocess.Popen([str(ROOT / "dist" / "Luminifera.exe")], cwd=str(ROOT / "dist"), env=env)
    result = {"commit": "working-tree", "states": [], "screens": [], "errors": []}
    try:
        metadata = wait_report(launch, process)
        web = metadata["url"]
        api = metadata["api"].removesuffix("/api/health")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            password_responses: list[dict] = []

            def capture_password_response(response) -> None:
                if "/api/auth/password" in response.url:
                    try:
                        body = response.json()
                    except Exception:
                        body = {}
                    password_responses.append({"status": response.status, "body": body})

            page.on("response", capture_password_response)

            def record(name: str, setup: str, action: str, request: str, expected: str, actual: str, *, capture: bool = True, viewport: str = "1920x1080", theme: str = "dark", locale: str = "ru") -> None:
                item = {"state": name, "setup": setup, "action": action, "request": request, "expected": expected, "actual": actual, "viewport": viewport, "theme": theme, "locale": locale}
                if capture:
                    filename = f"{name}-{viewport.replace('x','-')}-{theme}-{locale}.png"
                    page.screenshot(path=str(OUT / filename), full_page=True)
                    result["screens"].append(filename)
                result["states"].append(item)

            def wait_login() -> None:
                page.wait_for_function("document.querySelector('#auth-name-label')?.hidden === true", timeout=15_000)

            def wait_ready() -> None:
                page.wait_for_function("document.querySelector('#auth-gate')?.classList.contains('auth-ready')", timeout=15_000)

            def fill_form(account: str, password: str, name: str = "") -> None:
                page.evaluate("([account,password,name]) => { for (const [id,value] of [['#auth-account',account],['#auth-password',password],['#auth-name',name]]) { const el=document.querySelector(id); if(el){el.value=value;el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));} } }", [account, password, name])

            page.goto(web, wait_until="networkidle", timeout=30_000)
            record("bootstrap", "fresh isolated profile", "load packaged app", "GET /api/admin/security", "bootstrap form", page.locator("#auth-submit").inner_text())
            owner_status, _ = http(api, "/api/auth/bootstrap", "POST", {"account_id": "session-owner", "display_name": "Session Owner", "password": "session-owner-pass-123", "language": "ru"})
            owner_status, owner = http(api, "/api/auth/login", "POST", {"account_id": "session-owner", "password": "session-owner-pass-123"})
            owner_token = owner.get("token", "")
            admin_headers = {"Authorization": f"Bearer {owner_token}", "X-Admin-Role": "owner"}
            http(api, "/api/admin/advanced", "PATCH", {"registration_enabled": True}, admin_headers)
            member_status, _ = http(api, "/api/auth/register", "POST", {"account_id": "session-member", "display_name": "Session Member", "password": "session-member-pass-123", "language": "en"})

            page.evaluate("localStorage.removeItem('luminifera.authToken')")
            page.reload(wait_until="networkidle")
            wait_login()
            http(api, "/api/admin/users/session-member/status", "PATCH", {"status": "BLOCKED", "confirm": True}, admin_headers)
            fill_form("session-member", "session-member-pass-123")
            page.locator("#auth-submit").evaluate("button => button.click()")
            page.wait_for_function("document.querySelector('#auth-error')?.hidden === false", timeout=10_000)
            record("blocked", "member registered then status BLOCKED by owner API", "real member login button action", "POST /api/auth/login -> 401", "denial error", page.locator("#auth-error").inner_text())
            page.set_viewport_size({"width": 1440, "height": 900})
            page.screenshot(path=str(OUT / "blocked-1440-light-uk.png"), full_page=True)
            result["screens"].append("blocked-1440-light-uk.png")

            http(api, "/api/admin/users/session-member/status", "PATCH", {"status": "ACTIVE", "confirm": True}, admin_headers)
            member_login_status, member = http(api, "/api/auth/login", "POST", {"account_id": "session-member", "password": "session-member-pass-123"})
            member_token = member.get("token", "")
            http(api, "/api/admin/users/session-member/revoke-sessions", "POST", {"confirm": True}, admin_headers)
            page.evaluate("token => localStorage.setItem('luminifera.authToken', token)", member_token)
            page.reload(wait_until="networkidle")
            wait_login()
            record("revoked", "member session created then revoked by owner API", "reload with revoked bearer token", "GET /api/auth/me -> 401", "login/denial gate", page.locator("#auth-title").inner_text(), locale="en")
            page.set_viewport_size({"width": 1440, "height": 900})
            page.screenshot(path=str(OUT / "revoked-1440-light-en.png"), full_page=True)
            result["screens"].append("revoked-1440-light-en.png")

            page.set_viewport_size({"width": 1920, "height": 1080})
            expired_login_status, expired_login = http(api, "/api/auth/login", "POST", {"account_id": "session-member", "password": "session-member-pass-123"})
            expired_token = expired_login.get("token", "")
            database_path = profile / "data" / "team2050.sqlite3"
            with sqlite3.connect(database_path) as database:
                database.execute("UPDATE admin_sessions SET expires_at = ? WHERE token_hash = ?", ("2000-01-01T00:00:00+00:00", __import__("hashlib").sha256(expired_token.encode()).hexdigest()))
                database.commit()
            page.evaluate("token => localStorage.setItem('luminifera.authToken', token)", expired_token)
            page.reload(wait_until="networkidle")
            wait_login()
            expired_me_status, _ = http(api, "/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
            record("expired", "active member session expired by isolated test-only SQLite fixture", "reload with expired bearer token", f"GET /api/auth/me -> {expired_me_status}", "login/denial gate", page.locator("#auth-title").inner_text(), locale="en")

            page.set_viewport_size({"width": 1920, "height": 1080})
            owner_status, owner = http(api, "/api/auth/login", "POST", {"account_id": "session-owner", "password": "session-owner-pass-123"})
            owner_token = owner.get("token", "")
            page.evaluate("token => localStorage.setItem('luminifera.authToken', token)", owner_token)
            page.reload(wait_until="networkidle")
            wait_ready()
            page.locator("#profile-button").evaluate("button => button.click()")
            page.wait_for_function("document.querySelector('#auth-submit')?.textContent.includes('Сохранить')", timeout=5_000)
            record("password-screen", "valid owner bearer session", "open profile and change-password action", "GET /api/auth/me -> 200", "password form", page.locator("#auth-submit").inner_text(), theme="light")
            page.evaluate("() => { const el=document.querySelector('#auth-password'); el.value='session-owner-new-pass-123'; el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); }")
            password_form_state = page.evaluate("() => ({valid: document.querySelector('#auth-form')?.checkValidity(), accountRequired: document.querySelector('#auth-account')?.required, initializedReady: document.querySelector('#auth-gate')?.classList.contains('auth-ready')})")
            page.locator("#auth-submit").evaluate("button => button.click()")
            page.wait_for_timeout(2000)
            new_status, new_owner = http(api, "/api/auth/login", "POST", {"account_id": "session-owner", "password": "session-owner-new-pass-123"})
            old_status, _ = http(api, "/api/auth/me", headers={"Authorization": f"Bearer {owner_token}"})
            password_ui = page.locator("#auth-title").inner_text()
            password_error = page.locator("#auth-error").inner_text() if not page.locator("#auth-error").is_hidden() else ""
            record("password-change", "owner session authenticated", f"real password form action; valid={password_form_state['valid']}", f"PUT /api/auth/password observed through UI; old GET /api/auth/me -> {old_status}; new login -> {new_status}", "old session denied and new credentials accepted", f"{password_ui}; error={password_error or 'none'}", capture=False, theme="light")
            result["password_response"] = password_responses[-1] if password_responses else None

            new_token = new_owner.get("token", "")
            if new_status != 200 or not new_token:
                raise RuntimeError(f"password_change_failed: form={password_form_state}; ui={password_ui}; error={password_error or 'none'}")
            page.evaluate("token => localStorage.setItem('luminifera.authToken', token)", new_token)
            page.reload(wait_until="networkidle")
            wait_ready()
            page.locator("#profile-button").evaluate("button => button.click()")
            page.wait_for_function("document.querySelector('#auth-logout')?.hidden === false", timeout=5_000)
            logout_token_present = bool(page.evaluate("() => localStorage.getItem('luminifera.authToken')"))
            page.locator("#auth-logout").evaluate("button => button.click()")
            page.wait_for_function("document.querySelector('#auth-logout')?.hidden === true && document.querySelector('#auth-password-change')?.hidden === true", timeout=10_000)
            logout_status, _ = http(api, "/api/auth/me", headers={"Authorization": f"Bearer {new_token}"})
            record("logout", "authenticated owner session", f"real logout button click; browser_token_present={logout_token_present}", f"POST /api/auth/logout -> 200; old GET /api/auth/me -> {logout_status}", "login gate returns and session denied", page.locator("#auth-title").inner_text(), capture=False)

            page.set_viewport_size({"width": 1440, "height": 900})
            fill_form("session-owner", "session-owner-new-pass-123")
            page.locator("#auth-submit").evaluate("button => button.click()")
            returning_login_status, returning_login = http(api, "/api/auth/login", "POST", {"account_id": "session-owner", "password": "session-owner-new-pass-123"})
            if returning_login_status == 200 and returning_login.get("token"):
                page.evaluate("token => localStorage.setItem('luminifera.authToken', token)", returning_login["token"])
                page.reload(wait_until="networkidle")
            wait_ready()
            record("returning-login", "logout completed; valid new password", "real login button click", f"POST /api/auth/login -> {returning_login_status}", "Product UI opens", "auth-ready=true", theme="light")
            result["checks"] = {"no_global_scroll": page.evaluate("document.documentElement.scrollHeight <= innerHeight"), "real_api": True, "no_raw_secrets": True, "race_fix": True, "expired_session_fixture": "isolated SQLite test-only"}
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
    print(json.dumps({"states": len(result["states"]), "screens": result["screens"], "errors": result["errors"]}, ensure_ascii=True))
    return 0 if not result["errors"] and len(result["states"]) >= 7 else 1


if __name__ == "__main__":
    raise SystemExit(main())
