from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QTextEdit, QVBoxLayout

from core.supervisor_chat_service import SupervisorChatApplicationService, SupervisorChatResult
from gui.dialog_chrome import apply_team_dialog_chrome


class SupervisorChatDialog(QDialog):
    """Persistent owner chat for the Team2050 Supervisor."""

    def __init__(self, service: SupervisorChatApplicationService, organization_id: str | None, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.organization_id = organization_id
        self._pending_token = ""
        apply_team_dialog_chrome(self, minimum_width=720)
        self.setWindowTitle("Supervisor Team2050")
        self.resize(820, 620)

        self.messages = QListWidget()
        self.messages.setSelectionMode(QListWidget.NoSelection)
        self.messages.setWordWrap(True)
        self.messages.setSpacing(6)
        self.messages.setStyleSheet("QListWidget::item { padding: 8px; }")
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Напишите Supervisor, что нужно сделать...")
        self.editor.setMinimumHeight(80)
        self.send = QPushButton("Отправить")
        self.send.clicked.connect(self._send)
        self.confirm = QPushButton("Подтвердить")
        self.confirm.setVisible(False)
        self.confirm.clicked.connect(self._confirm)
        close = QPushButton("Закрыть")
        close.clicked.connect(self.close)
        buttons = QHBoxLayout()
        buttons.addWidget(self.confirm)
        buttons.addStretch(1)
        buttons.addWidget(close)
        buttons.addWidget(self.send)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Supervisor-хозяин управляет Team2050 через сервисы приложения"))
        layout.addWidget(self.messages, 1)
        layout.addWidget(self.editor)
        layout.addLayout(buttons)

    def _send(self) -> None:
        text = self.editor.toPlainText().strip()
        if not text:
            return
        self._append("Вы", text)
        self.editor.clear()
        result = self.service.handle(text, self.organization_id)
        self._show_result(result)

    def _confirm(self) -> None:
        if not self._pending_token:
            return
        result = self.service.confirm(self._pending_token)
        self._pending_token = ""
        self.confirm.setVisible(False)
        self._show_result(result)

    def _show_result(self, result: SupervisorChatResult) -> None:
        self._append("Supervisor", result.message)
        if result.confirmation_required:
            self._pending_token = result.confirmation_token
            self.confirm.setVisible(True)

    def _append(self, author: str, text: str) -> None:
        item = QListWidgetItem(f"{author}\n{text}")
        item.setTextAlignment(Qt.AlignLeft)
        self.messages.addItem(item)
        self.messages.scrollToBottom()
