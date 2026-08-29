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
        self.developer_mode = QCheckBox("Режим разработчика (диагностика и технические детали)")
        self.developer_mode.setChecked(bool(settings.get("developer_mode", False)))
        advanced_form.addRow("", self.developer_mode)
        tabs.addTab(advanced, "Дополнительно")

        # The settings dialog is also used as the language picker, so refresh every
        # visible label from the selected language before the dialog is shown.
        labels = {
            "ru": {
                "tabs": ["Основные", "Внешний вид", "Звук", "Подключения", "Данные", "Дополнительно"],
                "language": "Язык интерфейса", "responses": "Ответы команды", "theme": "Тема",
                "motion": "Уменьшить декоративные анимации", "sounds": "Звуки сообщений",
                "send": "Звук отправки", "receive": "Звук получения", "workspace": "Рабочая папка",
                "browse_hint": "Выберите рабочую папку кнопкой справа", "browse": "Обзор",
                "tools": "Разрешить локальные инструменты сотрудникам",
                "developer": "Режим разработчика (диагностика и технические детали)",
            },
            "uk": {
                "tabs": ["Основні", "Вигляд", "Звук", "Підключення", "Дані", "Додатково"],
                "language": "Мова інтерфейсу", "responses": "Відповіді команди", "theme": "Тема",
                "motion": "Зменшити декоративні анімації", "sounds": "Звуки повідомлень",
                "send": "Звук надсилання", "receive": "Звук отримання", "workspace": "Робоча папка",
                "browse_hint": "Виберіть робочу папку кнопкою праворуч", "browse": "Огляд",
                "tools": "Дозволити локальні інструменти співробітникам",
                "developer": "Режим розробника (діагностика й технічні деталі)",
            },
            "en": {
                "tabs": ["General", "Appearance", "Sound", "Connections", "Data", "Advanced"],
                "language": "Interface language", "responses": "Team responses", "theme": "Theme",
                "motion": "Reduce decorative animation", "sounds": "Message sounds",
                "send": "Send sound", "receive": "Receive sound", "workspace": "Workspace folder",
                "browse_hint": "Choose a workspace folder with the button on the right", "browse": "Browse",
                "tools": "Allow local tools for employees",
                "developer": "Developer mode (diagnostics and technical details)",
            },
        }.get(self.language_code, {})
        for index, title in enumerate(labels.get("tabs", [])):
            tabs.setTabText(index, title)
        combo_labels = {
            "ru": (["Русский", "Украинский", "Английский"], ["Один подходящий сотрудник", "Небольшая группа", "Вся команда"], ["Ночной космос", "Графит", "Ночной город", "Минимализм", "Светлая"]),
            "uk": (["Українська", "Російська", "Англійська"], ["Один відповідний співробітник", "Невелика група", "Уся команда"], ["Нічний космос", "Графіт", "Нічне місто", "Мінімалізм", "Світла"]),
            "en": (["Russian", "Ukrainian", "English"], ["One suitable employee", "Small group", "Whole team"], ["Night space", "Graphite", "Night city", "Minimal", "Light"]),
        }.get(self.language_code, ([], [], []))
        for index, text in enumerate(combo_labels[0]):
            self.language.setItemText(index, text)
        for index, text in enumerate(combo_labels[1]):
            self.response_mode.setItemText(index, text)
        for index, text in enumerate(combo_labels[2]):
            self.theme.setItemText(index, text)
        self.language_label = general_form.labelForField(self.language)
        self.response_label = general_form.labelForField(self.response_mode)
        self.theme_label = appearance_form.labelForField(self.theme)
        self.workspace_label = data_form.labelForField(workspace_row)
        if self.language_label:
            self.language_label.setText(labels["language"])
        if self.response_label:
            self.response_label.setText(labels["responses"])
        if self.theme_label:
            self.theme_label.setText(labels["theme"])
        if self.workspace_label:
            self.workspace_label.setText(labels["workspace"])
        self.reduce_motion.setText(labels["motion"])
        self.message_sounds.setText(labels["sounds"])
        self.send_sound.setText(labels["send"])
        self.receive_sound.setText(labels["receive"])
        self.workspace_browse.setPlaceholderText(labels["browse_hint"])
        button.setText(labels["browse"])
        self.allow_local_tools.setText(labels["tools"])
        self.developer_mode.setText(labels["developer"])

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_labels = {"ru": ("Сохранить", "Отмена"), "uk": ("Зберегти", "Скасувати"), "en": ("Save", "Cancel")}
        ok_text, cancel_text = button_labels.get(self.language_code, button_labels["en"])
        buttons.button(QDialogButtonBox.Ok).setText(ok_text)
        buttons.button(QDialogButtonBox.Cancel).setText(cancel_text)
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
            "developer_mode": self.developer_mode.isChecked(),
        }
