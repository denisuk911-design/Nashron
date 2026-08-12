import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtTest import QTest
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


def test_new_message_at_bottom_keeps_live_following():
    _app()
    widget = ChatWidget()
    widget.resize(760, 420)
    widget.show()
    for index in range(8):
        widget.add_message("roman", f"Сообщение {index}")
    QApplication.processEvents()
    bar = widget.messages.verticalScrollBar()
    bar.setValue(bar.maximum())

    widget.add_message("petr", "Новая проверка по задаче")
    QApplication.processEvents()

    assert widget._follow_new_messages is True
    assert widget.new_messages_button.isHidden()
    widget.deleteLater()


def test_history_reading_is_not_moved_by_new_messages_or_resize():
    _app()
    widget = ChatWidget()
    widget.resize(760, 420)
    widget.show()
    for index in range(12):
        widget.add_message("roman", f"История {index}")
    QApplication.processEvents()
    bar = widget.messages.verticalScrollBar()
    bar.setValue(max(bar.minimum(), bar.maximum() - 160))
    widget._on_user_scroll_started()
    widget._on_user_scroll_delta(120)
    QApplication.processEvents()
    position = bar.value()

    widget.add_message("petr", "Новое сообщение не должно утащить историю")
    widget.resize(900, 500)
    QApplication.processEvents()

    assert widget._follow_new_messages is False
    assert bar.value() == position
    assert not widget.new_messages_button.isHidden()
    widget.deleteLater()


def test_returning_to_bottom_restores_follow_after_multiple_messages():
    _app()
    widget = ChatWidget()
    widget.resize(760, 420)
    widget.show()
    for index in range(12):
        widget.add_message("roman", f"История {index}")
    QApplication.processEvents()
    bar = widget.messages.verticalScrollBar()
    bar.setValue(max(bar.minimum(), bar.maximum() - 180))
    widget._on_user_scroll_started()
    widget._on_user_scroll_delta(120)
    QApplication.processEvents()
    assert widget._follow_new_messages is False

    bar.setValue(bar.maximum())
    widget._on_user_scroll_finished()
    assert widget._follow_new_messages is True

    widget.add_message("petr", "Следующее сообщение")
    QApplication.processEvents()
    assert widget._follow_new_messages is True
    assert widget.new_messages_button.isHidden()
    widget.deleteLater()


def test_resize_at_bottom_preserves_follow_state():
    _app()
    widget = ChatWidget()
    widget.resize(760, 420)
    widget.show()
    for index in range(8):
        widget.add_message("roman", f"Сообщение {index}")
    QApplication.processEvents()
    bar = widget.messages.verticalScrollBar()
    bar.setValue(bar.maximum())
    widget.resize(980, 560)
    QApplication.processEvents()

    assert widget._follow_new_messages is True
    QTest.qWait(520)
    QApplication.processEvents()
    assert widget._is_at_bottom()
    widget.deleteLater()


def test_smooth_wheel_scroll_returns_to_following_at_bottom():
    _app()
    widget = ChatWidget()
    widget.resize(760, 420)
    widget.show()
    for index in range(18):
        widget.add_message("roman", f"Сообщение {index}")
    QApplication.processEvents()
    bar = widget.messages.verticalScrollBar()
    bar.setValue(bar.maximum())

    widget._on_user_scroll_started()
    widget._on_user_scroll_delta(240)
    bar.setValue(max(bar.minimum(), bar.maximum() - 240))
    widget._on_user_scroll_finished()
    assert widget._follow_new_messages is False

    bar.setValue(bar.maximum())
    widget._on_user_scroll_finished()
    QTest.qWait(20)
    assert widget._follow_new_messages is True
    widget.deleteLater()


def test_theme_catalog_has_distinct_background_definitions():
    expected = {"dark", "dark_forest", "dark_ocean", "night_city", "warm_paper", "minimal", "light"}
    assert expected.issubset(ThemeManager.theme_ids())
    assert ThemeManager.native_chrome_colors("warm_paper")[0] is False
