from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget


def show_install_instructions(parent: QWidget | None = None) -> None:
    QMessageBox.information(
        parent,
        "Установка Codex CLI",
        "Установите Codex CLI официальным способом, затем выполните вход через кнопку "
        "\"Войти через ChatGPT\" в приложении. Приложение не запрашивает и не хранит пароль.",
    )
