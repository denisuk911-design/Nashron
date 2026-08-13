from __future__ import annotations

from datetime import date
from pathlib import Path
import hashlib
import random


THEME_COLLECTIONS = {
    "dark": "space",
    "space": "space",
    "dark_graphite": "mountains",
    "mountains": "mountains",
    "dark_ocean": "ocean",
    "dark_forest": "forest",
    "city": "city",
    "night_city": "night_city",
}


def collection_files(resource_root: Path, theme_id: str) -> list[Path]:
    collection = THEME_COLLECTIONS.get(theme_id)
    if not collection:
        return []
    directory = resource_root / "data" / "theme_backgrounds" / collection
    return sorted(path for path in directory.glob("*.png") if path.is_file())


def select_background(
    resource_root: Path,
    theme_id: str,
    rotation_mode: str = "launch",
    remembered_path: str = "",
    cycle: int = 0,
    today: date | None = None,
) -> str:
    files = collection_files(resource_root, theme_id)
    if not files:
        return ""
    remembered = Path(remembered_path) if remembered_path else None
    if rotation_mode == "remember" and remembered in files:
        base_index = files.index(remembered)
    elif rotation_mode == "daily":
        day = (today or date.today()).isoformat()
        digest = hashlib.sha256(f"{theme_id}:{day}".encode("utf-8")).digest()
        base_index = int.from_bytes(digest[:4], "big") % len(files)
    else:
        base_index = random.randrange(len(files))
    return str(files[(base_index + max(0, int(cycle))) % len(files)])
