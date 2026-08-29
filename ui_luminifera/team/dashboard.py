from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from core.agent_directory import ChatAgent


class TeamDashboard(QWidget):
    """Human-facing roster view; agent data is supplied by the application layer."""

    def __init__(self, language: str = "ru", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.language = language if language in {"ru", "uk", "en"} else "ru"
        self.setObjectName("luminiferaTeam")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(42, 32, 42, 32)
        layout.setSpacing(16)
        self.heading = QLabel()
        self.heading.setObjectName("luminiferaWorkHeading")
        layout.addWidget(self.heading)
        self.subtitle = QLabel()
        self.subtitle.setObjectName("luminiferaWorkMuted")
        layout.addWidget(self.subtitle)
        self.create_button = QPushButton()
        self.create_button.setObjectName("luminiferaHomePrimary")
        self.create_button.clicked.connect(self.create_team_requested)
        layout.addWidget(self.create_button, 0, Qt.AlignLeft)
        self.list = QListWidget()
        self.list.setObjectName("luminiferaTeamList")
        self.list.setSpacing(8)
        layout.addWidget(self.list, 1)
        self.set_language(self.language)

    def set_language(self, language: str) -> None:
        self.language = language if language in {"ru", "uk", "en"} else "ru"
        copy = {
            "ru": ("Команда", "Люди и AI-специалисты, назначенные в это рабочее пространство", "В команде пока никого нет", "Собрать команду"),
            "uk": ("Команда", "Люди та AI-фахівці, призначені до цього робочого простору", "У команді поки нікого немає", "Зібрати команду"),
            "en": ("Team", "People and AI specialists assigned to this workspace", "No team members yet", "Build a team"),
        }[self.language]
        self.heading.setText(copy[0])
        self.subtitle.setText(copy[1])
        self._empty_text = copy[2]
        self.create_button.setText(copy[3])
        if hasattr(self, "list"):
            self._rendered_agents = getattr(self, "_rendered_agents", ())
            self.render(self._rendered_agents)

    def render(self, agents: list[ChatAgent] | tuple[ChatAgent, ...]) -> None:
        self._rendered_agents = tuple(agents)
        self.list.clear()
        if not agents:
            self.create_button.setVisible(True)
            item = QListWidgetItem(self._empty_text)
            item.setTextAlignment(Qt.AlignCenter)
            self.list.addItem(item)
            return
        self.create_button.setVisible(False)
        role_labels = {
            "ru": {"PROJECT_MANAGER": "Руководитель проекта", "DESIGN_ENGINEER": "Инженер-проектировщик", "QA_ENGINEER": "Инженер ОТК", "DOCUMENT_CONTROL_OFFICER": "Специалист по документации", "VERIFICATION_ENGINEER": "Инженер проверки", "LEARNING_COORDINATOR": "Координатор обучения"},
            "uk": {"PROJECT_MANAGER": "Керівник проєкту", "DESIGN_ENGINEER": "Інженер-проєктувальник", "QA_ENGINEER": "Інженер ОТК", "DOCUMENT_CONTROL_OFFICER": "Фахівець з документації", "VERIFICATION_ENGINEER": "Інженер перевірки", "LEARNING_COORDINATOR": "Координатор навчання"},
            "en": {"PROJECT_MANAGER": "Project manager", "DESIGN_ENGINEER": "Design engineer", "QA_ENGINEER": "QA engineer", "DOCUMENT_CONTROL_OFFICER": "Documentation specialist", "VERIFICATION_ENGINEER": "Verification engineer", "LEARNING_COORDINATOR": "Learning coordinator"},
        }[self.language]
        for agent in agents:
            card = QFrame()
            card.setObjectName("luminiferaTeamCard")
            row = QHBoxLayout(card)
            row.setContentsMargins(14, 12, 14, 12)
            avatar = QLabel()
            avatar.setFixedSize(48, 48)
            avatar.setAlignment(Qt.AlignCenter)
            pixmap = QPixmap(agent.avatar_path) if agent.avatar_path and Path(agent.avatar_path).is_file() else QPixmap()
            if pixmap.isNull():
                avatar.setText(agent.chat_display_name[:1].upper())
            else:
                avatar.setPixmap(pixmap.scaled(48, 48, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
            row.addWidget(avatar)
            text = QVBoxLayout()
            name = QLabel(agent.chat_display_name)
            name.setObjectName("luminiferaTeamName")
            role = role_labels.get(agent.primary_role, agent.primary_role.replace("_", " ").title())
            role_label = QLabel(role)
            role_label.setObjectName("luminiferaWorkMuted")
            responsibility = QLabel(agent.description or ({"ru": "Отвечает за свою часть работы", "uk": "Відповідає за свою частину роботи", "en": "Owns a part of the work"}[self.language]))
            responsibility.setWordWrap(True)
            responsibility.setObjectName("luminiferaTeamResponsibility")
            text.addWidget(name)
            text.addWidget(role_label)
            text.addWidget(responsibility)
            row.addLayout(text, 1)
            item = QListWidgetItem()
            item.setSizeHint(card.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, card)
    create_team_requested = Signal()
