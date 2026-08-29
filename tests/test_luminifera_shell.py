from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QWidget

from core.branding import BRAND_NAME
from core.conversation_mode import ConversationMode
from tests.test_startup_bootstrap import _build_window, _make_settings_service
from ui_luminifera.app_shell import LuminiferaShell


def test_luminifera_shell_is_default_product_surface(tmp_path, monkeypatch):
    window = _build_window(_make_settings_service(tmp_path), monkeypatch)

    assert BRAND_NAME == "Luminifera"
    assert window.windowTitle() == "Luminifera"
    assert isinstance(window.centralWidget(), LuminiferaShell)
    assert window.product_shell is window.centralWidget()
    assert window.organization_selector.parent() is not None

    window.close()


def test_luminifera_shell_has_readable_primary_navigation(tmp_path, monkeypatch):
    window = _build_window(_make_settings_service(tmp_path), monkeypatch)
    buttons = window.product_shell._navigation_buttons

    assert set(buttons) == {"home", "chat", "work", "team", "files", "iris"}
    assert [buttons[key].text().split()[-1] for key in ("home", "chat", "work", "files", "iris")] == [
        "Главная",
        "Чат",
        "Работа",
        "Файлы",
        "Iris",
    ]
    assert buttons["home"].isChecked()

    buttons["work"].click()
    assert window.conversation_mode == ConversationMode.WORK
    assert buttons["work"].isChecked()
    assert not buttons["chat"].isChecked()

    window.close()


def test_luminifera_product_tree_hides_legacy_technical_toolbar(tmp_path, monkeypatch):
    window = _build_window(_make_settings_service(tmp_path), monkeypatch)
    product_chrome = [
        window.product_shell.findChild(QWidget, "luminiferaSidebar"),
        window.product_shell.findChild(QWidget, "luminiferaTopbar"),
    ]
    text_widgets = []
    for surface in product_chrome:
        assert surface is not None
        text_widgets.extend(surface.findChildren(QLabel))
        text_widgets.extend(surface.findChildren(QPushButton))
    product_text = " ".join(widget.text() for widget in text_widgets if widget.text())

    for forbidden in ("Codex", "Gemini", "Guide", "Supervisor", "Маршрут", "Контекст", "Рабочая папка"):
        assert forbidden not in product_text
    assert "ИИ готов" in product_text or "Нужен вход" in product_text
    assert "Iris" in product_text

    window.close()
