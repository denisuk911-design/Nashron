from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QTextEdit, QVBoxLayout

from core.supervisor_chat_service import SupervisorChatApplicationService, SupervisorChatResult
from gui.dialog_chrome import apply_team_dialog_chrome


class SupervisorChatDialog(QDialog):
    """Dedicated owner surface for Iris, backed by application services."""

    def __init__(self, service: SupervisorChatApplicationService, organization_id: str | None, parent=None, team_builder_handler=None) -> None:
        super().__init__(parent)
        self.service = service
        self.organization_id = organization_id
        self.team_builder_handler = team_builder_handler
        self._pending_token = ""
        apply_team_dialog_chrome(self, minimum_width=720)
        self.setWindowTitle("Iris - Luminifera")
        self.resize(820, 620)
        self.setObjectName("irisChatDialog")

        self.messages = QListWidget()
        self.messages.setSelectionMode(QListWidget.NoSelection)
        self.messages.setWordWrap(True)
        self.messages.setSpacing(6)
        self.messages.setStyleSheet("QListWidget::item { padding: 8px; }")
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Опишите Iris, какой результат нужно получить...")
        self.editor.setMinimumHeight(80)
        self.send = QPushButton("Отправить")
        self.send.clicked.connect(self._send)
        self.confirm = QPushButton("Подтвердить действие")
        self.confirm.setVisible(False)
        self.confirm.clicked.connect(self._confirm)
        self.build_team = QPushButton("Собрать команду")
        self.build_team.setVisible(False)
        self.build_team.clicked.connect(self._build_team)
        close = QPushButton("Закрыть")
        close.clicked.connect(self.close)
        buttons = QHBoxLayout()
        buttons.addWidget(self.confirm)
        buttons.addWidget(self.build_team)
        buttons.addStretch(1)
        buttons.addWidget(close)
        buttons.addWidget(self.send)
        layout = QVBoxLayout(self)
        intro = QLabel("Iris помогает управлять командой, целями и настройками Luminifera.")
        intro.setObjectName("irisChatIntro")
        layout.addWidget(intro)
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

    def _build_team(self) -> None:
        brief = getattr(self, "_team_brief", "")
        self.build_team.setVisible(False)
        if self.team_builder_handler is not None:
            self.team_builder_handler(brief)

    def _show_result(self, result: SupervisorChatResult) -> None:
        self._append("Iris", result.message)
        if result.action == "team_proposal":
            self._team_brief = str(result.data.get("brief") or "")
            self.build_team.setVisible(self.team_builder_handler is not None)
        if result.confirmation_required:
            self._pending_token = result.confirmation_token
            self.confirm.setVisible(True)

    def _append(self, author: str, text: str) -> None:
        item = QListWidgetItem(f"{author}\n{text}")
        item.setTextAlignment(Qt.AlignLeft)
        self.messages.addItem(item)
        self.messages.scrollToBottom()
