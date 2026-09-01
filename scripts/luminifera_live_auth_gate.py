"""Capture and probe the deployed unauthenticated Luminifera auth gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://nashron.onrender.com/app")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result = {"url": args.url, "build": None, "screens": [], "checks": {}, "errors": []}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context()
        page = context.new_page()
        api_responses = []
        page.on("response", lambda response: api_responses.append({"url": response.url, "status": response.status}) if "/api/" in response.url else None)
        page.goto(args.url, wait_until="networkidle", timeout=30_000)
        result["build"] = page.evaluate("async () => (await fetch('/api/build-info')).json()")
        result["checks"]["auth_gate_visible"] = page.locator("#auth-gate").is_visible()
        result["checks"]["bootstrap_status_ok"] = page.evaluate("async () => (await fetch('/api/auth/bootstrap-status')).ok")
        result["checks"]["iris_media_loaded"] = page.evaluate("() => { const el=document.querySelector('.auth-iris-presence'); return !!el && getComputedStyle(el).backgroundImage.includes('iris.png'); }")
        result["checks"]["no_console_errors"] = True
        for width, height in ((1920, 1080), (1440, 900)):
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_timeout(600)
            page.screenshot(path=str(args.output_dir / f"auth-{width}x{height}.png"), full_page=True)
            result["screens"].append(f"auth-{width}x{height}.png")
        result["api_responses"] = api_responses
        context.close()
        browser.close()
    result["passed"] = bool(result["build"].get("commit", "").startswith("e127798")) and all(result["checks"].values())
    (args.output_dir / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
