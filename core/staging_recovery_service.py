"""Guarded, one-shot recovery for an explicitly enabled staging profile."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from .database import Database

NONCE_SETTING = "staging.recovery.nonce_sha256"


def recover_auth_state_once(database: Database, nonce: str | None = None) -> bool:
    """Remove only staging auth/admin rows once for the supplied nonce."""
    if os.environ.get("LUMINIFERA_STAGING", "").lower() != "true":
        return False
    nonce = nonce or os.environ.get("LUMINIFERA_STAGING_RESET_ON_BOOT", "")
    if not nonce:
        return False
    digest = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
    with database.connect() as conn:
        previous = conn.execute("SELECT setting_value FROM admin_persisted_settings WHERE setting_key = ?", (NONCE_SETTING,)).fetchone()
        if previous is not None:
            return False
        conn.execute("INSERT INTO admin_persisted_settings(setting_key, setting_value) VALUES (?, ?)", (NONCE_SETTING, digest))
        for table in ("admin_sessions", "account_credentials", "auth_attempts", "provider_usage_events", "admin_accounts", "admin_users"):
            conn.execute(f"DELETE FROM {table}")
    return True


def recover_profile_auth(profile: Path, nonce: str | None = None) -> bool:
    database = Database(Path(profile).expanduser().resolve() / "team2050.sqlite3")
    database.initialize()
    return recover_auth_state_once(database, nonce)
