import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractSlider, QApplication

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


def test_scrollbar_page_action_updates_follow_state():
    _app()
    widget = ChatWidget()
    widget.resize(760, 420)
    widget.show()
    for index in range(18):
        widget.add_message("employee", f"Сообщение {index}")
    QApplication.processEvents()
    bar = widget.messages.verticalScrollBar()
    bar.setValue(bar.maximum())

    bar.triggerAction(QAbstractSlider.SliderPageStepSub)
    QApplication.processEvents()
    assert widget._follow_new_messages is False

    bar.triggerAction(QAbstractSlider.SliderToMaximum)
    QApplication.processEvents()
    assert widget._follow_new_messages is True
    widget.deleteLater()


def test_message_rows_fit_content_with_small_reserve():
    _app()
    widget = ChatWidget()
    widget.resize(920, 620)
    widget.show()
    texts = [
        "Коротко.",
        "Строка 1\nСтрока 2\nСтрока 3",
        "Длинный проверочный текст " * 80,
    ]
    for text in texts:
        item = widget.add_message("employee", text)
        QApplication.processEvents()
        message = widget.messages.itemWidget(item)
        reserve = item.sizeHint().height() - message.sizeHint().height()
        assert 4 <= reserve <= 12
        required_body_height = message._wrapped_text_height(message.body.text(), message.body.width(), message.body)
        assert message.body.height() >= required_body_height
    widget.deleteLater()


def test_empty_composer_keeps_compact_initial_height():
    _app()
    widget = ChatWidget()
    widget.resize(920, 620)
    widget.show()
    QApplication.processEvents()
    assert widget.input.height() == 52
    widget.input.setPlainText("Строка\n" * 12)
    QApplication.processEvents()
    assert 52 < widget.input.height() <= 220
    widget.deleteLater()


def test_chat_status_strings_follow_interface_language():
    _app()
    widget = ChatWidget("uk")
    assert "Нові" in widget.new_messages_button.text()
    widget.set_goal_status(True, "Завершити перевірку", 2)
    assert widget.goal_banner.text().startswith("Мета:")
    widget.start_agent_typing("employee")
    assert "набирає повідомлення" in widget._parallel_typing["employee"]["label"].text()
    widget.set_language("en")
    assert widget.new_messages_button.text() == "↓  New messages"
    widget.deleteLater()


def test_theme_catalog_has_distinct_background_definitions():
    expected = {"dark", "dark_forest", "dark_ocean", "night_city", "warm_paper", "minimal", "light"}
    assert expected.issubset(ThemeManager.theme_ids())
    assert ThemeManager.definition("dark_forest").pattern == "forest"
    assert ThemeManager.definition("dark_ocean").pattern == "ocean"
    assert ThemeManager.definition("night_city").pattern == "city"
    assert ThemeManager.definition("minimal").pattern == "none"
    assert ThemeManager.native_chrome_colors("warm_paper")[0] is False


def test_long_chat_keeps_500_message_rows_usable():
    _app()
    widget = ChatWidget()
    widget.resize(1100, 760)
    widget.show()
    QApplication.processEvents()

    started = time.perf_counter()
    for index in range(500):
        widget.add_message("employee", f"Сообщение {index}: проверенный результат и короткое пояснение.")
    QApplication.processEvents()

    assert widget.messages.count() == 500
    assert widget.messages.verticalScrollBar().maximum() > 0
    assert time.perf_counter() - started < 15.0
    widget.resize(900, 620)
    widget.add_message("employee", "Сообщение после изменения размера")
    QApplication.processEvents()
    assert widget.messages.count() == 501
    widget.deleteLater()


def test_theme_text_contrast_is_readable_on_all_core_surfaces():
    def luminance(color: str) -> float:
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    def ratio(first: str, second: str) -> float:
        high, low = sorted((luminance(first), luminance(second)), reverse=True)
        return (high + 0.05) / (low + 0.05)

    for theme_id in ThemeManager.theme_ids():
        colors = ThemeManager.definition(theme_id).colors
        for surface in ("bg", "chat_bg", "surface", "surface_alt", "input", "dialog_bg"):
            assert ratio(colors["text"], colors[surface]) >= 7.0, (theme_id, surface)


def test_agent_typing_accepts_activity_status_text():
    _app()
    widget = ChatWidget()
    widget.start_agent_typing("runtime_v3", "создаю план")

    assert widget._parallel_typing["runtime_v3"]["status"] == "создаю план"
    assert "создаю план" in widget._parallel_typing["runtime_v3"]["label"].text()
    widget.deleteLater()
