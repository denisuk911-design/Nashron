from pathlib import Path

from core.branding import BRAND_MARK_RELATIVE_PATH, BRAND_NAME, BRAND_TAGLINE, brand_mark_path


def test_branding_uses_one_canonical_team2050_mark():
    root = Path(__file__).resolve().parents[1]

    assert BRAND_NAME == "Team2050"
    assert BRAND_TAGLINE
    assert brand_mark_path(root) == root / BRAND_MARK_RELATIVE_PATH
    assert brand_mark_path(root).is_file()
