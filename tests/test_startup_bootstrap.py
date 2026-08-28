from __future__ import annotations

import logging

import pytest

from core.database import Database
from core.settings_service import SettingsService
from core.avatar_catalog import list_avatar_files
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
    assert window.active_organization_id is None
    assert not window.empty_team_panel.isHidden()
    assert window.chat.isHidden()
    window.close()


def test_first_run_can_be_skipped_without_creating_seed_employees(tmp_path, monkeypatch):
    settings_service = _make_settings_service(tmp_path)
    window = _build_window(settings_service, monkeypatch)

    window._skip_onboarding()

    assert window.empty_team_panel.isHidden()
    assert not window.chat.isHidden()
    assert window.database.list_organizations() == []
    assert window.database.list_agent_profiles() == []
    assert settings_service.load()["onboarding_skipped"] is True
    window.close()


def test_onboarding_user_avatar_is_saved_and_restored(tmp_path, monkeypatch):
    settings_service = _make_settings_service(tmp_path)
    avatar = settings_service.paths.avatar_dir / "avatar-01-man-realistic.png"
    avatar.parent.mkdir(parents=True, exist_ok=True)
    avatar.write_bytes(b"test-avatar")
    window = _build_window(settings_service, monkeypatch)
    avatars = list_avatar_files(settings_service.paths.avatar_dir)
    assert avatars

    index = window.empty_team_avatar.findData(str(avatars[0]))
    assert index > 0
    window.empty_team_avatar.setCurrentIndex(index)
    window.close()

    restored = settings_service.load()
    assert restored["user_avatar_path"] == str(avatars[0])


def test_first_team_activation_refreshes_chat_without_restart(tmp_path, monkeypatch):
    window = _build_window(_make_settings_service(tmp_path), monkeypatch)
    template = next(
        item for item in window.universal_platform_service.list_templates()
        if item.name == "SOLO_PROFESSIONAL"
    )
    activation = window.universal_platform_service.activate_template(
        template.template_id,
        "Live team",
        team_size="MINI",
    )

    window._activate_organization_live(activation.organization.organization_id)

    assert window.active_organization_id == activation.organization.organization_id
    assert window.conversation_id == window.database.ensure_organization_conversation(
        activation.organization.organization_id,
        activation.organization.name,
    )
    assert not window.chat.isHidden()
    assert window.empty_team_panel.isHidden()
    assert len(window._chat_agents()) == len(activation.employee_ids)
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
