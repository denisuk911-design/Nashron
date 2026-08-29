from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class LuminiferaSettingsDialog(QDialog):
    def __init__(self, settings: dict[str, object], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.language_code = str(settings.get("interface_language", "ru"))
        self.setObjectName("luminiferaSettings")
        self.setWindowTitle({"ru": "Настройки Luminifera", "uk": "Налаштування Luminifera", "en": "Luminifera settings"}.get(self.language_code, "Luminifera settings"))
        self.setMinimumSize(620, 460)
        root = QVBoxLayout(self)
        tabs = QTabWidget()
        root.addWidget(tabs, 1)

        general = QWidget()
        general_form = QFormLayout(general)
        self.language = QComboBox()
        for code, label in (("ru", "Русский"), ("uk", "Українська"), ("en", "English")):
            self.language.addItem(label, code)
        self.language.setCurrentIndex(max(0, self.language.findData(self.language_code)))
        general_form.addRow("Язык интерфейса", self.language)
        self.response_mode = QComboBox()
        for label, value in (("Один подходящий сотрудник", "SINGLE"), ("Небольшая группа", "SMALL_GROUP"), ("Вся команда", "ALL")):
            self.response_mode.addItem(label, value)
        self.response_mode.setCurrentIndex(max(0, self.response_mode.findData(str(settings.get("general_chat_response", "SINGLE")))))
        general_form.addRow("Ответы команды", self.response_mode)
        tabs.addTab(general, "Основные")

        appearance = QWidget()
        appearance_form = QFormLayout(appearance)
        self.theme = QComboBox()
        for label, value in (("Ночной космос", "dark"), ("Графит", "dark_graphite"), ("Ночной город", "night_city"), ("Минимализм", "minimal"), ("Светлая", "light")):
            self.theme.addItem(label, value)
        self.theme.setCurrentIndex(max(0, self.theme.findData(str(settings.get("theme", "dark")))))
        appearance_form.addRow("Тема", self.theme)
        self.reduce_motion = QCheckBox("Уменьшить декоративные анимации")
        self.reduce_motion.setChecked(bool(settings.get("reduce_motion", False)))
        appearance_form.addRow("", self.reduce_motion)
        tabs.addTab(appearance, "Внешний вид")

        sound = QWidget()
        sound_form = QFormLayout(sound)
        self.message_sounds = QCheckBox("Звуки сообщений")
        self.message_sounds.setChecked(bool(settings.get("message_sounds_enabled", True)))
        sound_form.addRow("", self.message_sounds)
        self.send_sound = QCheckBox("Звук отправки")
        self.send_sound.setChecked(bool(settings.get("send_sound_enabled", True)))
        sound_form.addRow("", self.send_sound)
        self.receive_sound = QCheckBox("Звук получения")
        self.receive_sound.setChecked(bool(settings.get("receive_sound_enabled", True)))
        sound_form.addRow("", self.receive_sound)
        tabs.addTab(sound, "Звук")

        providers = QWidget()
        provider_form = QFormLayout(providers)
        provider_form.addRow("Codex", QLabel("Проверяется при запуске чата"))
        provider_form.addRow("Gemini", QLabel("Проверяется при запуске чата"))
        provider_form.addRow("Iris", QLabel("Доступен в рабочем чате"))
        tabs.addTab(providers, "Подключения")

        data = QWidget()
        data_form = QFormLayout(data)
        workspace_row = QWidget()
        workspace_layout = QHBoxLayout(workspace_row)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        self.workspace = QLineEdit(str(settings.get("workspace_root", "")))
        browse = QLineEdit()
        browse.setReadOnly(True)
        browse.setPlaceholderText("Выберите рабочую папку кнопкой справа")
        self.workspace_browse = browse
        workspace_layout.addWidget(self.workspace, 1)
        from PySide6.QtWidgets import QPushButton
        button = QPushButton("Обзор")
        button.clicked.connect(self._browse_workspace)
        workspace_layout.addWidget(button)
        data_form.addRow("Рабочая папка", workspace_row)
        tabs.addTab(data, "Данные")

        advanced = QWidget()
        advanced_form = QFormLayout(advanced)
        self.allow_local_tools = QCheckBox("Разрешить локальные инструменты сотрудникам")
        self.allow_local_tools.setChecked(bool(settings.get("allow_local_tools", False)))
        advanced_form.addRow("", self.allow_local_tools)
        tabs.addTab(advanced, "Дополнительно")

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _browse_workspace(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Выберите рабочую папку", self.workspace.text() or str(Path.home()))
        if selected:
            self.workspace.setText(selected)

    def values(self) -> dict[str, object]:
        return {
            "interface_language": str(self.language.currentData()),
            "general_chat_response": str(self.response_mode.currentData()),
            "theme": str(self.theme.currentData()),
            "reduce_motion": self.reduce_motion.isChecked(),
            "message_sounds_enabled": self.message_sounds.isChecked(),
            "send_sound_enabled": self.send_sound.isChecked(),
            "receive_sound_enabled": self.receive_sound.isChecked(),
            "workspace_root": self.workspace.text().strip(),
            "allow_local_tools": self.allow_local_tools.isChecked(),
        }
