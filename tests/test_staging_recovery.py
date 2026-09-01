from __future__ import annotations

from pathlib import Path

import pytest

from scripts.recover_staging_owner import recover_profile


def test_recovery_requires_explicit_staging_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LUMINIFERA_STAGING", raising=False)
    with pytest.raises(RuntimeError, match="LUMINIFERA_STAGING=true"):
        recover_profile(tmp_path / "profile")


def test_recovery_moves_old_profile_and_creates_clean_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUMINIFERA_STAGING", "true")
    profile = tmp_path / "profile"
    profile.mkdir()
    (profile / "team2050.sqlite3").write_text("staging-only", encoding="utf-8")

    backup = recover_profile(profile)

    assert profile.is_dir()
    assert not (profile / "team2050.sqlite3").exists()
    assert backup.is_dir()
    assert (backup / "team2050.sqlite3").read_text(encoding="utf-8") == "staging-only"
