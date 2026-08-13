from __future__ import annotations

import argparse
import json
import os
import sqlite3
import time
from pathlib import Path

from pywinauto import Desktop


AUDIT_ROOT = Path(__file__).resolve().parents[1] / "QA" / "RealityAudit001"
PROFILE_ROOT = Path(os.environ.get("ROMAN2050_AUDIT_PROFILE", AUDIT_ROOT / "clean_profile_baseline"))
DATABASE_PATH = PROFILE_ROOT / "roman2050.sqlite3"
WIZARD_PREFIX = "QApplication.OrganizationActivationWizard"
CONSOLE_PREFIX = "QApplication.DirectorConsoleDialog"
CREATE_TEAM_CAPTION = "\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u043a\u043e\u043c\u0430\u043d\u0434\u0443 \u0438\u0437 \u043f\u0440\u0435\u0441\u0435\u0442\u0430"


def team_window():
    candidates = []
    for window in Desktop(backend="uia").windows():
        try:
            if window.window_text().startswith("Team2050"):
                rectangle = window.rectangle()
                candidates.append(((rectangle.right - rectangle.left) * (rectangle.bottom - rectangle.top), window))
        except Exception:
            continue
    if candidates:
        return max(candidates, key=lambda item: item[0])[1]
    raise RuntimeError("Team2050 window is not available")


def wait_until(predicate, timeout: float = 10.0, interval: float = 0.1):
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            result = predicate()
            if result:
                return result
        except Exception as exc:
            last_error = exc
        time.sleep(interval)
    if last_error is not None:
        raise TimeoutError(str(last_error)) from last_error
    raise TimeoutError("GUI condition was not reached")


def visible_descendants(control_type: str):
    return [item for item in team_window().descendants(control_type=control_type) if item.is_visible()]


def wizard_button(caption: str):
    return wait_until(
        lambda: next(
            (
                item
                for item in visible_descendants("Button")
                if item.window_text() == caption and WIZARD_PREFIX in item.element_info.automation_id
            ),
            None,
        )
    )


def open_console_organization_tab() -> None:
    tabs = [item for item in visible_descendants("TabItem") if CONSOLE_PREFIX in item.element_info.automation_id]
    if not tabs:
        top_buttons = [
            item
            for item in visible_descendants("Button")
            if item.element_info.automation_id == "QApplication.MainWindow.appRoot.topBar.smallAction"
        ]
        if len(top_buttons) < 2:
            raise RuntimeError("Director Console button was not found")
        sorted(top_buttons, key=lambda item: item.rectangle().left)[-1].click_input()
        tabs = wait_until(
            lambda: [
                item
                for item in visible_descendants("TabItem")
                if CONSOLE_PREFIX in item.element_info.automation_id
            ]
        )
    tabs[1].select()
    wait_until(
        lambda: len(
            [
                item
                for item in visible_descendants("List")
                if "UniversalPlatformTab" in item.element_info.automation_id
            ]
        )
        >= 3
    )


def open_consulting_wizard() -> None:
    open_console_organization_tab()
    lists = [
        item
        for item in visible_descendants("List")
        if "UniversalPlatformTab" in item.element_info.automation_id
    ]
    template_list = max(lists, key=lambda item: item.rectangle().left)
    template_items = template_list.descendants(control_type="ListItem")
    if len(template_items) < 3:
        raise RuntimeError("Consulting preset was not found")
    template_items[2].click_input()
    time.sleep(0.3)
    action_button = next(
        (
            item
            for item in visible_descendants("Button")
            if "UniversalPlatformTab.QPushButton" in item.element_info.automation_id
            and item.window_text() == CREATE_TEAM_CAPTION
        ),
        None,
    )
    if action_button is None:
        raise RuntimeError("Preset activation button was not found")
    action_button.click_input()
    wait_until(
        lambda: next(
            (
                item
                for item in visible_descendants("Edit")
                if WIZARD_PREFIX in item.element_info.automation_id
            ),
            None,
        )
    )


def configure_providers() -> None:
    all_boxes = [
        item
        for item in visible_descendants("ComboBox")
        if WIZARD_PREFIX in item.element_info.automation_id
    ]
    rows: dict[int, list] = {}
    for box in all_boxes:
        rows.setdefault(box.rectangle().top, []).append(box)
    provider_boxes = [min(row, key=lambda item: item.rectangle().left) for row in rows.values() if len(row) == 3]
    if len(provider_boxes) != 6:
        raise RuntimeError(f"Expected 6 provider selectors, found {len(provider_boxes)} from {len(all_boxes)} boxes")
    for index, box in enumerate(sorted(provider_boxes, key=lambda item: item.rectangle().top)):
        caption = "Codex CLI" if index % 2 == 0 else "Gemini CLI"
        box.expand()
        option = wait_until(
            lambda: next(
                (
                    item
                    for window in Desktop(backend="uia").windows()
                    for item in window.descendants(control_type="ListItem")
                    if item.is_visible() and item.window_text() == caption
                ),
                None,
            )
        )
        option.click_input()
        time.sleep(0.1)


def create_consulting_organization(name: str) -> None:
    wizard_is_open = any(
        WIZARD_PREFIX in item.element_info.automation_id
        for item in team_window().descendants()
        if item.is_visible()
    )
    if not wizard_is_open:
        open_consulting_wizard()
    name_edits = [
        item
        for item in visible_descendants("Edit")
        if WIZARD_PREFIX in item.element_info.automation_id
    ]
    if name_edits:
        name_edits[0].set_edit_text(name)
        wizard_button("Next").click_input()
        wait_until(
            lambda: len(
                [
                    item
                    for item in visible_descendants("ComboBox")
                    if WIZARD_PREFIX in item.element_info.automation_id
                ]
            )
            >= 18
        )
    configure_providers()
    wizard_button("Next").click_input()
    time.sleep(0.3)
    wizard_button("Next").click_input()
    time.sleep(0.3)
    wizard_button("Finish").click_input()

    def close_summary():
        for button in visible_descendants("Button"):
            if button.window_text() == "OK" and "QMessageBox" in button.element_info.automation_id:
                return button
        return None

    wait_until(close_summary, timeout=30.0).click_input()
    wait_until(
        lambda: any(
            name in item.window_text()
            for item in visible_descendants("ListItem")
            if "UniversalPlatformTab.QListWidget" in item.element_info.automation_id
        )
    )


def database_inventory() -> dict[str, object]:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        organizations = [dict(row) for row in connection.execute("SELECT * FROM organizations ORDER BY created_at, id")]
        employees = [dict(row) for row in connection.execute("SELECT * FROM agent_profiles ORDER BY created_at, agent_id")]
        members = [dict(row) for row in connection.execute("SELECT * FROM organization_members ORDER BY organization_id, agent_id")]
        schema_rows = [dict(row) for row in connection.execute("SELECT * FROM schema_meta ORDER BY key")]
    finally:
        connection.close()
    return {
        "database": str(DATABASE_PATH),
        "schema": schema_rows,
        "organizations": organizations,
        "employees": employees,
        "members": members,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--create-organizations", type=int, default=0)
    parser.add_argument("--start-index", type=int, default=2)
    parser.add_argument("--inventory", action="store_true")
    args = parser.parse_args()

    for offset in range(args.create_organizations):
        create_consulting_organization(f"Audit Organization {args.start_index + offset}")
    if args.inventory:
        print(json.dumps(database_inventory(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
