from core.unicode_pipeline import REQUIRED_UI_LABELS, validate_unicode_catalog
from gui.localization import TEXT


def test_required_ui_strings_are_utf8_and_not_mojibake():
    assert validate_unicode_catalog() == ()
    for language, values in REQUIRED_UI_LABELS.items():
        catalog = TEXT[language]
        assert all(value in catalog.values() for value in values)
        assert all("�" not in value for value in catalog.values())


def test_director_console_source_has_no_mojibake_markers():
    source = open("gui/director_console.py", encoding="utf-8").read()
    assert "РљРѕРјР°РЅРґР°" not in source
    assert "РџСЂРѕС„РёР»СЊ" not in source
