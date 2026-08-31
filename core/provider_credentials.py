from __future__ import annotations

from .database import Database
import os

from .secure_storage import FileCredentialStore, SecureStorageUnavailable, WindowsCredentialStore


class ProviderCredentialService:
    """Provider-neutral secure credential boundary; no secrets are stored in SQLite."""

    def __init__(self, database: Database, store=None) -> None:
        self.database = database
        self._store = store

    def read(self, provider_id: str) -> str | None:
        try:
            return self._credential_store().read(provider_id)
        except (SecureStorageUnavailable, OSError):
            return None

    def is_configured(self, provider_id: str) -> bool:
        return bool(self.read(provider_id))

    def save(self, provider_id: str, secret: str) -> str:
        value = str(secret).strip()
        if not value:
            raise ValueError("credential is empty")
        reference = self._credential_store().write(provider_id, value)
        self.database.log_event("provider_credential_saved", f"{provider_id}:{reference}")
        return reference

    def remove(self, provider_id: str) -> bool:
        removed = self._credential_store().delete(provider_id)
        self.database.log_event("provider_connection_removed", provider_id)
        return removed

    def _credential_store(self):
        if self._store is None:
            test_store = os.environ.get("TEAM2050_TEST_CREDENTIAL_STORE")
            self._store = FileCredentialStore(test_store) if test_store else WindowsCredentialStore()
        return self._store
