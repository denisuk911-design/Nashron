from datetime import date
from pathlib import Path

from core.theme_background_service import collection_files, select_background


def test_bundled_theme_collections_have_multiple_original_images():
    root = Path(__file__).resolve().parents[1]
    for theme in ("city", "dark_forest", "dark_ocean", "mountains", "night_city", "space"):
        files = collection_files(root, theme)
        assert len(files) >= 2
        assert all(path.stat().st_size > 100_000 for path in files)


def test_daily_background_is_stable_and_cycle_changes_selection():
    root = Path(__file__).resolve().parents[1]
    selected = select_background(root, "space", "daily", today=date(2026, 8, 13))
    repeated = select_background(root, "space", "daily", today=date(2026, 8, 13))
    cycled = select_background(root, "space", "remember", selected, cycle=1)

    assert selected == repeated
    assert cycled != selected
