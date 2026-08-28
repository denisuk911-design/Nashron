import json
import sqlite3
import zipfile

import pytest

from core.profile_backup_service import ProfileBackupError, ProfileBackupService


def _profile(path):
    (path / "data").mkdir(parents=True)
    (path / "data" / "app_settings.json").write_text('{"theme":"dark"}', encoding="utf-8")
    connection = sqlite3.connect(path / "team2050.sqlite3")
    connection.execute("CREATE TABLE organization (id INTEGER PRIMARY KEY)")
    connection.commit()
    connection.close()


def test_backup_restore_preserves_profile_and_excludes_secrets(tmp_path):
    source, restored = tmp_path / "source", tmp_path / "restored"
    _profile(source)
    (source / "logs").mkdir()
    (source / "logs" / "secret.log").write_text("AQ.secret", encoding="utf-8")
    backup = tmp_path / "profile.zip"
    service = ProfileBackupService()
    service.backup(source, backup)
    with zipfile.ZipFile(backup) as archive:
        assert "logs/secret.log" not in archive.namelist()
        assert json.loads(archive.read("backup-manifest.json"))["schema_version"] == 1
    service.restore(backup, restored)
    assert (restored / "team2050.sqlite3").is_file()
    assert (restored / "data" / "app_settings.json").read_text(encoding="utf-8") == '{"theme":"dark"}'


def test_restore_rejects_tampered_backup_without_touching_profile(tmp_path):
    source, target = tmp_path / "source", tmp_path / "target"
    _profile(source)
    target.mkdir()
    (target / "marker.txt").write_text("untouched", encoding="utf-8")
    backup = tmp_path / "profile.zip"
    ProfileBackupService().backup(source, backup)
    with zipfile.ZipFile(backup, "a") as archive:
        archive.writestr("data/app_settings.json", "tampered")
    with pytest.raises(ProfileBackupError, match="backup_integrity_failed"):
        ProfileBackupService().restore(backup, target)
    assert (target / "marker.txt").read_text(encoding="utf-8") == "untouched"
