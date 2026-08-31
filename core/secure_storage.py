from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from pathlib import Path


class SecureStorageUnavailable(RuntimeError):
    pass


class FileCredentialStore:
    """Opt-in isolated store used only by disposable integration-test profiles."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)

    def _load(self) -> dict[str, str]:
        try:
            import json
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _save(self, values: dict[str, str]) -> None:
        import json
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(values), encoding="utf-8")

    def write(self, key: str, secret: str, username: str = "Team2050") -> str:
        values = self._load()
        values[key] = secret
        self._save(values)
        return f"test-store/{key}"

    def read(self, key: str) -> str | None:
        return self._load().get(key)

    def delete(self, key: str) -> bool:
        values = self._load()
        existed = key in values
        values.pop(key, None)
        self._save(values)
        return existed


class WindowsCredentialStore:
    """Minimal Windows Credential Manager wrapper; secrets never enter SQLite."""

    CRED_TYPE_GENERIC = 1
    CRED_PERSIST_LOCAL_MACHINE = 2

    class _CREDENTIAL(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    def __init__(self, namespace: str = "Team2050") -> None:
        if os.name != "nt":
            raise SecureStorageUnavailable("Windows Credential Manager is available only on Windows")
        self.namespace = namespace
        self._advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)

    def write(self, key: str, secret: str, username: str = "Team2050") -> str:
        target = self._target(key)
        secret_bytes = secret.encode("utf-8")
        blob = (ctypes.c_ubyte * len(secret_bytes)).from_buffer_copy(secret_bytes)
        credential = self._CREDENTIAL()
        credential.Type = self.CRED_TYPE_GENERIC
        credential.TargetName = target
        credential.CredentialBlobSize = len(secret_bytes)
        credential.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(ctypes.c_ubyte))
        credential.Persist = self.CRED_PERSIST_LOCAL_MACHINE
        credential.UserName = username
        if not self._advapi32.CredWriteW(ctypes.byref(credential), 0):
            raise ctypes.WinError()
        return target

    def read(self, key: str) -> str | None:
        pointer = ctypes.POINTER(self._CREDENTIAL)()
        if not self._advapi32.CredReadW(self._target(key), self.CRED_TYPE_GENERIC, 0, ctypes.byref(pointer)):
            error = ctypes.get_last_error()
            if error == 1168:
                return None
            raise ctypes.WinError(error)
        try:
            credential = pointer.contents
            data = ctypes.string_at(credential.CredentialBlob, credential.CredentialBlobSize)
            return data.decode("utf-8")
        finally:
            self._advapi32.CredFree(pointer)

    def delete(self, key: str) -> bool:
        if self._advapi32.CredDeleteW(self._target(key), self.CRED_TYPE_GENERIC, 0):
            return True
        error = ctypes.get_last_error()
        if error == 1168:
            return False
        raise ctypes.WinError(error)

    def _target(self, key: str) -> str:
        clean = "".join(character for character in key if character.isalnum() or character in "-_.")
        if not clean:
            raise ValueError("credential key is empty")
        return f"{self.namespace}/{clean}"
