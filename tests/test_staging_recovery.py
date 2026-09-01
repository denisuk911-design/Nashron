from __future__ import annotations

from pathlib import Path

import pytest

from core.database import Database
from core.staging_recovery_service import recover_auth_state_once


def _database(path: Path) -> Database:
    database = Database(path)
    database.initialize()
    return database


def test_recovery_requires_explicit_staging_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database = _database(tmp_path / "team2050.sqlite3")
    monkeypatch.delenv("LUMINIFERA_STAGING", raising=False)
    monkeypatch.setenv("LUMINIFERA_STAGING_RESET_ON_BOOT", "nonce-a")
    assert recover_auth_state_once(database) is False


def test_recovery_is_one_shot_and_preserves_product_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database = _database(tmp_path / "team2050.sqlite3")
    monkeypatch.setenv("LUMINIFERA_STAGING", "true")
    monkeypatch.setenv("LUMINIFERA_STAGING_RESET_ON_BOOT", "nonce-a")
    with database.connect() as conn:
        conn.execute("INSERT INTO organizations(id, name, purpose) VALUES ('ORG-KEEP', 'Keep', 'product')")
        conn.execute("INSERT INTO admin_accounts(account_id, display_name, role) VALUES ('owner', 'Owner', 'owner')")
        conn.execute("INSERT INTO admin_sessions(session_id, account_id, token_hash, expires_at) VALUES ('session', 'owner', 'hash', '2099-01-01')")
        conn.execute("INSERT INTO product_telemetry_events(event_id, user_id, event_type, detail) VALUES ('event', 'owner', 'visit', '{}')")

    assert recover_auth_state_once(database) is True
    assert recover_auth_state_once(database) is False
    with database.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM organizations WHERE id = 'ORG-KEEP'").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM product_telemetry_events WHERE event_id = 'event'").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM admin_accounts").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM admin_sessions").fetchone()[0] == 0
        assert conn.execute("SELECT setting_value FROM admin_persisted_settings WHERE setting_key = 'staging.recovery.nonce_sha256'").fetchone()[0] != 'nonce-a'
