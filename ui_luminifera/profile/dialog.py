from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget


class LuminiferaProfileDialog(QDialog):
    def __init__(self, settings: dict[str, object], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setObjectName("luminiferaProfile")
        self.setWindowTitle("Профиль владельца")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        self.avatar = QLabel()
        self.avatar.setFixedSize(88, 88)
        self.avatar.setObjectName("luminiferaProfileAvatar")
        layout.addWidget(self.avatar)
        form = QFormLayout()
        self.name = QLineEdit(str(settings.get("owner_display_name", "Владелец")))
        form.addRow("Имя", self.name)
        self.avatar_path = QLineEdit(str(settings.get("user_avatar_path", "")))
        browse = QPushButton("Выбрать аватар")
        browse.clicked.connect(self._browse_avatar)
        form.addRow("Аватар", self.avatar_path)
        form.addRow("", browse)
        layout.addLayout(form)
        self._render_avatar()
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_avatar(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "Выберите аватар", str(Path.home()), "Images (*.png *.jpg *.jpeg *.webp)")
        if selected:
            self.avatar_path.setText(selected)
            self._render_avatar()

    def _render_avatar(self) -> None:
        pixmap = QPixmap(self.avatar_path.text())
        self.avatar.setPixmap(pixmap.scaled(self.avatar.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation) if not pixmap.isNull() else QPixmap())

    def values(self) -> dict[str, object]:
        return {"owner_display_name": self.name.text().strip() or "Владелец", "user_avatar_path": self.avatar_path.text().strip()}
