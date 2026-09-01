"""Capture the deployed Render product for the public visual-review artifact.

The runner never starts the local app. It waits for Render to expose the
requested commit, then records only browser-visible screenshots and health
metadata. Credentials are read from the environment and are never written.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://nashron.onrender.com/app")
    parser.add_argument("--target-sha", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--wait-seconds", type=int, default=600)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    base = args.url.split("/app", 1)[0] + "/"
    result: dict[str, object] = {
        "url": args.url,
        "target_sha": args.target_sha,
        "build": None,
        "scenarios": [],
        "network": [],
        "console": [],
        "errors": [],
    }
    build_url = urljoin(base, "api/build-info")
    def read_build() -> dict[str, object]:
        request = Request(build_url, headers={"Cache-Control": "no-cache"})
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for width, height in ((1920, 1080), (1440, 900)):
            context = browser.new_context(viewport={"width": width, "height": height})
            page = context.new_page()
            console_errors: list[str] = []
            network: list[dict[str, object]] = []
            expected_auth_error = {"active": False}
            page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" and not expected_auth_error["active"] else None)
            page.on("response", lambda response: network.append({"url": response.url, "status": response.status}) if "/api/" in response.url else None)
            deadline = time.monotonic() + args.wait_seconds
            build = None
            while time.monotonic() < deadline:
                try:
                    build = read_build()
                    if str(build.get("commit", "")).startswith(args.target_sha):
                        break
                except Exception:
                    pass
                time.sleep(5)
            if not build or not str(build.get("commit", "")).startswith(args.target_sha):
                result["errors"].append(f"Render did not expose target SHA {args.target_sha}")
                context.close()
                continue
            result["build"] = build
            page.goto(args.url, wait_until="domcontentloaded", timeout=60_000)
            page.locator("#auth-form").wait_for(state="visible", timeout=30_000)
            page.wait_for_function("() => document.querySelector('#auth-gate')?.getAttribute('aria-busy') !== 'true'")
            page.screenshot(path=str(args.output_dir / f"registration-{width}x{height}.png"), full_page=True)
            result["scenarios"].append(f"registration-{width}x{height}.png")
            page.locator("#auth-alt").click()
            page.screenshot(path=str(args.output_dir / f"login-{width}x{height}.png"), full_page=True)
            result["scenarios"].append(f"login-{width}x{height}.png")
            page.locator("#auth-account").fill("invalid@example.com")
            page.locator("#auth-password").fill("wrong-pass-123")
            expected_auth_error["active"] = True
            page.locator("#auth-form").dispatch_event("submit")
            page.locator("#auth-error").wait_for(state="visible", timeout=15_000)
            expected_auth_error["active"] = False
            page.screenshot(path=str(args.output_dir / f"error-{width}x{height}.png"), full_page=True)
            result["scenarios"].append(f"error-{width}x{height}.png")
            account = os.environ.get("LUMINIFERA_REVIEW_EMAIL", "").strip()
            password = os.environ.get("LUMINIFERA_REVIEW_PASSWORD", "")
            if account and password:
                page.locator("#auth-account").fill(account)
                page.locator("#auth-password").fill(password)
                page.locator("#auth-form").dispatch_event("submit")
                page.locator(".iris-panel").wait_for(state="visible", timeout=45_000)
                page.wait_for_timeout(1200)
                page.screenshot(path=str(args.output_dir / f"iris-before-{width}x{height}.png"), full_page=True)
                page.locator("#iris-input").fill("Что ты умеешь?")
                page.locator("#iris-form").dispatch_event("submit")
                page.locator("#iris-chat .message").nth(1).wait_for(state="visible", timeout=90_000)
                page.wait_for_timeout(1000)
                page.screenshot(path=str(args.output_dir / f"iris-after-{width}x{height}.png"), full_page=True)
                result["scenarios"].extend([f"iris-before-{width}x{height}.png", f"iris-after-{width}x{height}.png"])
            else:
                result["errors"].append("LUMINIFERA_REVIEW_EMAIL and LUMINIFERA_REVIEW_PASSWORD are required for Iris live captures")
            result["network"].extend(network)
            result["console"].extend(console_errors)
            context.close()
        browser.close()
    result["checks"] = {
        "target_sha": bool(result["build"]),
        "auth_screens": all(any(name.startswith(prefix) and name.endswith(f"{size}.png") for name in result["scenarios"]) for prefix in ("registration-", "login-", "error-") for size in ("1920x1080", "1440x900")),
        "iris_screens": all(any(name.startswith(prefix) and name.endswith(f"{size}.png") for name in result["scenarios"]) for prefix in ("iris-before-", "iris-after-") for size in ("1920x1080", "1440x900")),
        "no_console_errors": not result["console"],
    }
    result["passed"] = not result["errors"] and all(bool(value) for value in result["checks"].values())
    manifest = json.dumps(result, ensure_ascii=False, indent=2)
    (args.output_dir / "manifest.json").write_text(manifest, encoding="utf-8")
    images = "".join(f'<figure><img src="{name}" loading="lazy"><figcaption>{name}</figcaption></figure>' for name in result["scenarios"])
    page = f"<!doctype html><meta charset='utf-8'><title>Luminifera Live Visual Review</title><style>body{{font:16px system-ui;background:#071126;color:#eef2ff;margin:32px}}h1{{font-weight:500}}.meta{{white-space:pre-wrap;background:#101d3a;padding:16px;border-radius:12px}}main{{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:20px}}figure{{margin:0}}img{{display:block;width:100%;border-radius:10px;border:1px solid #33466e}}figcaption{{margin-top:8px;color:#aab9db;font-size:13px}}</style><h1>Luminifera · Live Visual Review</h1><div class='meta'>{json.dumps({'build': result['build'], 'target_sha': result['target_sha'], 'checks': result['checks'], 'network_requests': len(result['network']), 'console_errors': len(result['console'])}, ensure_ascii=False, indent=2)}</div><main>{images}</main>"
    (args.output_dir / "index.html").write_text(page, encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
