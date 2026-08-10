from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from .path_guard import PathGuard


WORKSPACE_DIRS = ("Conversations", "Projects", "Images", "Documents", "Code", "Data", "Exports", "Imports", "Temp", "Logs", ".runtime", ".trash")


@dataclass(frozen=True)
class WorkspaceInfo:
    root: Path
    available: bool
    free_bytes: int


class WorkspaceService:
    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve(strict=False)
        self.guard = PathGuard(self.root)

    def ensure(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        for name in WORKSPACE_DIRS:
            (self.root / name).mkdir(parents=True, exist_ok=True)
        for name in ("chat", "gemini", "artifacts", "images", "development"):
            (self.root / ".runtime" / name).mkdir(parents=True, exist_ok=True)
        return self.root

    @property
    def chat_runtime(self) -> Path:
        return self.guard.validate_output_path(self.root / ".runtime" / "chat")

    @property
    def gemini_runtime(self) -> Path:
        return self.guard.validate_output_path(self.root / ".runtime" / "gemini")

    def info(self) -> WorkspaceInfo:
        try:
            usage = shutil.disk_usage(self.root if self.root.exists() else self.root.parent)
            return WorkspaceInfo(self.root, self.root.exists(), usage.free)
        except OSError:
            return WorkspaceInfo(self.root, False, 0)

    def resolve_safe_path(self, relative_path: str | Path) -> Path:
        return self.guard.resolve_safe_path(relative_path)

    def validate_existing_path(self, path: str | Path) -> Path:
        return self.guard.validate_existing_path(path)

    def validate_output_path(self, path: str | Path) -> Path:
        return self.guard.validate_output_path(path)

    def copy_input_to_workspace(self, source_path: Path) -> Path:
        source = source_path.expanduser().resolve(strict=True)
        if not source.is_file():
            raise ValueError("Вложение должно быть файлом")
        target_dir = self.root / "Imports"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = self.guard.validate_output_path(target_dir / source.name)
        if target.exists():
            target = self.guard.validate_output_path(target_dir / f"{source.stem}_{hashlib.sha256(str(source).encode()).hexdigest()[:8]}{source.suffix}")
        shutil.copy2(source, target)
        return target

    def create_artifact_path(self, category: str, filename: str) -> Path:
        if category not in WORKSPACE_DIRS:
            raise ValueError("Неизвестная категория артефакта")
        target = self.guard.resolve_safe_path(Path(category) / filename)
        target.parent.mkdir(parents=True, exist_ok=True)
        return self.guard.validate_output_path(target)
