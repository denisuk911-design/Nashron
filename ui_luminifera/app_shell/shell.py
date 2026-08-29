from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QToolButton, QVBoxLayout, QWidget


class LuminiferaShell(QWidget):
    """Product shell around the existing application content and services."""

    def __init__(self, content: QWidget, organization_selector: QComboBox, callbacks: dict[str, Callable[[], None]], *, owner_avatar_path: str = "", onboarding_language_selector: QComboBox | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("luminiferaShell")
        self._callbacks = callbacks
        self._navigation_buttons: dict[str, QPushButton] = {}
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.sidebar = self._build_sidebar()
        root.addWidget(self.sidebar, 0)
        workspace = QWidget()
        workspace.setObjectName("luminiferaWorkspace")
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)
        workspace_layout.addWidget(self._build_topbar(organization_selector, owner_avatar_path, onboarding_language_selector))
        workspace_layout.addWidget(content, 1)
        root.addWidget(workspace, 1)
        self.set_active_navigation("home")

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("luminiferaSidebar")
        sidebar.setFixedWidth(248)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 22, 18, 18)
        layout.setSpacing(8)
        brand_row = QHBoxLayout()
        brand_row.setSpacing(12)
        mark = QLabel("✦")
        mark.setObjectName("luminiferaBrandMark")
        mark.setAlignment(Qt.AlignCenter)
        mark.setFixedSize(44, 44)
        name = QLabel("LUMINIFERA")
        name.setObjectName("luminiferaBrandName")
        brand_row.addWidget(mark)
        brand_row.addWidget(name, 1)
        layout.addLayout(brand_row)
        layout.addSpacing(24)
        for key, symbol, label in (("home", "⌂", "Главная"), ("chat", "◌", "Чат"), ("work", "□", "Работа"), ("team", "♙", "Команда"), ("files", "▱", "Файлы")):
            layout.addWidget(self._navigation_button(key, symbol, label))
        divider = QFrame()
        divider.setObjectName("luminiferaDivider")
        divider.setFrameShape(QFrame.HLine)
        layout.addSpacing(8)
        layout.addWidget(divider)
        layout.addSpacing(8)
        self.iris_button = self._navigation_button("iris", "✦", "Iris")
        self.iris_button.setProperty("distinct", True)
        self.iris_button.setToolTip("Поговорить с Iris")
        layout.addWidget(self.iris_button)
        iris_caption = QLabel("AI-супервизер")
        iris_caption.setObjectName("luminiferaIrisCaption")
        iris_caption.setContentsMargins(48, 0, 0, 0)
        layout.addWidget(iris_caption)
        layout.addStretch(1)
        self.help_button = self._utility_button("?", "Помощь", "help")
        self.settings_button = self._utility_button("⚙", "Настройки", "settings")
        layout.addWidget(self.help_button)
        layout.addWidget(self.settings_button)
        return sidebar

    def _build_topbar(self, organization_selector: QComboBox, owner_avatar_path: str, onboarding_language_selector: QComboBox | None) -> QWidget:
        self.organization_selector = organization_selector
        topbar = QWidget()
        topbar.setObjectName("luminiferaTopbar")
        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(28, 15, 24, 15)
        layout.setSpacing(12)
        self.onboarding_brand = QLabel("✦  Luminifera")
        self.onboarding_brand.setObjectName("luminiferaOnboardingBrand")
        self.onboarding_brand.setVisible(False)
        layout.addWidget(self.onboarding_brand)
        organization_selector.setObjectName("luminiferaOrganizationSelector")
        organization_selector.setMinimumWidth(220)
        organization_selector.setMaximumWidth(340)
        layout.addWidget(organization_selector)
        layout.addStretch(1)
        self.onboarding_language_selector = onboarding_language_selector
        if onboarding_language_selector is not None:
            onboarding_language_selector.setObjectName("luminiferaOnboardingLanguage")
            onboarding_language_selector.setMinimumWidth(148)
            onboarding_language_selector.setVisible(False)
            layout.addWidget(onboarding_language_selector)
        self.ai_state_label = QLabel("●  ИИ готов")
        self.ai_state_label.setObjectName("luminiferaAiState")
        layout.addWidget(self.ai_state_label)
        self.iris_state_label = QLabel("Iris на связи")
        self.iris_state_label.setObjectName("luminiferaIrisState")
        layout.addWidget(self.iris_state_label)
        self.profile_button = QToolButton()
        self.profile_button.setObjectName("luminiferaProfileButton")
        self.profile_button.setToolTip("Профиль")
        self.profile_button.setFixedSize(42, 42)
        avatar = QPixmap(owner_avatar_path) if owner_avatar_path and Path(owner_avatar_path).is_file() else QPixmap()
        if not avatar.isNull():
            icon = avatar.scaled(34, 34, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.profile_button.setIcon(QIcon(icon))
            self.profile_button.setIconSize(icon.size())
        else:
            self.profile_button.setText("ВЫ")
        self.profile_button.clicked.connect(self._callbacks["profile"])
        layout.addWidget(self.profile_button)
        return topbar

    def set_onboarding_mode(self, active: bool) -> None:
        self.sidebar.setVisible(not active)
        self.onboarding_brand.setVisible(active)
        self.organization_selector.setVisible(not active)
        self.ai_state_label.setVisible(not active)
        self.iris_state_label.setVisible(not active)
        self.profile_button.setVisible(not active)
        if self.onboarding_language_selector is not None:
            self.onboarding_language_selector.setVisible(active)

    def _navigation_button(self, key: str, symbol: str, label: str) -> QPushButton:
        button = QPushButton(f"{symbol}   {label}")
        button.setObjectName("luminiferaNavButton")
        button.setCheckable(True)
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(lambda _checked=False, item=key: self._activate(item))
        self._navigation_buttons[key] = button
        return button

    def _utility_button(self, symbol: str, label: str, callback: str) -> QPushButton:
        button = QPushButton(f"{symbol}   {label}")
        button.setObjectName("luminiferaUtilityButton")
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(self._callbacks[callback])
        return button

    def _activate(self, key: str) -> None:
        callback = self._callbacks.get(key)
        if callback is not None:
            callback()
        self.set_active_navigation(key)

    def set_active_navigation(self, key: str) -> None:
        for item, button in self._navigation_buttons.items():
            button.setChecked(item == key)

    def set_language(self, language: str) -> None:
        labels = {
            "ru": {"home": "Главная", "chat": "Чат", "work": "Работа", "team": "Команда", "files": "Файлы", "iris": "Iris", "iris_caption": "AI-супервизер", "help": "Помощь", "settings": "Настройки"},
            "uk": {"home": "Головна", "chat": "Чат", "work": "Робота", "team": "Команда", "files": "Файли", "iris": "Iris", "iris_caption": "AI-супервізор", "help": "Допомога", "settings": "Налаштування"},
            "en": {"home": "Home", "chat": "Chat", "work": "Work", "team": "Team", "files": "Files", "iris": "Iris", "iris_caption": "AI supervisor", "help": "Help", "settings": "Settings"},
        }.get(language, {})
        symbols = {"home": "⌂", "chat": "◌", "work": "□", "team": "♙", "files": "▱", "iris": "✦"}
        for key, label in labels.items():
            if key in self._navigation_buttons:
                self._navigation_buttons[key].setText(f"{symbols.get(key, '')}   {label}")
        if "iris_caption" in labels:
            self.iris_button.parentWidget().findChild(QLabel, "luminiferaIrisCaption").setText(labels["iris_caption"])
        self.help_button.setText(f"?   {labels.get('help', 'Help')}")
        self.settings_button.setText(f"⚙   {labels.get('settings', 'Settings')}")
        state_labels = {
            "ru": ("ИИ готов", "Iris на связи"),
            "uk": ("ШІ готовий", "Iris на зв'язку"),
            "en": ("AI ready", "Iris is available"),
        }.get(language, ("AI ready", "Iris is available"))
        self.ai_state_label.setText(f"●  {state_labels[0]}")
        self.iris_state_label.setText(state_labels[1])
        self.profile_button.setToolTip({"ru": "Профиль", "uk": "Профіль", "en": "Profile"}.get(language, "Profile"))

    def set_ai_ready(self, ready: bool) -> None:
        self.ai_state_label.setText("●  ИИ готов" if ready else "●  Нужен вход")
        self.ai_state_label.setProperty("ready", ready)
        self.ai_state_label.style().unpolish(self.ai_state_label)
        self.ai_state_label.style().polish(self.ai_state_label)

    def set_owner_avatar(self, path: str) -> None:
        pixmap = QPixmap(path) if path and Path(path).is_file() else QPixmap()
        if pixmap.isNull():
            self.profile_button.setIcon(QIcon())
            self.profile_button.setText("ВЫ")
            return
        icon = pixmap.scaled(34, 34, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self.profile_button.setText("")
        self.profile_button.setIcon(QIcon(icon))
        self.profile_button.setIconSize(icon.size())
