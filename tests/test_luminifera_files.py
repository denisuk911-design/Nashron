from __future__ import annotations

import pytest

from core.luminifera_files_service import ProductArtifact
from ui_luminifera.files import FilesBrowser


def test_files_browser_renders_empty_state_and_artifact_metadata():
    widgets = pytest.importorskip("PySide6.QtWidgets")
    app = widgets.QApplication.instance() or widgets.QApplication([])
    browser = FilesBrowser("ru")
    browser.render(())
    assert browser.heading.text() == "Файлы и результаты"
    assert browser.list.count() == 1
    browser.render((ProductArtifact("docs/spec.md", "Документ", "Проверен", "2026-08-29T12:30:00"),))
    assert browser.list.count() == 1
    card = browser.list.itemWidget(browser.list.item(0))
    assert card is not None
    assert "docs/spec.md" in card.findChild(widgets.QLabel, "luminiferaFileTitle").text()
    assert browser._artifact_type_label("BOM") == "Спецификация"
    assert browser._status_label("VERIFIED") == "Проверен"
    browser.set_language("en")
    assert browser.heading.text() == "Files and results"
    assert browser._artifact_type_label("BOM") == "Bill of materials"
    browser.close()
