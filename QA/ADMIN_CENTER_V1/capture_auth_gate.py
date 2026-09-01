"""Capture and probe the real Luminifera auth gate without fake backend data."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "QA" / "ADMIN_CENTER_V1" / "captures" / "auth-final"


def wait_for_report(report: Path, process: subprocess.Popen[bytes]) -> dict:
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline and not report.exists():
        if process.poll() is not None:
            raise RuntimeError(f"packaged_exit:{process.returncode}")
        time.sleep(0.25)
    if not report.exists():
        raise TimeoutError("launcher_report_timeout")
    return json.loads(report.read_text(encoding="utf-8"))


def request_json(url: str, payload: dict, method: str = "POST", headers: dict | None = None) -> dict:
    request_headers = {"Content-Type": "application/json", **(headers or {})}
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=request_headers, method=method)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode())


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for item in OUT.glob("*.png"):
        item.unlink()
    result = {"screens": [], "checks": {}, "errors": []}
    package_root = ROOT / ".tmp_auth_visual_profile"
    if package_root.exists():
        shutil.rmtree(package_root)
    package_root.mkdir()
    report = package_root / "launch.json"
    stop = package_root / "stop"
    env = os.environ.copy()
    env.update({"TEAM2050_HOME": str(package_root / "profile"), "LUMINIFERA_LAUNCHER_REPORT": str(report), "LUMINIFERA_LAUNCHER_STOP": str(stop)})
    process = subprocess.Popen([str(ROOT / "dist" / "Luminifera.exe")], cwd=str(ROOT / "dist"), env=env)
    try:
        metadata = wait_for_report(report, process)
        app_url = metadata["url"]
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            context.add_init_script("""() => {
                window.__authTrace = [];
                document.addEventListener('submit', event => window.__authTrace.push({type:'submit', defaultPrevented:event.defaultPrevented, target:event.target?.id || null}), true);
                const originalFetch = window.fetch;
                window.fetch = async (...args) => {
                    const url = String(args[0]?.url || args[0] || '');
                    const response = await originalFetch(...args);
                    if (url.includes('/api/auth/') || url.includes('/api/admin/security')) {
                        const body = await response.clone().text().catch(() => '');
                        window.__authTrace.push({type:'fetch', url, status:response.status, body:body.slice(0,240)});
                    }
                    return response;
                };
                new MutationObserver(() => {
                    const error = document.querySelector('#auth-error');
                    if (error) window.__authTrace.push({type:'error-dom', hidden:error.hidden, display:getComputedStyle(error).display, text:error.textContent});
                }).observe(document, {subtree:true, childList:true, attributes:true, attributeFilter:['hidden','class','style']});
            }""")
            page = context.new_page()
            network_trace = []
            page.on("request", lambda request: network_trace.append({"type": "request", "method": request.method, "url": request.url}) if "/api/" in request.url else None)
            page.on("response", lambda response: network_trace.append({"type": "response", "status": response.status, "url": response.url}) if "/api/" in response.url else None)
            page.on("console", lambda message: network_trace.append({"type": "console", "level": message.type, "text": message.text}))
            page.on("pageerror", lambda error: network_trace.append({"type": "pageerror", "text": str(error)}))
            page.goto(app_url, wait_until="networkidle", timeout=30_000)
            page.screenshot(path=str(OUT / "bootstrap-1920.png"), full_page=True)
            result["screens"].append("bootstrap-1920.png")
            result["checks"]["bootstrap_visible"] = page.locator("#auth-title").inner_text() == "Откройте своё рабочее пространство"
            result["checks"]["bootstrap_no_document_scroll"] = page.evaluate("document.documentElement.scrollHeight <= innerHeight")
            bootstrap_result = {}
            try:
                bootstrap_result = request_json(metadata["api"].removesuffix("/api/health") + "/api/auth/bootstrap", {"account_id": "visual-owner", "display_name": "Visual Owner", "password": "visual-owner-pass-123", "language": "ru"})
            except Exception as error:
                result["checks"]["bootstrap_api_note"] = type(error).__name__
            result["checks"]["bootstrap_api_used"] = True
            admin_headers = {"X-Admin-Role": "owner"}
            if bootstrap_result.get("token"):
                admin_headers["Authorization"] = f"Bearer {bootstrap_result['token']}"
            advanced = request_json(metadata["api"].removesuffix("/api/health") + "/api/admin/advanced", {"registration_enabled": False}, method="PATCH", headers=admin_headers)
            result["checks"]["registration_policy_off"] = advanced.get("controls", {}).get("registration_enabled") is False
            page.evaluate("localStorage.removeItem('luminifera.authToken')")
            page.reload(wait_until="networkidle")
            page.wait_for_function("document.querySelector('#auth-name-label')?.hidden === true", timeout=10_000)
            page.screenshot(path=str(OUT / "login-1920.png"), full_page=True)
            result["screens"].append("login-1920.png")
            result["checks"]["login_visible_after_bootstrap"] = page.locator("#auth-title").inner_text() == "Войдите в своё рабочее пространство"
            page.locator("#auth-alt").evaluate("button => button.click()")
            page.wait_for_function("document.querySelector('#auth-name-label')?.hidden === false && document.querySelector('#auth-language-label')?.hidden === false", timeout=5_000)
            result["checks"]["registration_screen"] = page.locator("#auth-submit").inner_text() == "Создать аккаунт"
            page.screenshot(path=str(OUT / "registration-off-1920.png"), full_page=True)
            result["screens"].append("registration-off-1920.png")
            page.locator("#auth-account").fill("registration-off-check")
            page.locator("#auth-name").fill("Registration Check")
            page.locator("#auth-password").fill("registration-off-pass-123")
            result["checks"]["auth_dom"] = page.evaluate("() => { const form=document.querySelector('#auth-form'), submit=document.querySelector('#auth-submit'), gate=document.querySelector('#auth-gate'); return {formOuterHTML:form?.outerHTML, submitType:submit?.type, submitDisabled:submit?.disabled, formHidden:form?.hidden, gateHidden:gate?.hidden, gateDisplay:getComputedStyle(gate).display, gatePointer:getComputedStyle(gate).pointerEvents, gateZ:getComputedStyle(gate).zIndex, duplicateForm:document.querySelectorAll('#auth-form').length, duplicateSubmit:document.querySelectorAll('#auth-submit').length, onsubmit:typeof form?.onsubmit === 'function' ? form.onsubmit.toString().slice(0,180) : null}; }")
            def trace_action(name: str, action) -> None:
                network_trace.clear()
                page.evaluate("window.__authTrace = []")
                page.evaluate("""() => {
                    const values = {"#auth-account":"registration-off-check", "#auth-name":"Registration Check", "#auth-password":"registration-off-pass-123"};
                    for (const [selector, value] of Object.entries(values)) {
                        const input = document.querySelector(selector);
                        if (input) { input.value = value; input.dispatchEvent(new Event('input', {bubbles:true})); input.dispatchEvent(new Event('change', {bubbles:true})); }
                    }
                }""")
                action()
                page.wait_for_timeout(1800)
                result["checks"][name] = {"trace": list(network_trace), "pageTrace": page.evaluate("window.__authTrace"), "dom": page.evaluate("() => ({errorHidden:document.querySelector('#auth-error')?.hidden, errorText:document.querySelector('#auth-error')?.textContent, mode:document.querySelector('#auth-submit')?.textContent})")}
            def real_mouse_click() -> None:
                box = page.locator("#auth-submit").bounding_box()
                if not box:
                    raise RuntimeError("submit_button_has_no_box")
                page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            trace_action("real_click", real_mouse_click)
            trace_action("request_submit", lambda: page.locator("#auth-form").evaluate("form => form.requestSubmit()"))
            trace_action("submit_event", lambda: page.locator("#auth-form").evaluate("form => form.dispatchEvent(new SubmitEvent('submit', {bubbles:true, cancelable:true, submitter:document.querySelector('#auth-submit')}))"))
            result["checks"]["registration_off_error"] = result["checks"]["request_submit"]["dom"]["errorHidden"] is False
            context.close()
            browser.close()
        result["checks"]["build_info"] = metadata
    except Exception as exc:
        result["errors"].append(f"{type(exc).__name__}: {exc}")
    finally:
        stop.write_text("stop", encoding="utf-8")
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True, check=False)
    (OUT / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True))
    return 0 if not result["errors"] and all(result["checks"].get(k) for k in ("bootstrap_visible", "bootstrap_no_document_scroll", "login_visible_after_bootstrap", "registration_off_error")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
