from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QToolButton, QVBoxLayout, QWidget


COPY = {
    "ru": {"title": "Добро пожаловать\nв Luminifera", "value": "Ваша AI-команда, которая доводит работу до проверенного результата.", "question": "С чего начнём?", "avatar": "Добавьте свой аватар", "upload": "Загрузить", "setup": "Настроить вместе", "hint": "Iris поможет на каждом шаге", "team": "Создать команду", "team_hint": "Соберите команду и начните работу", "demo": "Запустить демо", "demo_hint": "Посмотрите, как работает Luminifera", "skip": "Осмотреться", "choose": "Выбрать изображение владельца"},
    "uk": {"title": "Ласкаво просимо\nдо Luminifera", "value": "Ваша AI-команда, яка доводить роботу до перевіреного результату.", "question": "З чого почнемо?", "avatar": "Додайте свій аватар", "upload": "Завантажити", "setup": "Налаштувати разом", "hint": "Iris допоможе на кожному кроці", "team": "Створити команду", "team_hint": "Зберіть команду та почніть роботу", "demo": "Запустити демо", "demo_hint": "Побачте, як працює Luminifera", "skip": "Ознайомитися", "choose": "Вибрати зображення власника"},
    "en": {"title": "Welcome to\nLuminifera", "value": "Your AI team that carries work through to a verified result.", "question": "Where should we begin?", "avatar": "Add your avatar", "upload": "Upload", "setup": "Set up together", "hint": "Iris will guide every step", "team": "Create a team", "team_hint": "Assemble a team and start working", "demo": "Run demo", "demo_hint": "See Luminifera at work", "skip": "Look around", "choose": "Choose owner image"},
}


class FirstRunOnboarding(QWidget):
    avatar_selected = Signal(str)
    upload_requested = Signal()
    setup_requested = Signal()
    create_team_requested = Signal()
    demo_requested = Signal()
    skip_requested = Signal()

    def __init__(self, language: str, avatars: list[Path], selected_avatar: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("luminiferaOnboarding")
        self._language = language if language in COPY else "ru"
        self._selected_avatar = selected_avatar
        self._avatar_buttons: list[QToolButton] = []
        self._build(avatars)
        self.set_language(self._language)
        if selected_avatar:
            self.select_avatar(selected_avatar, emit=False)

    def _build(self, avatars: list[Path]) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 32)
        outer.addStretch(1)
        card = QFrame(objectName="luminiferaOnboardingCard")
        card.setMaximumWidth(720)
        content = QVBoxLayout(card)
        content.setContentsMargins(48, 42, 48, 36)
        content.setSpacing(18)
        mark = QLabel("✦", objectName="luminiferaOnboardingMark")
        mark.setAlignment(Qt.AlignCenter)
        mark.setFixedSize(72, 72)
        content.addWidget(mark, 0, Qt.AlignHCenter)
        self.title = QLabel(objectName="luminiferaOnboardingTitle")
        self.title.setAlignment(Qt.AlignCenter)
        content.addWidget(self.title)
        self.value = QLabel(objectName="luminiferaOnboardingValue")
        self.value.setAlignment(Qt.AlignCenter)
        self.value.setWordWrap(True)
        content.addWidget(self.value)
        self.question = QLabel(objectName="luminiferaOnboardingQuestion")
        self.question.setAlignment(Qt.AlignCenter)
        content.addWidget(self.question)
        avatar_panel = QFrame(objectName="luminiferaAvatarPanel")
        avatar_layout = QVBoxLayout(avatar_panel)
        avatar_layout.setContentsMargins(18, 14, 18, 14)
        self.avatar_label = QLabel()
        self.avatar_label.setAlignment(Qt.AlignCenter)
        avatar_layout.addWidget(self.avatar_label)
        choices = QHBoxLayout()
        choices.addStretch(1)
        for avatar in avatars[:5]:
            button = QToolButton()
            button.setObjectName("luminiferaAvatarChoice")
            button.setCheckable(True)
            button.setFixedSize(58, 58)
            button.setToolTip("Выбрать изображение владельца")
            pixmap = QPixmap(str(avatar))
            if not pixmap.isNull():
                icon = pixmap.scaled(48, 48, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                button.setIcon(QIcon(icon))
                button.setIconSize(icon.size())
            button.clicked.connect(lambda _checked=False, path=str(avatar): self.select_avatar(path))
            button.setProperty("avatarPath", str(avatar))
            self._avatar_buttons.append(button)
            choices.addWidget(button)
        self.upload_button = QPushButton(objectName="luminiferaAvatarUpload")
        self.upload_button.clicked.connect(self.upload_requested)
        choices.addWidget(self.upload_button)
        choices.addStretch(1)
        avatar_layout.addLayout(choices)
        content.addWidget(avatar_panel)
        self.setup_button = QPushButton(objectName="luminiferaOnboardingPrimary")
        self.setup_button.clicked.connect(self.setup_requested)
        content.addWidget(self.setup_button)
        secondary = QHBoxLayout()
        self.team_button = QPushButton(objectName="luminiferaOnboardingSecondary")
        self.team_button.clicked.connect(self.create_team_requested)
        self.demo_button = QPushButton(objectName="luminiferaOnboardingSecondary")
        self.demo_button.clicked.connect(self.demo_requested)
        secondary.addWidget(self.team_button)
        secondary.addWidget(self.demo_button)
        content.addLayout(secondary)
        self.result = QLabel(objectName="luminiferaOnboardingResult")
        self.result.setAlignment(Qt.AlignCenter)
        self.result.setWordWrap(True)
        self.result.setVisible(False)
        content.addWidget(self.result)
        self.skip_button = QPushButton(objectName="luminiferaOnboardingSkip")
        self.skip_button.clicked.connect(self.skip_requested)
        content.addWidget(self.skip_button, 0, Qt.AlignHCenter)
        outer.addWidget(card, 0, Qt.AlignHCenter)
        outer.addStretch(1)

    def set_language(self, language: str) -> None:
        self._language = language if language in COPY else "ru"
        copy = COPY[self._language]
        self.title.setText(copy["title"])
        self.value.setText(copy["value"])
        self.question.setText(copy["question"])
        self.avatar_label.setText(copy["avatar"])
        self.upload_button.setText(copy["upload"])
        self.setup_button.setText(f"{copy['setup']}\n{copy['hint']}")
        self.team_button.setText(f"{copy['team']}\n{copy['team_hint']}")
        self.demo_button.setText(f"{copy['demo']}\n{copy['demo_hint']}")
        self.skip_button.setText(copy["skip"])

    def select_avatar(self, path: str, *, emit: bool = True) -> None:
        self._selected_avatar = path
        for button in self._avatar_buttons:
            button.setChecked(str(button.property("avatarPath")) == path)
        if emit:
            self.avatar_selected.emit(path)

    def set_result(self, text: str) -> None:
        self.result.setText(text)
        self.result.setVisible(bool(text))
