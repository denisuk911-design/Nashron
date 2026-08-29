from __future__ import annotations

from pathlib import Path


BRAND_NAME = "Luminifera"
BRAND_TAGLINE = "Ваша AI-команда"
BRAND_MARK_RELATIVE_PATH = Path("data") / "branding" / "team2050-mark.png"


def brand_mark_path(resource_root: Path) -> Path:
    """Resolve the bundled brand mark in source and packaged builds."""
    return resource_root / BRAND_MARK_RELATIVE_PATH
