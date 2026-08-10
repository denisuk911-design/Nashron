from __future__ import annotations

import os
from pathlib import Path


class PathGuardError(ValueError):
    pass


class PathGuard:
    """Validates every path crossing the Roman2050 workspace boundary."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser().resolve(strict=False)

    def resolve_safe_path(self, relative_path: str | Path) -> Path:
        raw = str(relative_path)
        candidate = Path(raw)
        if candidate.is_absolute() or raw.startswith(("\\\\", "//")):
            raise PathGuardError("Абсолютные и сетевые пути запрещены")
        if any(part == ".." for part in candidate.parts):
            raise PathGuardError("Переходы через .. запрещены")
        if ":" in raw:
            raise PathGuardError("Пути с двоеточием и NTFS alternate data streams запрещены")
        resolved = (self.workspace_root / candidate).resolve(strict=False)
        self._assert_inside(resolved)
        return resolved

    def validate_existing_path(self, path: str | Path) -> Path:
        resolved = self._resolve_for_validation(path)
        if not resolved.exists():
            raise PathGuardError("Файл или каталог не существует")
        self._assert_inside(resolved)
        return resolved

    def validate_output_path(self, path: str | Path) -> Path:
        resolved = self._resolve_for_validation(path)
        self._assert_inside(resolved)
        return resolved

    def _resolve_for_validation(self, path: str | Path) -> Path:
        candidate = Path(path)
        if not candidate.is_absolute():
            return self.resolve_safe_path(candidate)
        if os.name == "nt" and candidate.drive and candidate.drive != self.workspace_root.drive:
            raise PathGuardError("Другие диски запрещены")
        return candidate.expanduser().resolve(strict=False)

    def _assert_inside(self, resolved: Path) -> None:
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError as exc:
            raise PathGuardError("Путь выходит за пределы рабочей папки") from exc
        if resolved == self.workspace_root:
            return
        for parent in (resolved, *resolved.parents):
            if parent == self.workspace_root:
                break
            if parent.is_symlink():
                target = parent.resolve(strict=False)
                try:
                    target.relative_to(self.workspace_root)
                except ValueError as exc:
                    raise PathGuardError("Симлинки наружу запрещены") from exc
