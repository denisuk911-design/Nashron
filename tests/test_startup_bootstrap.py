from __future__ import annotations

import logging

import pytest

from core.database import Database
from core.settings_service import SettingsService
from gui.main_window import MainWindow


def _make_settings_service(tmp_path):
    settings_service = SettingsService(project_root=tmp_path, user_dir=tmp_path / "user")
    settings = settings_service.load()
    settings["workspace_root"] = str(tmp_path / "workspace")
    settings_service.save(settings)
    return settings_service


def _build_window(settings_service, monkeypatch):
    qt_widgets = pytest.importorskip("PySide6.QtWidgets")
    app = qt_widgets.QApplication.instance() or qt_widgets.QApplication([])

    # The constructor path is real; provider health checks are outside this bootstrap invariant.
    monkeypatch.setattr(MainWindow, "refresh_codex_status", lambda self: None)
    window = MainWindow(settings_service, logging.getLogger("test-startup"))

    assert window.conversation_id is not None
    assert window.universal_platform_service.conversation_id == window.conversation_id
    assert window.thread_service.conversation_id == window.conversation_id
    assert window.startup_history == [
        "APP_START",
        "SETTINGS_READY",
        "DATABASE_READY",
        "MANAGEMENT_READY",
        "CONVERSATION_RESOLVED",
        "ORGANIZATION_RESOLVED",
        "CHAT_SERVICES_READY",
        "MAINWINDOW_READY",
        "USER_INTERACTIVE",
    ]
    assert window.startup_state == "USER_INTERACTIVE"

    return window


def test_main_window_bootstrap_first_run(tmp_path, monkeypatch):
    window = _build_window(_make_settings_service(tmp_path), monkeypatch)
    window.close()


def test_main_window_bootstrap_existing_conversation(tmp_path, monkeypatch):
    settings_service = _make_settings_service(tmp_path)
    database = Database(settings_service.paths.database_path)
    database.initialize()
    conversation_id = database.ensure_single_conversation("Existing conversation")
    database.add_message(conversation_id, "user", "Existing data")

    window = _build_window(settings_service, monkeypatch)
    assert window.conversation_id == conversation_id
    window.close()


def test_main_window_bootstrap_existing_active_organization(tmp_path, monkeypatch):
    settings_service = _make_settings_service(tmp_path)
    database = Database(settings_service.paths.database_path)
    database.initialize()
    conversation_id = database.ensure_single_conversation()
    organization_id = database.create_organization({"id": "ORG-BOOTSTRAP", "name": "Existing organization"})
    database.create_organization_workspace(
        {
            "organization_id": organization_id,
            "conversation_id": conversation_id,
            "workspace_path": str(tmp_path / "org-workspace"),
            "is_active": True,
        }
    )

    window = _build_window(settings_service, monkeypatch)
    assert window.active_organization_id == organization_id
    window.close()
