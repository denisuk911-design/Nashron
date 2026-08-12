from __future__ import annotations

import re
from collections import deque
from datetime import datetime

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent, QWheelEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QComboBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.response_cleaner import ResponseCleaner
from gui.chat.message_widget import MessageWidget


class MessageList(QListWidget):
    copy_requested = Signal()
    user_scrolled = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._wheel_animation: QPropertyAnimation | None = None
        self._wheel_target: int | None = None

    def wheelEvent(self, event: QWheelEvent) -> None:
        pixel_delta = event.pixelDelta().y()
        angle_delta = event.angleDelta().y()
        delta = pixel_delta if pixel_delta else int(angle_delta * 1.15)
        if not delta:
            super().wheelEvent(event)
            return

        bar = self.verticalScrollBar()
        if bar.maximum() <= bar.minimum():
            super().wheelEvent(event)
            return

        self.user_scrolled.emit()
        if self._wheel_animation is not None:
            current_target = self._wheel_target if self._wheel_target is not None else bar.value()
            self._wheel_animation.stop()
            self._wheel_animation.deleteLater()
            self._wheel_animation = None
        else:
            current_target = bar.value()
        target = max(bar.minimum(), min(bar.maximum(), int(current_target - delta)))
        if target == bar.value():
            event.accept()
            return

        animation = QPropertyAnimation(bar, b"value", self)
        animation.setStartValue(bar.value())
        animation.setEndValue(target)
        animation.setDuration(max(300, min(780, 260 + abs(target - bar.value()) * 2)))
        animation.setEasingCurve(QEasingCurve.OutCubic)
        animation.finished.connect(lambda: self._finish_wheel_animation(animation))
        self._wheel_animation = animation
        self._wheel_target = target
        animation.start()
        event.accept()

    def _finish_wheel_animation(self, animation: QPropertyAnimation) -> None:
        if self._wheel_animation is animation:
            self._wheel_animation = None
            self._wheel_target = None
        animation.deleteLater()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_C and event.modifiers() & Qt.ControlModifier:
            self.copy_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class MessageInput(QTextEdit):
    send_requested = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not event.modifiers() & Qt.ShiftModifier:
            self.send_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class ChatWidget(QWidget):
    send_requested = Signal(str)
    stop_requested = Signal()
    attach_requested = Signal()
    copy_requested = Signal()

    def __init__(self, language: str = "ru") -> None:
        super().__init__()
        self.language = language if language in {"ru", "uk", "en"} else "ru"
        self._typing_item: QListWidgetItem | None = None
        self._typing_label: QLabel | None = None
        self._typing_frame = 0
        self._parallel_typing: dict[str, dict[str, object]] = {}
        self._stream_item: QListWidgetItem | None = None
        self._stream_widget: MessageWidget | None = None
        self._stream_role = "roman"
        self._stream_text = ""
        self._stream_final_text = ""
        self._typewriter_queue: deque[str] = deque()
        self._completed_stream_item: QListWidgetItem | None = None
        self._completed_stream_widget: MessageWidget | None = None
        self._completed_stream_role = ""
        self._completed_stream_text = ""
        self._scroll_animation: QPropertyAnimation | None = None
        self._agent_labels = {"user": "Вы", "roman": "Роман", "petr": "Петр", "system": "Система"}
        self._agent_avatars: dict[str, str] = {}
        self._agent_titles: dict[str, str] = {"user": "Владелец"}
        self._recipient_keys: list[str] = []

        self.typing_timer = QTimer(self)
        self.typing_timer.setInterval(260)
        self.typing_timer.timeout.connect(self._advance_typing)
        self.typewriter_timer = QTimer(self)
        self.typewriter_timer.setInterval(16)
        self.typewriter_timer.timeout.connect(self._flush_typewriter)

        self.messages = MessageList()
        self.messages.setObjectName("messageList")
        self.messages.setWordWrap(True)
        self.messages.setUniformItemSizes(False)
        self.messages.setSelectionMode(QListWidget.ExtendedSelection)
        self.messages.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.messages.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.messages.verticalScrollBar().rangeChanged.connect(self._on_scroll_range_changed)
        self.messages.user_scrolled.connect(self._cancel_output_scroll)
        self.messages.copy_requested.connect(self.copy_requested.emit)

        self.input = MessageInput()
        self.input.setObjectName("messageInput")
        self.input.setPlaceholderText("Напишите в отдел...")
        self.input.setAcceptRichText(False)
        self.input.setMinimumHeight(52)
        self.input.setMaximumHeight(220)
        self.input.send_requested.connect(self._emit_send)
        self.input.textChanged.connect(self._resize_input)

        self.send_button = QPushButton("➤")
        self.send_button.setObjectName("sendButton")
        self.send_button.setFixedSize(42, 36)
        self.stop_button = QPushButton("Остановить")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setVisible(False)

        self.send_button.clicked.connect(self._emit_send)
        self.stop_button.clicked.connect(self.stop_requested.emit)

        self.goal_banner = QLabel()
        self.goal_banner.setObjectName("goalBanner")
        self.goal_banner.setWordWrap(True)
        self.goal_banner.setVisible(False)

        composer = QWidget()
        composer.setObjectName("composer")
        composer_layout = QVBoxLayout(composer)
        composer_layout.setContentsMargins(10, 8, 10, 8)
        composer_layout.setSpacing(4)
        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        self.attach_button = QPushButton("＋")
        self.attach_button.setObjectName("roundIconButton")
        self.attach_button.setToolTip("Прикрепить файл")
        self.attach_button.setFixedSize(40, 40)
        self.attach_button.clicked.connect(self.attach_requested.emit)
        input_row.addWidget(self.attach_button)
        input_row.addWidget(self.input, 1)
        input_row.addWidget(self.send_button)
        composer_layout.addLayout(input_row)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(2)
        self.recipient_selector = QComboBox()
        self.recipient_selector.setObjectName("routingSelector")
        self.recipient_selector.setToolTip("Кому адресовано сообщение")
        self.recipient_selector.addItem("Кому: Авто", None)
        self.mode_selector = QComboBox()
        self.mode_selector.setObjectName("routingSelector")
        self.mode_selector.setToolTip("Режим участия сотрудников")
        self.mode_selector.addItem("Режим: Авто", "auto")
        self.mode_selector.addItem("Цель", "goal")
        self.mode_selector.addItem("Работа", "work")
        self.mode_selector.addItem("Общение", "social")
        self.mode_selector.addItem("Обсуждение", "discussion")
        self.mode_selector.addItem("Только выбранный", "selected")
        self.mode_selector.addItem("Обсуждение команды", "team")
        self.mode_selector.addItem("Проверка", "review")
        self.mode_selector.addItem("Без ответа", "silent")
        toolbar.addWidget(self.recipient_selector)
        toolbar.addWidget(self.mode_selector)
        self.copy_button = QPushButton("Копировать чат")
        self.copy_button.setObjectName("smallAction")
        self.copy_button.setToolTip("Скопировать выбранные сообщения с именами и временем")
        self.copy_button.clicked.connect(self.copy_requested.emit)
        toolbar.addWidget(self.copy_button)
        toolbar.addStretch(1)
        toolbar.addWidget(self.stop_button)
        composer_layout.addLayout(toolbar)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.messages, 1)
        layout.addWidget(self.goal_banner)
        layout.addWidget(composer)
        self.set_language(self.language)

    def set_language(self, language: str) -> None:
        self.language = language if language in {"ru", "uk", "en"} else "ru"
        labels = {
            "ru": {
                "placeholder": "Напишите в отдел...",
                "copy": "Копировать чат",
                "copy_tip": "Скопировать выбранные сообщения с именами и временем",
                "recipient": "Кому: Авто",
                "recipient_tip": "Кому адресовано сообщение",
                "mode_tip": "Режим участия сотрудников",
                "modes": [("Режим: Авто", "auto"), ("Цель", "goal"), ("Работа", "work"), ("Общение", "social"), ("Обсуждение", "discussion"), ("Только выбранный", "selected"), ("Обсуждение команды", "team"), ("Проверка", "review"), ("Без ответа", "silent")],
            },
            "uk": {
                "placeholder": "Напишіть у відділ...",
                "copy": "Копіювати чат",
                "copy_tip": "Скопіювати вибрані повідомлення з іменами й часом",
                "recipient": "Кому: Авто",
                "recipient_tip": "Кому адресоване повідомлення",
                "mode_tip": "Режим участі співробітників",
                "modes": [("Режим: Авто", "auto"), ("Мета", "goal"), ("Робота", "work"), ("Спілкування", "social"), ("Обговорення", "discussion"), ("Лише вибраний", "selected"), ("Обговорення команди", "team"), ("Перевірка", "review"), ("Без відповіді", "silent")],
            },
            "en": {
                "placeholder": "Write to the department...",
                "copy": "Copy chat",
                "copy_tip": "Copy selected messages with names and timestamps",
                "recipient": "To: Auto",
                "recipient_tip": "Who the message is addressed to",
                "mode_tip": "Employee participation mode",
                "modes": [("Mode: Auto", "auto"), ("Goal", "goal"), ("Work", "work"), ("Social", "social"), ("Discussion", "discussion"), ("Selected only", "selected"), ("Team discussion", "team"), ("Review", "review"), ("No response", "silent")],
            },
        }[self.language]
        self.input.setPlaceholderText(labels["placeholder"])
        self.copy_button.setText(labels["copy"])
        self.copy_button.setToolTip(labels["copy_tip"])
        self.recipient_selector.setToolTip(labels["recipient_tip"])
        current_recipient = self.recipient_selector.currentData()
        self.recipient_selector.setItemText(0, labels["recipient"])
        if current_recipient is not None:
            index = self.recipient_selector.findData(current_recipient)
            if index >= 0:
                self.recipient_selector.setCurrentIndex(index)
        current_mode = self.mode_selector.currentData()
        self.mode_selector.blockSignals(True)
        self.mode_selector.clear()
        for label, value in labels["modes"]:
            self.mode_selector.addItem(label, value)
        index = self.mode_selector.findData(current_mode or "auto")
        self.mode_selector.setCurrentIndex(index if index >= 0 else 0)
        self.mode_selector.blockSignals(False)
        self.mode_selector.setToolTip(labels["mode_tip"])

    def add_message(self, role: str, content: str, message_id: int | None = None, created_at: str = "") -> QListWidgetItem:
        should_follow = self._should_follow_output()
        item = QListWidgetItem()
        timestamp = created_at or datetime.now().strftime("%H:%M")
        widget = MessageWidget(
            role,
            content,
            timestamp,
            self._agent_labels.get(role),
            self._agent_avatars.get(role),
            self._agent_titles.get(role),
        )
        item.setData(Qt.UserRole, {"id": message_id, "role": role, "content": content, "created_at": timestamp})
        item.setData(Qt.UserRole + 1, role)
        self.messages.addItem(item)
        self.messages.setItemWidget(item, widget)
        item.setSizeHint(self._message_item_size(widget))
        self._resize_message_widgets()
        self._follow_output_if_needed(should_follow)
        return item

    def transcript_text(self, selected_only: bool = True) -> str:
        items = self.messages.selectedItems() if selected_only else []
        if not items:
            items = [self.messages.item(index) for index in range(self.messages.count())]
        lines: list[str] = []
        for item in items:
            data = item.data(Qt.UserRole)
            if not isinstance(data, dict):
                continue
            content = str(data.get("content") or "").strip()
            if not content:
                continue
            role = str(data.get("role") or "")
            name = self._agent_labels.get(role, role)
            title = self._agent_titles.get(role, "")
            timestamp = str(data.get("created_at") or "")
            suffix = f" ({title})" if title else ""
            prefix = f"[{timestamp}] " if timestamp else ""
            lines.append(f"{prefix}{name}{suffix}:\n{content}")
        return "\n\n".join(lines)

    def set_agent_labels(
        self,
        labels: dict[str, str],
        avatars: dict[str, str] | None = None,
        titles: dict[str, str] | None = None,
    ) -> None:
        self._agent_labels = {"user": "Вы", "system": "Система", **labels}
        self._agent_avatars = avatars or {}
        self._agent_titles = {"user": "Владелец", **(titles or {})}
        current_key = self.recipient_selector.currentData() if hasattr(self, "recipient_selector") else None
        self.recipient_selector.blockSignals(True)
        self.recipient_selector.clear()
        self.recipient_selector.addItem("Кому: Авто", None)
        for key, label in sorted(labels.items(), key=lambda item: item[1].lower()):
            self.recipient_selector.addItem(label, key)
        if current_key:
            index = self.recipient_selector.findData(current_key)
            if index >= 0:
                self.recipient_selector.setCurrentIndex(index)
        self.recipient_selector.blockSignals(False)

    def routing_options(self) -> dict[str, object]:
        mode = self.mode_selector.currentData()
        recipient = self.recipient_selector.currentData()
        return {
            "recipient_key": recipient if isinstance(recipient, str) else None,
            "only_selected": mode == "selected",
            "team_discussion": mode == "team",
            "review_request": mode == "review",
            "no_response": mode == "silent",
            "goal_mode": mode == "goal",
            "conversation_mode": {
                "work": "WORK",
                "social": "SOCIAL",
                "discussion": "TEAM_DISCUSSION",
                "team": "TEAM_DISCUSSION",
                "review": "REVIEW",
            }.get(str(mode), ""),
        }

    def goal_mode_requested(self) -> bool:
        return self.mode_selector.currentData() == "goal"

    def set_goal_status(self, active: bool, goal: str = "", turn: int = 0) -> None:
        if not active:
            self.goal_banner.clear()
            self.goal_banner.setVisible(False)
            return
        suffix = f" · ход {turn}" if turn else ""
        self.goal_banner.setText(f"Цель: {goal.strip()}{suffix}")
        self.goal_banner.setVisible(True)

    def clear_messages(self) -> None:
        self.stop_typing_indicator()
        self.stop_all_agent_typing()
        self.typewriter_timer.stop()
        self._stream_item = None
        self._stream_widget = None
        self._stream_role = "roman"
        self._stream_text = ""
        self._stream_final_text = ""
        self._completed_stream_item = None
        self._completed_stream_widget = None
        self._completed_stream_role = ""
        self._completed_stream_text = ""
        self._typewriter_queue.clear()
        self.messages.clear()

    def set_busy(self, busy: bool, mood_source: str = "") -> None:
        self.send_button.setVisible(not busy)
        self.stop_button.setVisible(busy)
        self.input.setEnabled(True)
        self.focus_input_later()
        if busy:
            self.start_typing_indicator(mood_source)
        else:
            self.stop_typing_indicator()
            self.stop_all_agent_typing()

    def start_agent_typing(self, agent_key: str) -> None:
        self.stop_agent_typing(agent_key)
        item = QListWidgetItem()
        item.setFlags(Qt.NoItemFlags)
        label = QLabel()
        label.setObjectName("typingBubble")
        label.setMinimumHeight(34)
        label.setTextFormat(Qt.PlainText)
        self.messages.addItem(item)
        self.messages.setItemWidget(item, label)
        self._parallel_typing[agent_key] = {"item": item, "label": label, "status": "", "frame": 0}
        if not self.typing_timer.isActive():
            self.typing_timer.start()
        self._advance_typing()

    def set_agent_activity_status(self, agent_key: str, status: str) -> None:
        if agent_key not in self._parallel_typing:
            self.start_agent_typing(agent_key)
        state = self._parallel_typing.get(agent_key)
        if state is not None:
            state["status"] = status.strip()
            self._advance_typing()

    def stop_agent_typing(self, agent_key: str) -> None:
        state = self._parallel_typing.pop(agent_key, None)
        if state is not None:
            item = state.get("item")
            if isinstance(item, QListWidgetItem):
                row = self.messages.row(item)
                if row >= 0:
                    self.messages.takeItem(row)
        if not self._parallel_typing and self._typing_item is None:
            self.typing_timer.stop()

    def stop_all_agent_typing(self) -> None:
        for agent_key in list(self._parallel_typing):
            self.stop_agent_typing(agent_key)

    def focus_input_later(self) -> None:
        QTimer.singleShot(0, lambda: self.input.setFocus(Qt.OtherFocusReason))
        QTimer.singleShot(60, lambda: self.input.setFocus(Qt.OtherFocusReason))

    def start_typing_indicator(self, mood_source: str = "") -> None:
        self.stop_typing_indicator()
        should_follow = self._should_follow_output()
        self._typing_frame = 0
        self._typing_item = QListWidgetItem()
        self._typing_item.setFlags(Qt.NoItemFlags)
        self._typing_label = QLabel()
        self._typing_label.setObjectName("typingBubble")
        self._typing_label.setMinimumHeight(34)
        self._typing_label.setTextFormat(Qt.PlainText)
        self.messages.addItem(self._typing_item)
        self.messages.setItemWidget(self._typing_item, self._typing_label)
        self._typing_item.setSizeHint(self._typing_label.sizeHint() + QSize(0, 10))
        self.typing_timer.start()
        self._advance_typing()
        self._follow_output_if_needed(should_follow)

    def stop_typing_indicator(self) -> None:
        self.typing_timer.stop()
        if self._typing_item is None:
            return
        row = self.messages.row(self._typing_item)
        if row >= 0:
            self.messages.takeItem(row)
        self._typing_item = None
        self._typing_label = None

    def _advance_typing(self) -> None:
        if self._typing_label is not None:
            dots = " •" * (1 + self._typing_frame % 3)
            self._typing_label.setText(f"{self._agent_short_name()} набирает сообщение{dots}")
            if self._typing_item is not None:
                self._typing_item.setSizeHint(self._typing_label.sizeHint() + QSize(0, 10))
        for agent_key, state in self._parallel_typing.items():
            label = state.get("label")
            item = state.get("item")
            if not isinstance(label, QLabel) or not isinstance(item, QListWidgetItem):
                continue
            frame = int(state.get("frame") or 0)
            dots = " •" * (1 + frame % 3)
            name = self._agent_labels.get(agent_key, agent_key)
            status = str(state.get("status") or "набирает сообщение")
            label.setText(f"{name}: {status}{dots}")
            item.setSizeHint(label.sizeHint() + QSize(0, 10))
            state["frame"] = frame + 1
        self._typing_frame += 1

    def set_stream_role(self, role: str) -> None:
        self._stream_role = role

    def begin_roman_response(self) -> None:
        if self._stream_item is not None:
            return
        self.stop_typing_indicator()
        self._stream_text = ""
        self._stream_item = self.add_message(self._stream_role, "")
        self._stream_widget = self.messages.itemWidget(self._stream_item)

    def append_roman_delta(self, delta: str) -> None:
        if not delta:
            return
        self.begin_roman_response()
        self._typewriter_queue.extend(delta)
        if not self.typewriter_timer.isActive():
            self.typewriter_timer.start()

    def finish_roman_response(self, final_text: str) -> None:
        self.stop_typing_indicator()
        if self._stream_item is None:
            if self._replace_completed_stream(final_text):
                return
            if self._replace_recent_stream_placeholder(final_text):
                return
            if self._replace_recent_stream_duplicate(final_text):
                return
            self.begin_roman_response()
            self._stream_final_text = final_text
            self._typewriter_queue.extend(final_text)
            if not self.typewriter_timer.isActive():
                self.typewriter_timer.start()
            return
        self._stream_final_text = final_text
        if final_text.startswith(self._stream_text):
            self._typewriter_queue.clear()
            self._typewriter_queue.extend(final_text[len(self._stream_text) :])
        elif final_text != self._stream_text:
            self._typewriter_queue.clear()
            self._stream_text = final_text
            self._update_stream_item()

    def _flush_typewriter(self) -> None:
        if self._stream_item is None:
            self.typewriter_timer.stop()
            self._typewriter_queue.clear()
            return
        for _ in range(min(18, len(self._typewriter_queue))):
            self._stream_text += self._typewriter_queue.popleft()
        self._update_stream_item()
        if not self._typewriter_queue:
            self.typewriter_timer.stop()
            self._completed_stream_item = self._stream_item
            self._completed_stream_widget = self._stream_widget
            self._completed_stream_role = self._stream_role
            self._completed_stream_text = self._stream_text
            self._stream_item = None
            self._stream_widget = None
            self._stream_final_text = ""

    def _update_stream_item(self) -> None:
        if self._stream_item is None:
            return
        should_follow = self._should_follow_output()
        widget = self._stream_widget or self.messages.itemWidget(self._stream_item)
        if isinstance(widget, MessageWidget):
            widget.set_content(self._visible_stream_text(self._stream_text))
            self._stream_widget = widget
            self._stream_item.setSizeHint(self._message_item_size(widget))
        self._stream_item.setData(Qt.UserRole, {"id": None, "role": self._stream_role, "content": self._visible_stream_text(self._stream_text)})
        self._follow_output_if_needed(should_follow)

    def set_activity_status(self, status: str) -> None:
        clean = status.strip()
        if not clean:
            self.clear_activity_status()
            return
        self.begin_roman_response()
        widget = self._stream_widget or self.messages.itemWidget(self._stream_item)
        if isinstance(widget, MessageWidget):
            should_follow = self._should_follow_output()
            widget.set_activity(clean)
            self._stream_widget = widget
            if self._stream_item is not None:
                self._stream_item.setSizeHint(self._message_item_size(widget))
            self._follow_output_if_needed(should_follow)

    def clear_activity_status(self) -> None:
        if self._stream_item is None:
            return
        widget = self._stream_widget or self.messages.itemWidget(self._stream_item)
        if isinstance(widget, MessageWidget):
            should_follow = self._should_follow_output()
            widget.set_activity("")
            self._stream_widget = widget
            self._stream_item.setSizeHint(self._message_item_size(widget))
            self._follow_output_if_needed(should_follow)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self._resize_message_widgets)

    def _resize_message_widgets(self) -> None:
        should_follow = self._should_follow_output()
        width = max(160, self.messages.viewport().width() - 4)
        for index in range(self.messages.count()):
            item = self.messages.item(index)
            widget = self.messages.itemWidget(item)
            if isinstance(widget, MessageWidget):
                widget.setFixedWidth(width)
                widget.updateGeometry()
                item.setSizeHint(self._message_item_size(widget))
        self._follow_output_if_needed(should_follow)

    @staticmethod
    def _message_item_size(widget: MessageWidget) -> QSize:
        hint = widget.sizeHint()
        return QSize(hint.width(), hint.height() + 36)

    def _resize_input(self) -> None:
        document_height = self.input.document().size().height()
        target_height = max(52, min(220, int(document_height + 22)))
        self.input.setFixedHeight(target_height)

    def reset_stream(self) -> None:
        if self._stream_item is not None and self._stream_final_text:
            self.clear_activity_status()
            self._stream_text = self._stream_final_text
            self._update_stream_item()
        self._stream_item = None
        self._stream_widget = None
        self._stream_role = "roman"
        self._stream_text = ""
        self._stream_final_text = ""
        self._completed_stream_item = None
        self._completed_stream_widget = None
        self._completed_stream_role = ""
        self._completed_stream_text = ""
        self._typewriter_queue.clear()
        self.typewriter_timer.stop()

    def discard_stream(self) -> None:
        self.stop_typing_indicator()
        self.typewriter_timer.stop()
        self._typewriter_queue.clear()
        if self._stream_item is not None:
            row = self.messages.row(self._stream_item)
            if row >= 0:
                self.messages.takeItem(row)
        self._stream_item = None
        self._stream_widget = None
        self._stream_role = "roman"
        self._stream_text = ""
        self._stream_final_text = ""
        self._completed_stream_item = None
        self._completed_stream_widget = None
        self._completed_stream_role = ""
        self._completed_stream_text = ""

    def set_stream_message_id(self, message_id: int, content: str) -> None:
        if self._stream_item is not None:
            self._stream_item.setData(Qt.UserRole, {"id": message_id, "role": self._stream_role, "content": content})
        elif self._completed_stream_item is not None:
            self._completed_stream_item.setData(Qt.UserRole, {"id": message_id, "role": self._completed_stream_role, "content": content})

    def _replace_completed_stream(self, final_text: str) -> bool:
        if self._completed_stream_item is None:
            return False
        if self._completed_stream_role != self._stream_role or (
            self._completed_stream_text.strip()
            and not ResponseCleaner._same(self._completed_stream_text, final_text)
            and not self._looks_like_structured_payload(self._completed_stream_text)
        ):
            return False
        widget = self._completed_stream_widget or self.messages.itemWidget(self._completed_stream_item)
        if not isinstance(widget, MessageWidget):
            return False
        should_follow = self._should_follow_output()
        widget.set_content(final_text)
        widget.set_activity("")
        self._completed_stream_widget = widget
        self._completed_stream_item.setSizeHint(self._message_item_size(widget))
        self._completed_stream_item.setData(Qt.UserRole, {"id": None, "role": self._completed_stream_role or self._stream_role, "content": final_text})
        self._completed_stream_text = final_text
        self._follow_output_if_needed(should_follow)
        return True

    def _replace_recent_stream_duplicate(self, final_text: str) -> bool:
        if not final_text:
            return False
        for index in range(self.messages.count() - 1, max(-1, self.messages.count() - 6), -1):
            item = self.messages.item(index)
            data = item.data(Qt.UserRole) or {}
            if not isinstance(data, dict):
                continue
            role = str(data.get("role") or "")
            content = str(data.get("content") or "")
            if role != self._stream_role or not ResponseCleaner._same(content, final_text):
                continue
            widget = self.messages.itemWidget(item)
            if not isinstance(widget, MessageWidget):
                return False
            should_follow = self._should_follow_output()
            widget.set_content(final_text)
            widget.set_activity("")
            item.setData(Qt.UserRole, {"id": data.get("id"), "role": role, "content": final_text})
            item.setSizeHint(self._message_item_size(widget))
            self._completed_stream_item = item
            self._completed_stream_widget = widget
            self._completed_stream_role = role
            self._completed_stream_text = final_text
            self._follow_output_if_needed(should_follow)
            return True
        return False

    def _replace_recent_stream_placeholder(self, final_text: str) -> bool:
        if not final_text:
            return False
        for index in range(self.messages.count() - 1, max(-1, self.messages.count() - 6), -1):
            item = self.messages.item(index)
            data = item.data(Qt.UserRole) or {}
            if not isinstance(data, dict):
                continue
            role = str(data.get("role") or "")
            content = str(data.get("content") or "")
            if role != self._stream_role:
                continue
            if content.strip() and not self._looks_like_structured_payload(content):
                continue
            widget = self.messages.itemWidget(item)
            if not isinstance(widget, MessageWidget):
                return False
            should_follow = self._should_follow_output()
            widget.set_content(final_text)
            widget.set_activity("")
            item.setData(Qt.UserRole, {"id": data.get("id"), "role": role, "content": final_text})
            item.setSizeHint(self._message_item_size(widget))
            self._completed_stream_item = item
            self._completed_stream_widget = widget
            self._completed_stream_role = role
            self._completed_stream_text = final_text
            self._follow_output_if_needed(should_follow)
            return True
        return False

    @staticmethod
    def _visible_stream_text(text: str) -> str:
        match = re.search(r"```(?:json)?\s*\{|\A\s*json\s*\n\s*\{\s*\"schema_version\"\s*:|(?:^|\n)\s*\{\s*\"schema_version\"\s*:|<structured_response>", text, re.IGNORECASE | re.DOTALL)
        if match is None:
            return text
        return text[: match.start()].rstrip()

    @staticmethod
    def _looks_like_structured_payload(text: str) -> bool:
        return bool(
            re.search(
                r"```(?:json)?\s*\{|\A\s*json\s*\n\s*\{\s*\"schema_version\"\s*:|(?:^|\n)\s*\{\s*\"schema_version\"\s*:|<structured_response>",
                text,
                re.IGNORECASE | re.DOTALL,
            )
        )

    def _should_follow_output(self) -> bool:
        bar = self.messages.verticalScrollBar()
        return bar.maximum() - bar.value() <= 140

    def _follow_output_if_needed(self, should_follow: bool) -> None:
        if should_follow:
            QTimer.singleShot(0, self._animate_scroll_to_bottom)

    def _animate_scroll_to_bottom(self) -> None:
        bar = self.messages.verticalScrollBar()
        target = bar.maximum()
        if target <= bar.value():
            return
        if self._scroll_animation is not None:
            self._scroll_animation.stop()
            self._scroll_animation.deleteLater()
            self._scroll_animation = None
        animation = QPropertyAnimation(bar, b"value", self)
        animation.setStartValue(bar.value())
        animation.setEndValue(target)
        distance = target - bar.value()
        # Keep the movement readable even for a long streamed response.
        animation.setDuration(max(420, min(1400, 320 + distance * 2)))
        animation.setEasingCurve(QEasingCurve.InOutCubic)
        animation.finished.connect(lambda: self._finish_scroll_animation(animation))
        self._scroll_animation = animation
        animation.start()

    def _cancel_output_scroll(self) -> None:
        if self._scroll_animation is None:
            return
        self._scroll_animation.stop()
        self._scroll_animation.deleteLater()
        self._scroll_animation = None

    def _finish_scroll_animation(self, animation: QPropertyAnimation) -> None:
        if self._scroll_animation is animation:
            self._scroll_animation = None
        animation.deleteLater()

    def _on_scroll_range_changed(self, _minimum: int, _maximum: int) -> None:
        self._follow_output_if_needed(self._should_follow_output())

    def _emit_send(self) -> None:
        text = self.input.toPlainText().strip()
        if not text:
            return
        self.send_requested.emit(text)
        self.focus_input_later()

    def clear_input(self) -> None:
        """Clear the composer only after MainWindow accepted the message."""
        self.input.clear()

    def _agent_short_name(self) -> str:
        return self._agent_labels.get(self._stream_role, "Сотрудник")
