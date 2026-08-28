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
    assert json.loads(service.paths.settings_path.read_text(encoding="utf-8"))["workspace_root"] == ""


def test_explicit_team2050_home_wins_over_legacy_override(monkeypatch, tmp_path):
    monkeypatch.setenv("ROMAN2050_HOME", str(tmp_path / "legacy"))
    monkeypatch.setenv("TEAM2050_HOME", str(tmp_path / "team"))

    assert SettingsService.default_user_dir() == tmp_path / "team"
