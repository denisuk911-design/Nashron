from __future__ import annotations

import hashlib
import hmac
import secrets
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Any

from .database import Database
from .codex_client import CodexClient
from .models import AuthStatus


class AuthenticationError(PermissionError):
    pass


class AuthService:
    """Legacy Codex login facade retained for the PySide fallback."""

    def __init__(self, client: CodexClient) -> None:
        self.client = client

    def status(self) -> AuthStatus:
        return self.client.login_status()

    def start_login(self) -> subprocess.Popen[str]:
        return self.client.start_login()

    def logout(self) -> AuthStatus:
        return self.client.logout()


class AccountAuthService:
    """Minimal persistent account/session contract for the local product.

    Registration is controlled by the application policy. Credentials and
    sessions are always stored as hashes or opaque tokens only.
    """

    SESSION_HOURS = 24

    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210_000).hex()

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _identifier_hash(identifier: str) -> str:
        return hashlib.sha256(identifier.strip().casefold().encode("utf-8")).hexdigest()

    def set_password(self, account_id: str, password: str) -> None:
        if len(password) < 10:
            raise ValueError("password_too_short")
        if not any(ch.isalpha() for ch in password) or not any(ch.isdigit() for ch in password):
            raise ValueError("password_requires_letters_and_digits")
        salt = secrets.token_bytes(16)
        self.database.save_account_credential(account_id, self._hash_password(password, salt), salt.hex())

    def register(self, account_id: str, display_name: str, password: str, *, language: str = "ru") -> dict[str, Any]:
        normalized = account_id.strip()
        if len(normalized) < 3 or any(ch.isspace() for ch in normalized):
            raise ValueError("invalid_account_id")
        if len(display_name.strip()) < 1:
            raise ValueError("invalid_display_name")
        if self.database.get_account_credential(normalized) is not None:
            raise ValueError("account_already_exists")
        if any(str(row["account_id"]).casefold() == normalized.casefold() for row in self.database.list_admin_accounts()):
            raise ValueError("account_already_exists")
        self.database.upsert_admin_user({
            "user_id": normalized,
            "display_name": display_name.strip(),
            "role": "member",
            "organization_id": None,
            "language": language if language in {"ru", "uk", "en"} else "ru",
            "plan": "free",
            "status": "ACTIVE",
        })
        self.set_password(normalized, password)
        self.database.record_auth_attempt(self._identifier_hash(normalized), account_id=normalized, succeeded=True)
        return {"account_id": normalized, "status": "created"}

    def login(self, account_id: str, password: str, *, max_attempts: int = 10) -> dict[str, Any]:
        identifier = self._identifier_hash(account_id)
        if self.database.count_auth_failures(identifier) >= max_attempts:
            raise AuthenticationError("login_rate_limited")
        account = next((row for row in self.database.list_admin_accounts() if str(row["account_id"]) == account_id), None)
        credential = self.database.get_account_credential(account_id)
        if account is None or credential is None or str(account["status"]).upper() != "ACTIVE":
            self.database.record_auth_attempt(identifier, account_id=account_id if account else None)
            raise AuthenticationError("invalid_credentials_or_blocked_account")
        expected = self._hash_password(password, bytes.fromhex(str(credential["salt"])))
        if not hmac.compare_digest(expected, str(credential["password_hash"])):
            self.database.record_auth_attempt(identifier, account_id=account_id)
            raise AuthenticationError("invalid_credentials_or_blocked_account")
        token = secrets.token_urlsafe(32)
        session_id = f"SES-{secrets.token_hex(8).upper()}"
        expires = datetime.now(timezone.utc) + timedelta(hours=self.SESSION_HOURS)
        self.database.create_admin_session(session_id, account_id, self._token_hash(token), expires.isoformat())
        with self.database.connect() as conn:
            conn.execute("UPDATE admin_accounts SET last_login = CURRENT_TIMESTAMP, last_activity_at = CURRENT_TIMESTAMP WHERE account_id = ?", (account_id,))
        self.database.record_auth_attempt(identifier, account_id=account_id, succeeded=True)
        return {"session_id": session_id, "token": token, "expires_at": expires.isoformat(), "account_id": account_id}

    def authenticate(self, token: str) -> dict[str, Any]:
        row = self.database.get_admin_session(self._token_hash(token))
        if row is None or row["revoked_at"] is not None or str(row["status"]).upper() != "ACTIVE":
            raise AuthenticationError("session_invalid_or_revoked")
        expires = datetime.fromisoformat(str(row["expires_at"]))
        if expires <= datetime.now(timezone.utc):
            raise AuthenticationError("session_expired")
        return {key: row[key] for key in ("session_id", "account_id", "role", "status", "organization_id", "language", "plan")}

    def logout(self, token: str) -> bool:
        row = self.database.get_admin_session(self._token_hash(token))
        return bool(row and self.database.revoke_admin_session(str(row["session_id"])))
