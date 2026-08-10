from gui.theme.theme_manager import ThemeManager


def test_light_and_dark_stylesheets_are_distinct():
    dark = ThemeManager.stylesheet("dark")
    light = ThemeManager.stylesheet("light")

    assert dark != light
    assert "#0f141b" in dark
    assert "#f5f7fb" in light


def test_dialogs_have_explicit_theme_colors():
    dark = ThemeManager.stylesheet("dark")

    assert "QMessageBox" in dark
    assert "QDialog QLabel" in dark
    assert "QComboBox" in dark
