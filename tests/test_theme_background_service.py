from datetime import date
from pathlib import Path

from core.theme_background_service import collection_files, pending_background_cycle, select_background


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


def test_background_cycle_is_consumed_once_and_legacy_profile_does_not_advance():
    legacy = {"chat_background_cycle": 7}

    cycle, pending, migrated = pending_background_cycle(legacy)

    assert (cycle, pending, migrated) == (7, False, True)
    assert legacy["chat_background_cycle_applied"] == 7

    legacy["chat_background_cycle"] = 8
    cycle, pending, migrated = pending_background_cycle(legacy)
    assert (cycle, pending, migrated) == (8, True, False)

    legacy["chat_background_cycle_applied"] = cycle
    assert pending_background_cycle(legacy) == (8, False, False)
