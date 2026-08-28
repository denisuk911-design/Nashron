from __future__ import annotations

import json

from core.settings_service import SettingsService


def test_preview_profile_uses_team2050_namespace_and_private_workspace(monkeypatch, tmp_path):
    preview_home = tmp_path / "Team2050-Preview"
    monkeypatch.delenv("ROMAN2050_HOME", raising=False)
    monkeypatch.setenv("TEAM2050_PREVIEW", "1")
    monkeypatch.setenv("TEAM2050_PREVIEW_HOME", str(preview_home))

    service = SettingsService(project_root=tmp_path / "source")
    settings = service.load()

    assert service.user_dir == preview_home
    assert settings["workspace_root"] == str(preview_home / "workspace")
    assert "Roman2050" not in settings["workspace_root"]
    assert service.paths.database_path.parent == preview_home
    assert service.paths.avatar_dir == preview_home / "data" / "avatars"
    assert service.paths.database_path.name == "team2050.sqlite3"
    assert json.loads(service.paths.settings_path.read_text(encoding="utf-8"))["workspace_root"] == ""


def test_explicit_team2050_home_wins_over_legacy_override(monkeypatch, tmp_path):
    monkeypatch.setenv("ROMAN2050_HOME", str(tmp_path / "legacy"))
    monkeypatch.setenv("TEAM2050_HOME", str(tmp_path / "team"))

    assert SettingsService.default_user_dir() == tmp_path / "team"


def test_default_profile_uses_team2050_names_without_legacy_paths(monkeypatch, tmp_path):
    monkeypatch.delenv("TEAM2050_PREVIEW", raising=False)
    monkeypatch.delenv("TEAM2050_PREVIEW_HOME", raising=False)
    monkeypatch.delenv("TEAM2050_HOME", raising=False)
    monkeypatch.delenv("ROMAN2050_HOME", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    service = SettingsService(project_root=tmp_path / "source")

    assert service.user_dir == tmp_path / "Team2050"
    assert service.paths.database_path == tmp_path / "Team2050" / "team2050.sqlite3"
