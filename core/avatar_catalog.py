from __future__ import annotations

from pathlib import Path


SUPPORTED_AVATAR_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def list_avatar_files(avatar_dir: Path | None) -> list[Path]:
    """Return selectable avatar assets while excluding source/contact sheets."""
    if avatar_dir is None or not avatar_dir.exists():
        return []
    return sorted(
        path
        for path in avatar_dir.iterdir()
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_AVATAR_SUFFIXES
        and "sheet" not in path.stem.lower()
    )
