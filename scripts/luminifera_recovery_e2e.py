"""Owner-observed recovery acceptance against the packaged Luminifera app."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

from luminifera_packaged_e2e import launch, stop


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", type=Path, default=Path("dist/Luminifera.exe"))
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args()
    args.work_dir = args.work_dir.resolve()
    args.exe = args.exe.resolve()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TEAM2050_PREVIEW_HOME"] = str(args.work_dir / "profile")
    result = {"checks": {}, "errors": [], "screens": []}
    process = None
    stop_marker = args.work_dir / "stop"
    try:
        with sync_playwright() as playwright:
            process, _api, app_url = launch(args.exe.resolve(), args.work_dir / "profile", args.work_dir / "launch.json", stop_marker)
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()
            auth_responses = []
            def record_auth(response):
                if "/api/auth/" in response.url:
                    try:
                        body = response.json()
                        if isinstance(body, dict):
                            body.pop("token", None)
                        auth_responses.append({"url": response.url, "status": response.status, "body": body})
                    except Exception:
                        auth_responses.append({"url": response.url, "status": response.status})
            page.on("response", record_auth)
            failed_resources = []
            page.on("response", lambda response: failed_resources.append({"url": response.url, "status": response.status}) if response.status >= 400 else None)
            page_errors = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.on("console", lambda message: page_errors.append("console: " + message.text) if message.type == "error" else None)
            page.goto(app_url, wait_until="networkidle", timeout=30_000)
            page.locator("#auth-form").wait_for(state="visible")
            page.wait_for_function("() => document.querySelector('#auth-gate')?.getAttribute('aria-busy') !== 'true' && !document.querySelector('#auth-account')?.disabled")
            if page.locator("#auth-name-label").is_hidden():
                page.locator("#auth-alt").click(force=True)
            page.locator("#auth-form").evaluate("form => { form.querySelector('#auth-account').value = 'recovery-owner@example.com'; form.querySelector('#auth-name').value = 'Recovery Owner'; form.querySelector('#auth-password').value = 'Recovery-pass-123'; }")
            result["form_values"] = page.locator("#auth-form").evaluate("form => ({account: form.querySelector('#auth-account').value, name: form.querySelector('#auth-name').value, passwordLength: form.querySelector('#auth-password').value.length, submit: form.querySelector('#auth-submit').textContent})")
            page.locator("#auth-form").dispatch_event("submit")
            page.wait_for_timeout(500)
            if page.locator("#auth-error").is_visible():
                result["errors"].append("signup_error: " + page.locator("#auth-error").inner_text())
            page.locator(".iris-panel").wait_for(state="visible", timeout=30_000)
            page.wait_for_timeout(1200)
            result["checks"]["signup_to_iris"] = not page.locator("#auth-gate").is_visible() and page.locator(".iris-panel").is_visible()
            onboarding = page.locator("#onboarding-start")
            if onboarding.is_visible():
                onboarding.click(force=True)
                page.locator(".onboarding-dialog").wait_for(state="detached", timeout=15_000)
            page.screenshot(path=str(args.work_dir / "iris-before.png"))
            page.locator("#iris-form").evaluate("form => { const input = form.querySelector('#iris-input'); input.value = 'Что ты умеешь?'; form.requestSubmit(); }")
            page.wait_for_function("() => document.querySelectorAll('#iris-chat .message').length >= 2", timeout=45_000)
            page.wait_for_timeout(500)
            result["checks"]["iris_message"] = page.locator("#iris-chat .message").count() >= 2
            page.screenshot(path=str(args.work_dir / "iris-after.png"))
            page.locator('nav [data-route="team"]').click(); page.locator('[data-screen="team"]').wait_for(state="visible")
            page.locator('.brand[data-route="home"]').click(); page.locator('[data-screen="home"]').wait_for(state="visible"); page.wait_for_timeout(900)
            result["checks"]["history_after_route_switch"] = page.locator("#iris-chat .message").count() >= 2
            page.reload(wait_until="networkidle"); page.locator("#auth-gate.auth-ready").wait_for(state="attached", timeout=30_000); page.locator('.brand[data-route="home"]').click(force=True); page.locator(".iris-panel").wait_for(state="visible", timeout=30_000); page.wait_for_timeout(900)
            result["checks"]["history_after_reload"] = page.locator("#iris-chat .message").count() >= 2
            page.locator("#profile-button").click(force=True); page.locator("#auth-logout").evaluate("async button => { if (typeof button.onclick !== 'function') throw new Error('logout_handler_missing'); await button.onclick(new Event('click')); }"); page.locator("#auth-gate").wait_for(state="visible", timeout=15_000)
            result["checks"]["logout"] = page.locator("#auth-gate").is_visible()
            page.reload(wait_until="networkidle"); page.locator("#auth-form").wait_for(state="visible"); page.wait_for_function("() => document.querySelector('#auth-gate')?.getAttribute('aria-busy') !== 'true'")
            page.locator("#auth-form").evaluate("form => { form.querySelector('#auth-account').value = 'recovery-owner@example.com'; form.querySelector('#auth-password').value = 'Recovery-pass-123'; }")
            page.locator("#auth-form").dispatch_event("submit"); page.locator(".iris-panel").wait_for(state="visible", timeout=30_000); page.locator('.brand[data-route="home"]').click(force=True); page.wait_for_timeout(2000)
            result["checks"]["history_after_relogin"] = page.locator("#iris-chat .message").count() >= 2
            result["relogin_chat_probe"] = page.evaluate("async () => { const base = window.LUMINIFERA_API_BASE || ''; const response = await fetch(`${base}/api/chat`, {headers: {Authorization: `Bearer ${localStorage.getItem('luminifera.authToken')}`}}); return {dom: document.querySelectorAll('#iris-chat .message').length, status: response.status, api: await response.json()}; }")
            page.locator('.brand[data-route="home"]').click(); page.locator(".viewport").hover(); before = page.evaluate("location.hash"); page.mouse.wheel(0, 700); page.wait_for_timeout(700)
            result["checks"]["wheel_does_not_switch_route"] = page.evaluate("location.hash") == before == "#home"
            result["screens"] = ["iris-before.png", "iris-after.png"]
            context.close(); browser.close()
    except Exception as exc:
        result["errors"].append(f"{type(exc).__name__}: {exc}")
    finally:
        if process is not None:
            stop(process, stop_marker)
    result["passed"] = not result["errors"] and all(result["checks"].values())
    result["auth_responses"] = locals().get("auth_responses", [])
    result["page_errors"] = locals().get("page_errors", [])
    result["failed_resources"] = locals().get("failed_resources", [])
    (args.work_dir / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
