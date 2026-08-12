from __future__ import annotations

from PySide6.QtWidgets import (
    QFileDialog,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

from gui.localization import SUPPORTED_LANGUAGES, tr


class SettingsDialog(QDialog):
    def __init__(self, settings: dict[str, object], parent=None) -> None:
        super().__init__(parent)
        language = str(settings.get("interface_language", "ru"))
        self.setWindowTitle(
            {
                "ru": "Настройки",
                "uk": "Налаштування",
                "en": "Settings",
            }.get(language, "Настройки")
        )
        self.history_limit = QSpinBox()
        self.history_limit.setRange(4, 1000)
        self.history_limit.setValue(int(settings.get("history_message_limit", 20)))

        self.timeout = QSpinBox()
        self.timeout.setRange(30, 3600)
        self.timeout.setValue(int(settings.get("codex_timeout_seconds", 180)))

        self.response_soft_warning = QSpinBox()
        self.response_soft_warning.setRange(5, 3600)
        self.response_soft_warning.setSuffix(" сек.")
        self.response_soft_warning.setValue(int(settings.get("response_soft_warning_seconds", 20)))

        self.response_extended_warning = QSpinBox()
        self.response_extended_warning.setRange(6, 7200)
        self.response_extended_warning.setSuffix(" сек.")
        self.response_extended_warning.setValue(int(settings.get("response_extended_warning_seconds", 90)))

        self.response_timeout = QSpinBox()
        self.response_timeout.setRange(0, 10800)
        self.response_timeout.setSuffix(" сек.")
        self.response_timeout.setSpecialValueText(
            {
                "ru": "Не останавливать",
                "uk": "Не зупиняти",
                "en": "Do not stop",
            }.get(language, "Не останавливать")
        )
        self.response_timeout.setValue(int(settings.get("response_timeout_seconds", 0)))

        self.theme = QComboBox()
        theme_labels = {
            "ru": [
                ("Тёмная · космос", "dark"),
                ("Графит", "dark_graphite"),
                ("Ночной океан", "dark_ocean"),
                ("Тихий лес", "dark_forest"),
                ("Инженерная мастерская", "dark_amber"),
                ("Ночной город", "night_city"),
                ("Тёплая бумага", "warm_paper"),
                ("Минимализм", "minimal"),
                ("Светлая", "light"),
            ],
            "uk": [
                ("Темна · космос", "dark"),
                ("Графіт", "dark_graphite"),
                ("Нічний океан", "dark_ocean"),
                ("Тихий ліс", "dark_forest"),
                ("Інженерна майстерня", "dark_amber"),
                ("Нічне місто", "night_city"),
                ("Теплий папір", "warm_paper"),
                ("Мінімалізм", "minimal"),
                ("Світла", "light"),
            ],
            "en": [
                ("Dark · space", "dark"),
                ("Graphite", "dark_graphite"),
                ("Night ocean", "dark_ocean"),
                ("Quiet forest", "dark_forest"),
                ("Engineering workshop", "dark_amber"),
                ("Night city", "night_city"),
                ("Warm paper", "warm_paper"),
                ("Minimal", "minimal"),
                ("Light", "light"),
            ],
        }.get(language, [("Тёмная", "dark"), ("Светлая", "light")])
        for label, value in theme_labels:
            self.theme.addItem(label, value)
        theme_index = self.theme.findData(str(settings.get("theme", "dark")))
        self.theme.setCurrentIndex(theme_index if theme_index >= 0 else 0)
        self.theme_preview = QLabel()
        self.theme_preview.setObjectName("themePreview")
        self.theme_preview.setMinimumHeight(44)
        self.theme_preview.setWordWrap(True)
        self.theme.currentIndexChanged.connect(self._update_theme_preview)

        self.language = QComboBox()
        for code, label in SUPPORTED_LANGUAGES.items():
            self.language.addItem(label, code)
        selected_language = str(settings.get("interface_language", "ru"))
        language_index = self.language.findData(selected_language)
        self.language.setCurrentIndex(language_index if language_index >= 0 else 0)

        self.general_response = QComboBox()
        response_labels = {
            "ru": ("Один подходящий сотрудник", "Небольшая группа", "Все сотрудники"),
            "uk": ("Один відповідний співробітник", "Невелика група", "Усі співробітники"),
            "en": ("One suitable employee", "Small group", "All employees"),
        }.get(language, ("Один подходящий сотрудник", "Небольшая группа", "Все сотрудники"))
        self.general_response.addItem(response_labels[0], "SINGLE")
        self.general_response.addItem(response_labels[1], "SMALL_GROUP")
        self.general_response.addItem(response_labels[2], "ALL")
        response_index = self.general_response.findData(str(settings.get("general_chat_response", "SINGLE")))
        self.general_response.setCurrentIndex(response_index if response_index >= 0 else 0)

        self.allow_local_tools = QCheckBox(
            {
                "ru": "Разрешить Codex читать и создавать файлы, а также выполнять команды",
                "uk": "Дозволити Codex читати і створювати файли, а також виконувати команди",
                "en": "Allow Codex to read and create files and run commands",
            }.get(language, "Разрешить Codex читать и создавать файлы, а также выполнять команды")
        )
        self.allow_local_tools.setChecked(bool(settings.get("allow_local_tools", False)))

        self.workspace = QLineEdit(str(settings.get("workspace_root", "")))
        browse = QPushButton({"ru": "Выбрать", "uk": "Обрати", "en": "Browse"}.get(language, "Выбрать"))
        browse.clicked.connect(self._browse_workspace)
        workspace_row = QWidget()
        workspace_layout = QHBoxLayout(workspace_row)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.addWidget(self.workspace)
        workspace_layout.addWidget(browse)

        self.user_avatar = QLineEdit(str(settings.get("user_avatar_path", "")))
        browse_avatar = QPushButton({"ru": "Выбрать", "uk": "Обрати", "en": "Browse"}.get(language, "Выбрать"))
        browse_avatar.clicked.connect(self._browse_user_avatar)
        avatar_row = QWidget()
        avatar_layout = QHBoxLayout(avatar_row)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        avatar_layout.addWidget(self.user_avatar)
        avatar_layout.addWidget(browse_avatar)

        self.chat_background = QLineEdit(str(settings.get("chat_background_path", "")))
        browse_background = QPushButton({"ru": "Выбрать", "uk": "Обрати", "en": "Browse"}.get(language, "Выбрать"))
        browse_background.clicked.connect(self._browse_chat_background)
        background_row = QWidget()
        background_layout = QHBoxLayout(background_row)
        background_layout.setContentsMargins(0, 0, 0, 0)
        background_layout.addWidget(self.chat_background)
        background_layout.addWidget(browse_background)

        self.background_opacity = QSpinBox()
        self.background_opacity.setRange(0, 70)
        self.background_opacity.setSuffix(" %")
        self.background_opacity.setValue(int(settings.get("chat_background_opacity", 18)))
        self.background_mode = QComboBox()
        mode_labels = {
            "ru": [("Заполнить", "cover"), ("Замостить", "tile"), ("По центру", "center")],
            "uk": [("Заповнити", "cover"), ("Замостити", "tile"), ("По центру", "center")],
            "en": [("Cover", "cover"), ("Tile", "tile"), ("Center", "center")],
        }.get(language, [("Заполнить", "cover"), ("Замостить", "tile"), ("По центру", "center")])
        for label, value in mode_labels:
            self.background_mode.addItem(label, value)
        mode_index = self.background_mode.findData(str(settings.get("chat_background_mode", "cover")))
        self.background_mode.setCurrentIndex(mode_index if mode_index >= 0 else 0)

        self.reduce_motion = QCheckBox(
            {
                "ru": "Уменьшить декоративные анимации",
                "uk": "Зменшити декоративні анімації",
                "en": "Reduce decorative animations",
            }.get(language, "Уменьшить декоративные анимации")
        )
        self.reduce_motion.setChecked(bool(settings.get("reduce_motion", False)))

        self.message_sounds = QCheckBox(
            {"ru": "Звуки сообщений", "uk": "Звуки повідомлень", "en": "Message sounds"}.get(language, "Звуки сообщений")
        )
        self.message_sounds.setChecked(bool(settings.get("message_sounds_enabled", True)))
        self.send_sound = QCheckBox(
            {"ru": "Звук отправки", "uk": "Звук надсилання", "en": "Send sound"}.get(language, "Звук отправки")
        )
        self.send_sound.setChecked(bool(settings.get("send_sound_enabled", True)))
        self.receive_sound = QCheckBox(
            {"ru": "Звук получения", "uk": "Звук отримання", "en": "Receive sound"}.get(language, "Звук получения")
        )
        self.receive_sound.setChecked(bool(settings.get("receive_sound_enabled", True)))
        self.sound_volume = QSpinBox()
        self.sound_volume.setRange(0, 100)
        self.sound_volume.setSuffix(" %")
        self.sound_volume.setValue(int(settings.get("message_sound_volume", 35)))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QFormLayout(self)
        labels = {
            "ru": {
                "history": "Лимит краткой истории",
                "timeout": "Тайм-аут Codex, сек.",
                "soft_warning": "Показать предупреждение ожидания",
                "extended_warning": "Показать расширенное предупреждение",
                "response_timeout": "Остановить ответ автоматически",
                "theme": "Тема",
                "workspace": "Рабочая папка",
                "language": "Язык интерфейса",
            },
            "uk": {
                "history": "Ліміт короткої історії",
                "timeout": "Тайм-аут Codex, сек.",
                "soft_warning": "Показати попередження очікування",
                "extended_warning": "Показати розширене попередження",
                "response_timeout": "Зупинити відповідь автоматично",
                "theme": "Тема",
                "workspace": "Робоча папка",
                "language": "Мова інтерфейсу",
            },
            "en": {
                "history": "Short history limit",
                "timeout": "Codex timeout, sec.",
                "soft_warning": "Show waiting warning",
                "extended_warning": "Show extended waiting warning",
                "response_timeout": "Stop response automatically",
                "theme": "Theme",
                "workspace": "Workspace folder",
                "language": "Interface language",
            },
        }.get(language)
        if labels is None:
            labels = {
                "history": "Лимит краткой истории",
                "timeout": "Тайм-аут Codex, сек.",
                "soft_warning": "Показать предупреждение ожидания",
                "extended_warning": "Показать расширенное предупреждение",
                "response_timeout": "Остановить ответ автоматически",
                "theme": "Тема",
                "workspace": "Рабочая папка",
                "language": "Язык интерфейса",
            }
        layout.addRow(labels["history"], self.history_limit)
        layout.addRow(labels["timeout"], self.timeout)
        layout.addRow(labels["soft_warning"], self.response_soft_warning)
        layout.addRow(labels["extended_warning"], self.response_extended_warning)
        layout.addRow(labels["response_timeout"], self.response_timeout)
        layout.addRow(labels["theme"], self.theme)
        layout.addRow({"ru": "Предпросмотр", "uk": "Попередній перегляд", "en": "Preview"}.get(language, "Предпросмотр"), self.theme_preview)
        layout.addRow({"ru": "Фон чата", "uk": "Фон чату", "en": "Chat background"}.get(language, "Фон чата"), background_row)
        layout.addRow({"ru": "Прозрачность фона", "uk": "Прозорість фону", "en": "Background opacity"}.get(language, "Прозрачность фона"), self.background_opacity)
        layout.addRow({"ru": "Размещение фона", "uk": "Розміщення фону", "en": "Background placement"}.get(language, "Размещение фона"), self.background_mode)
        layout.addRow(labels["workspace"], workspace_row)
        layout.addRow({"ru": "Мой аватар", "uk": "Мій аватар", "en": "My avatar"}.get(language, "Мой аватар"), avatar_row)
        layout.addRow(labels["language"], self.language)
        layout.addRow(
            {"ru": "Ответ на общие сообщения", "uk": "Відповідь на загальні повідомлення", "en": "Response to general messages"}.get(language, "Ответ на общие сообщения"),
            self.general_response,
        )
        layout.addRow(self.allow_local_tools)
        layout.addRow(self.reduce_motion)
        layout.addRow(self.message_sounds)
        layout.addRow(self.send_sound)
        layout.addRow(self.receive_sound)
        layout.addRow(
            {"ru": "Громкость сообщений", "uk": "Гучність повідомлень", "en": "Message volume"}.get(language, "Громкость сообщений"),
            self.sound_volume,
        )
        layout.addRow(buttons)
        self._update_theme_preview()

    def _browse_workspace(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, tr(str(self.language.currentData()), "workspace"), self.workspace.text())
        if selected:
            self.workspace.setText(selected)

    def _browse_user_avatar(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            {"ru": "Выбрать аватар", "uk": "Обрати аватар", "en": "Choose avatar"}.get(str(self.language.currentData()), "Выбрать аватар"),
            self.user_avatar.text(),
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)",
        )
        if selected:
            self.user_avatar.setText(selected)

    def _browse_chat_background(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            {"ru": "Выбрать фон чата", "uk": "Обрати фон чату", "en": "Choose chat background"}.get(str(self.language.currentData()), "Выбрать фон чата"),
            self.chat_background.text(),
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if selected:
            self.chat_background.setText(selected)

    def _update_theme_preview(self) -> None:
        previews = {
            "dark": ("#081421", "#f3f6fb", "#7357ff"),
            "dark_graphite": ("#171a20", "#f3f6fb", "#737bff"),
            "dark_ocean": ("#082238", "#f3f6fb", "#5f73ff"),
            "dark_forest": ("#0c211c", "#f3f6fb", "#7968e8"),
            "dark_amber": ("#211a10", "#f3f6fb", "#806be3"),
            "night_city": ("#0b1324", "#f3f6fb", "#6c63ff"),
            "warm_paper": ("#f4eee3", "#292622", "#7561c9"),
            "minimal": ("#101216", "#f3f6fb", "#667085"),
            "light": ("#f7faff", "#162033", "#6757d8"),
        }
        background, foreground, accent = previews.get(str(self.theme.currentData()), previews["dark"])
        preview_text = {
            "ru": "  Team2050    Сообщение по делу    12:44",
            "uk": "  Team2050    Повідомлення по суті    12:44",
            "en": "  Team2050    Focused message    12:44",
        }.get(str(self.language.currentData()), "  Team2050    Focused message    12:44")
        self.theme_preview.setText(preview_text)
        self.theme_preview.setStyleSheet(
            f"background: {background}; color: {foreground}; border: 2px solid {accent}; border-radius: 8px; padding: 8px;"
        )

    def values(self) -> dict[str, object]:
        return {
            "history_message_limit": self.history_limit.value(),
            "codex_timeout_seconds": self.timeout.value(),
            "response_soft_warning_seconds": self.response_soft_warning.value(),
            "response_extended_warning_seconds": self.response_extended_warning.value(),
            "response_timeout_seconds": self.response_timeout.value(),
            "theme": self.theme.currentData(),
            "chat_background_path": self.chat_background.text().strip(),
            "chat_background_opacity": self.background_opacity.value(),
            "chat_background_mode": self.background_mode.currentData(),
            "interface_language": self.language.currentData(),
            "allow_local_tools": self.allow_local_tools.isChecked(),
            "workspace_root": self.workspace.text().strip(),
            "reduce_motion": self.reduce_motion.isChecked(),
            "user_avatar_path": self.user_avatar.text().strip(),
            "general_chat_response": self.general_response.currentData(),
            "message_sounds_enabled": self.message_sounds.isChecked(),
            "send_sound_enabled": self.send_sound.isChecked(),
            "receive_sound_enabled": self.receive_sound.isChecked(),
            "message_sound_volume": self.sound_volume.value(),
        }
