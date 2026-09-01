"""Packaged visual/interaction evidence for Phase 7."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from luminifera_packaged_e2e import launch, stop


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", default=str(ROOT / "dist" / "Luminifera.exe"))
    parser.add_argument("--work-dir", default=str(ROOT / ".tmp_luminifera_phase7_visual"))
    parser.add_argument("--evidence-dir", default=str(ROOT / "QA" / "PHASE7_LUMINIFERA_VISUAL"))
    args = parser.parse_args()
    work, evidence = Path(args.work_dir).resolve(), Path(args.evidence_dir).resolve()
    if work.exists():
        shutil.rmtree(work)
    if evidence.exists():
        shutil.rmtree(evidence)
    work.mkdir(parents=True)
    evidence.mkdir(parents=True)
    process = None
    result: dict[str, object] = {"checks": {}, "captures": [], "errors": []}
    try:
        process, _api, app_url = launch(Path(args.exe).resolve(), work / "profile", work / "launch.json", work / "stop")
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            for width, height in ((1920, 1080), (1440, 900)):
                page = browser.new_page(viewport={"width": width, "height": height})
                auth_responses = []
                def record_auth_response(response):
                    if "/api/auth/" not in response.url:
                        return
                    try:
                        auth_responses.append((response.url, response.status, response.text()[:400]))
                    except Exception:
                        auth_responses.append((response.url, response.status, "<unreadable>"))
                page.on("response", record_auth_response)
                page.goto(app_url, wait_until="networkidle", timeout=20_000)
                if not page.locator("#auth-gate.auth-ready").count():
                    page.wait_for_timeout(1_500)
                    page.locator("#auth-form").evaluate("form => { form.querySelector('#auth-account').value = 'visual-owner'; form.querySelector('#auth-name').value = 'Visual Owner'; form.querySelector('#auth-password').value = 'Visual-owner-pass-123'; }")
                    page.locator("#auth-form").dispatch_event("submit")
                    try:
                        page.locator("#auth-gate.auth-ready").wait_for(state="attached", timeout=15_000)
                    except Exception as error:
                        auth_error = page.locator("#auth-error").inner_text() if page.locator("#auth-error").count() else ""
                        auth_status = page.locator("#auth-status").inner_text() if page.locator("#auth-status").count() else ""
                        title = page.locator("#auth-title").inner_text() if page.locator("#auth-title").count() else ""
                        requests = page.evaluate("performance.getEntriesByType('resource').map(entry => entry.name).filter(name => name.includes('/api/auth/'))")
                        raise RuntimeError(f"first_run_auth_failed: title={title}; error={auth_error}; status={auth_status}; requests={requests}; responses={auth_responses}") from error
                page.locator('[data-screen="home"]').wait_for(state="visible")
                if page.locator(".onboarding-dialog[open]").count():
                    page.locator("#onboarding-start").click(force=True)
                    page.locator(".onboarding-dialog[open]").wait_for(state="detached", timeout=10_000)
                if width == 1920:
                    page.locator("#iris-input").fill("Мне нужен результат: техническая спецификация преобразователя 24 В в 12 В, 5 А")
                    page.locator("#iris-form").dispatch_event("submit")
                    page.locator("#iris-action").wait_for(state="visible", timeout=30_000)
                    result["checks"]["iris_goal_proposal"] = page.locator("#iris-action").inner_text() == "Собрать созвездие"
                    page.locator("#iris-action").click()
                    page.locator("#iris-action").wait_for(state="visible", timeout=30_000)
                    result["checks"]["team_created_from_ui"] = page.locator("#iris-action").inner_text() == "Создать цель из запроса"
                    page.locator("#iris-action").click()
                    page.locator("#iris-action").wait_for(state="visible", timeout=15_000)
                    result["checks"]["goal_created_from_ui"] = page.locator("#iris-action").inner_text() == "Запустить работу"
                    page.locator("#iris-action").click()
                    page.locator('[data-screen="work"]').wait_for(state="visible", timeout=30_000)
                    result["checks"]["goal_started_from_ui"] = page.evaluate("location.hash") == "#work"
                    page.locator('.brand[data-route="home"]').click()
                    page.locator('[data-screen="home"]').wait_for(state="visible", timeout=10_000)
                page.screenshot(path=str(evidence / f"home-{width}x{height}.png"), full_page=True)
                page.locator(".viewport").hover()
                page.mouse.wheel(0, 700)
                page.wait_for_timeout(700)
                result["checks"][f"wheel_home_to_team_{width}"] = page.evaluate("location.hash") == "#team"
                page.screenshot(path=str(evidence / f"team-{width}x{height}.png"), full_page=True)
                page.mouse.wheel(0, 700); page.wait_for_timeout(700)
                result["checks"][f"wheel_team_to_work_{width}"] = page.evaluate("location.hash") == "#work"
                page.screenshot(path=str(evidence / f"work-{width}x{height}.png"), full_page=True)
                page.locator('nav button[data-route="files"]').click(); page.wait_for_timeout(350)
                page.screenshot(path=str(evidence / f"files-{width}x{height}.png"), full_page=True)
                page.locator('nav button[data-route="settings"]').click(); page.wait_for_timeout(500)
                page.locator(".theme-preview").wait_for(state="visible")
                page.screenshot(path=str(evidence / f"settings-{width}x{height}.png"), full_page=True)
                page.locator('[data-theme-choice="night_city"]').click()
                page.locator("#save-settings").click()
                page.wait_for_timeout(500)
                result["checks"][f"theme_applies_{width}"] = page.locator("html").get_attribute("data-theme") == "night_city"
                page.locator('.brand[data-route="home"]').click(); page.wait_for_timeout(350)
                page.locator(".viewport").hover()
                page.mouse.wheel(0, -900); page.wait_for_timeout(150)
                result["checks"][f"edge_spring_{width}"] = bool(page.locator(".viewport.edge-pull-up").count())
                result["captures"].extend([f"home-{width}x{height}.png", f"team-{width}x{height}.png", f"work-{width}x{height}.png", f"files-{width}x{height}.png", f"settings-{width}x{height}.png"])
                page.close()
            browser.close()
        result["passed"] = all(bool(value) for value in result["checks"].values())
    except Exception as exc:
        result["errors"].append(f"{type(exc).__name__}: {exc}")
        result["passed"] = False
    finally:
        if process is not None:
            stop(process, work / "stop")
    output = evidence / "manifest.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
