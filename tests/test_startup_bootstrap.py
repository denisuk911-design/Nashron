from __future__ import annotations

import logging

import pytest

from core.settings_service import SettingsService
from gui.main_window import MainWindow


def test_main_window_resolves_conversation_before_dependent_services(tmp_path, monkeypatch):
    qt_widgets = pytest.importorskip("PySide6.QtWidgets")
    app = qt_widgets.QApplication.instance() or qt_widgets.QApplication([])
    settings_service = SettingsService(project_root=tmp_path, user_dir=tmp_path / "user")
    settings = settings_service.load()
    settings["workspace_root"] = str(tmp_path / "workspace")
    settings_service.save(settings)

    # The constructor path is real; provider health checks are outside this bootstrap invariant.
    monkeypatch.setattr(MainWindow, "refresh_codex_status", lambda self: None)
    window = MainWindow(settings_service, logging.getLogger("test-startup"))

    assert window.conversation_id is not None
    assert window.universal_platform_service.conversation_id == window.conversation_id
    assert window.thread_service.conversation_id == window.conversation_id
    assert window.startup_state == "USER_INTERACTIVE"

    window.close()
