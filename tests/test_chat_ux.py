import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gui.chat_widget import ChatWidget
from gui.theme import ThemeManager


def _app():
    return QApplication.instance() or QApplication([])


def test_autoscroll_follow_is_restored_at_bottom():
    _app()
    widget = ChatWidget()
    bar = widget.messages.verticalScrollBar()
    bar.setRange(0, 600)
    bar.setValue(600)

    assert widget._is_at_bottom()
    assert widget._follow_new_messages is True

    widget._on_user_scroll_delta(120)
    assert widget._follow_new_messages is False
    bar.setValue(600)
    widget._on_user_scroll_finished()

    assert widget._is_at_bottom()
    assert widget._follow_new_messages is True
    widget.deleteLater()


def test_new_message_indicator_jump_restores_follow():
    _app()
    widget = ChatWidget()
    bar = widget.messages.verticalScrollBar()
    bar.setRange(0, 600)
    bar.setValue(300)
    widget._on_user_scroll_delta(120)

    assert not widget.new_messages_button.isHidden()
    widget._jump_to_new_messages()

    assert widget._follow_new_messages is True
    assert widget.new_messages_button.isHidden()
    widget.deleteLater()


def test_theme_catalog_has_distinct_background_definitions():
    expected = {"dark", "dark_forest", "dark_ocean", "night_city", "warm_paper", "minimal", "light"}
    assert expected.issubset(ThemeManager.theme_ids())
    assert ThemeManager.native_chrome_colors("warm_paper")[0] is False
