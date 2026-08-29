from __future__ import annotations

import pytest

from ui_luminifera.settings import LuminiferaSettingsDialog


def test_product_settings_expose_translated_sections_and_persist_values():
    widgets = pytest.importorskip("PySide6.QtWidgets")
    app = widgets.QApplication.instance() or widgets.QApplication([])
    dialog = LuminiferaSettingsDialog({"interface_language": "ru", "theme": "dark", "workspace_root": "C:/work"})
    assert dialog.windowTitle() == "Настройки Luminifera"
    assert [dialog.findChild(widgets.QTabWidget).tabText(i) for i in range(6)] == ["Основные", "Внешний вид", "Звук", "Подключения", "Данные", "Дополнительно"]
    dialog.theme.setCurrentIndex(dialog.theme.findData("light"))
    dialog.language.setCurrentIndex(dialog.language.findData("uk"))
    values = dialog.values()
    assert values["theme"] == "light"
    assert values["interface_language"] == "uk"
    dialog.close()
