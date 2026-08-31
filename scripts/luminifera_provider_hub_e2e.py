"""Packaged smoke for the opt-in provider hub; never supplies credentials."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from luminifera_packaged_e2e import launch, stop

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    work = ROOT / ".tmp_luminifera_provider_hub"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    process = None
    result = {"checks": {}, "errors": []}
    try:
        process, _api, app_url = launch(ROOT / "dist" / "Luminifera.exe", work / "profile", work / "launch.json", work / "stop")
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(f"{app_url}?advanced=providers", wait_until="networkidle", timeout=20_000)
            page.locator(".provider-hub-dialog").wait_for(state="visible")
            result["checks"]["packaged_hub_opens"] = True
            result["checks"]["provider_rows_are_real"] = page.locator(".provider-hub-row").count() == page.locator("[data-provider-check]").count()
            result["checks"]["secret_inputs_are_passwords"] = page.locator('input[type="password"]').count() == page.locator("[data-provider-key]").count()
            result["checks"]["no_secret_values_rendered"] = page.locator('input[type="password"]').evaluate_all("items => items.every(item => !item.value)")
            result["checks"]["active_selection_present"] = page.locator("#provider-hub-active").count() == 1 and page.locator("#provider-hub-model").count() == 1
            browser.close()
        result["passed"] = all(result["checks"].values())
    except Exception as exc:
        result["errors"].append(f"{type(exc).__name__}: {exc}")
        result["passed"] = False
    finally:
        if process is not None:
            stop(process, work / "stop")
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
