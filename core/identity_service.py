from __future__ import annotations

import hashlib
import json
import logging
import shutil
from pathlib import Path
from typing import Any


class IdentityError(RuntimeError):
    pass


class IdentityService:
    def __init__(
        self,
        identity_path: Path,
        backup_path: Path | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.identity_path = identity_path
        self.backup_path = backup_path or identity_path.with_suffix(".initial.bak.json")
        self.logger = logger or logging.getLogger(__name__)
        self.initial_hash: str | None = None

    def load(self) -> dict[str, Any]:
        if not self.identity_path.exists():
            raise IdentityError(f"Файл личности не найден: {self.identity_path}")
        try:
            data = json.loads(self.identity_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise IdentityError("Файл личности поврежден: неверный JSON") from exc
        if not isinstance(data, dict):
            raise IdentityError("Файл личности должен содержать JSON-объект")
        self.validate(data)
        return data

    def validate(self, data: dict[str, Any]) -> None:
        if not str(data.get("full_name") or "").strip():
            raise IdentityError("Системный профиль повреждён: не указано имя")
        if not isinstance(data.get("current_year"), int):
            raise IdentityError("Системный профиль повреждён: неверный формат года")
        if data.get("identity_locked") is not True:
            raise IdentityError("Системный профиль повреждён: защита профиля должна быть включена")

    def sha256(self) -> str:
        digest = hashlib.sha256()
        with self.identity_path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def initialize_guard(self) -> str:
        data = self.load()
        self.validate(data)
        self.identity_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.backup_path.exists():
            shutil.copyfile(self.identity_path, self.backup_path)
        self.initial_hash = self.sha256()
        return self.initial_hash

    def check_for_change(self) -> bool:
        if self.initial_hash is None:
            self.initialize_guard()
            return False
        current_hash = self.sha256()
        changed = current_hash != self.initial_hash
        if changed:
            self.logger.warning("system_profile_changed sha256=%s", current_hash)
        return changed

    def restore_from_backup(self) -> None:
        if not self.backup_path.exists():
            raise IdentityError("Резервная копия системного профиля не найдена")
        shutil.copyfile(self.backup_path, self.identity_path)
        self.initial_hash = self.sha256()
