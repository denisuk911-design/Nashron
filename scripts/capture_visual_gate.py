"""Capture real Luminifera screens with an isolated local Chromium session.

This helper is intentionally outside the product runtime. It only drives the
already-running Web client and records what is actually rendered; it never
creates or mutates application data.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


VIEWS = (
    ("home", "Главная"),
    ("iris", "Iris"),
    ("team", "Команда"),
    ("work", "Работа"),
    ("files", "Файлы"),
    ("settings", "Настройки"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Running Luminifera URL, for example http://127.0.0.1:12345/app")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--profile-dir", type=Path, help="Optional isolated Chromium profile directory")
    parser.add_argument("--headed", action="store_true", help="Show Chromium while capturing")
    parser.add_argument("--timeout-ms", type=int, default=20_000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is required: python -m pip install playwright", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    base_url = args.url.rstrip("/")
    if base_url.endswith("/app"):
        app_url = base_url
        landing_url = base_url[:-4] or base_url
    else:
        landing_url = base_url
        app_url = f"{base_url}/app"
    manifest: dict[str, object] = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "app_url": app_url,
        "screens": [],
    }

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed)
        context_kwargs = {"viewport": {"width": 1440, "height": 900}}
        if args.profile_dir:
            context = playwright.chromium.launch_persistent_context(
                str(args.profile_dir), headless=not args.headed, **context_kwargs
            )
            browser = None
        else:
            context = browser.new_context(**context_kwargs)
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(args.timeout_ms)

        def capture(name: str, url: str) -> None:
            record: dict[str, object] = {"name": name, "url": url}
            try:
                page.goto(url, wait_until="networkidle", timeout=args.timeout_ms)
                page.screenshot(path=str(args.output_dir / f"{name}.png"), full_page=True)
                record["status"] = "captured"
            except PlaywrightTimeoutError as error:
                record.update({"status": "unavailable", "reason": f"timeout: {error}"})
            except Exception as error:  # pragma: no cover - browser-dependent diagnostics
                record.update({"status": "unavailable", "reason": str(error)})
            manifest["screens"].append(record)

        capture("landing", landing_url)
        page.goto(app_url, wait_until="networkidle", timeout=args.timeout_ms)
        for name, label in VIEWS:
            record: dict[str, object] = {"name": name, "label": label}
            try:
                button = page.locator(f'button[data-view="{name}"]:visible').first
                button.wait_for(state="visible", timeout=args.timeout_ms)
                button.click()
                page.wait_for_timeout(500)
                page.screenshot(path=str(args.output_dir / f"{name}.png"), full_page=True)
                record["status"] = "captured"
            except PlaywrightTimeoutError as error:
                record.update({"status": "unavailable", "reason": f"timeout: {error}"})
            except Exception as error:  # pragma: no cover - browser-dependent diagnostics
                record.update({"status": "unavailable", "reason": str(error)})
            manifest["screens"].append(record)

        # BYOK and Feedback are sections of Settings in the current product,
        # not separate routes. Capture the real Settings render without
        # clicking arbitrary text, and make that fact explicit in the manifest.
        section_selectors = {
            "byok": '.settings-grid .settings-panel:nth-child(2)',
            "feedback": '.settings-grid .settings-panel:nth-child(3)',
        }
        section_labels = {"byok": "AI providers", "feedback": "Iris feedback"}
        for name, selector in section_selectors.items():
            """legacy pattern table removed
            "byok": ("AI-провайдеры", "Подключения Iris", "BYOK"),
            "feedback": ("Feedback Inbox", "Обратная связь Iris", "Feedback"),
        }.items():
            """
            record = {"name": name, "status": "unavailable", "reason": "No real Settings section found"}
            section = page.locator(selector)
            if section.count() and section.is_visible():
                section.screenshot(path=str(args.output_dir / f"{name}.png"))
                record = {
                    "name": name,
                    "status": "captured",
                    "section": section_labels[name],
                    "route": "#settings",
                    "capture_mode": "element",
                }
            manifest["screens"].append(record)

        context.close()
        if browser:
            browser.close()

    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    unavailable = [screen["name"] for screen in manifest["screens"] if screen["status"] != "captured"]
    print(json.dumps({"output_dir": str(args.output_dir), "unavailable": unavailable}, ensure_ascii=False))
    return 1 if unavailable else 0


if __name__ == "__main__":
    raise SystemExit(main())
