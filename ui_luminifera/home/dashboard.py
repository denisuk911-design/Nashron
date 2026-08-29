from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from core.luminifera_home_service import HomeSnapshot


class HomeDashboard(QWidget):
    """Product Home. It only renders view state and emits user intent."""

    talk_to_iris = Signal()
    create_team_requested = Signal()
    demo_requested = Signal()
    work_requested = Signal()

    def __init__(self, language: str = "ru", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("luminiferaHome")
        self._language = language if language in {"ru", "uk", "en"} else "ru"
        self._build()
        self.render(HomeSnapshot(has_organization=False))

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(52, 46, 52, 46)
        layout.setSpacing(20)
        layout.addStretch(1)

        self.hero = QFrame()
        self.hero.setObjectName("luminiferaHomeHero")
        self.hero.setMaximumWidth(860)
        hero_layout = QVBoxLayout(self.hero)
        hero_layout.setContentsMargins(42, 38, 42, 38)
        hero_layout.setSpacing(14)
        self.eyebrow = QLabel()
        self.eyebrow.setObjectName("luminiferaHomeEyebrow")
        self.eyebrow.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(self.eyebrow)
        self.title = QLabel()
        self.title.setObjectName("luminiferaHomeTitle")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setWordWrap(True)
        hero_layout.addWidget(self.title)
        self.description = QLabel()
        self.description.setObjectName("luminiferaHomeDescription")
        self.description.setAlignment(Qt.AlignCenter)
        self.description.setWordWrap(True)
        hero_layout.addWidget(self.description)
        self.primary = QPushButton()
        self.primary.setObjectName("luminiferaHomePrimary")
        self.primary.clicked.connect(self.talk_to_iris)
        hero_layout.addWidget(self.primary, 0, Qt.AlignHCenter)
        self.secondary_row = QHBoxLayout()
        self.secondary_row.setSpacing(10)
        self.create_team = QPushButton()
        self.create_team.setObjectName("luminiferaHomeSecondary")
        self.create_team.clicked.connect(self.create_team_requested)
        self.demo = QPushButton()
        self.demo.setObjectName("luminiferaHomeSecondary")
        self.demo.clicked.connect(self.demo_requested)
        self.open_work = QPushButton()
        self.open_work.setObjectName("luminiferaHomeSecondary")
        self.open_work.clicked.connect(self.work_requested)
        self.secondary_row.addStretch(1)
        self.secondary_row.addWidget(self.create_team)
        self.secondary_row.addWidget(self.demo)
        self.secondary_row.addWidget(self.open_work)
        self.secondary_row.addStretch(1)
        hero_layout.addLayout(self.secondary_row)
        layout.addWidget(self.hero, 0, Qt.AlignHCenter)

        self.summary_row = QHBoxLayout()
        self.summary_row.setSpacing(14)
        self.team_card = self._summary_card()
        self.goal_card = self._summary_card()
        self.artifact_card = self._summary_card()
        self.summary_row.addWidget(self.team_card)
        self.summary_row.addWidget(self.goal_card)
        self.summary_row.addWidget(self.artifact_card)
        layout.addLayout(self.summary_row)
        layout.addStretch(2)

    @staticmethod
    def _summary_card() -> QFrame:
        card = QFrame()
        card.setObjectName("luminiferaHomeSummary")
        content = QVBoxLayout(card)
        content.setContentsMargins(18, 16, 18, 16)
        content.setSpacing(6)
        heading = QLabel()
        heading.setObjectName("luminiferaHomeSummaryHeading")
        body = QLabel()
        body.setObjectName("luminiferaHomeSummaryBody")
        body.setWordWrap(True)
        content.addWidget(heading)
        content.addWidget(body)
        return card

    @staticmethod
    def _labels(card: QFrame) -> tuple[QLabel, QLabel]:
        labels = card.findChildren(QLabel)
        return labels[0], labels[1]

    def set_language(self, language: str) -> None:
        self._language = language if language in {"ru", "uk", "en"} else "ru"

    def render(self, snapshot: HomeSnapshot) -> None:
        copy = {
            "ru": {
                "empty_eyebrow": "LUMINIFERA",
                "empty_title": "Опишите, чего хотите добиться.",
                "empty_description": "Iris поможет собрать команду, разложить цель на работу и сохранить результаты.",
                "team_eyebrow": "РАБОЧЕЕ ПРОСТРАНСТВО",
                "team_title": "{organization}",
                "team_description": "Команда готова. Следующий шаг определит Iris вместе с вами.",
                "primary": "Поговорить с Iris",
                "create": "Создать команду",
                "demo": "Запустить демо",
                "work": "Открыть работу",
                "team_heading": "Команда",
                "team_body": "{count} участников готовы к работе",
                "goal_heading": "Текущая цель",
                "goal_empty": "Пока нет активной цели",
                "artifacts_heading": "Последние результаты",
                "artifacts_empty": "Результаты появятся после начала работы",
            },
            "uk": {
                "empty_eyebrow": "LUMINIFERA", "empty_title": "Опишіть, чого хочете досягти.",
                "empty_description": "Iris допоможе зібрати команду, розкласти ціль на роботу та зберегти результати.",
                "team_eyebrow": "РОБОЧИЙ ПРОСТІР", "team_title": "{organization}",
                "team_description": "Команда готова. Наступний крок Iris визначить разом із вами.",
                "primary": "Поговорити з Iris", "create": "Створити команду", "demo": "Запустити демо", "work": "Відкрити роботу",
                "team_heading": "Команда", "team_body": "{count} учасників готові до роботи", "goal_heading": "Поточна ціль",
                "goal_empty": "Активної цілі поки немає", "artifacts_heading": "Останні результати",
                "artifacts_empty": "Результати з'являться після початку роботи",
            },
            "en": {
                "empty_eyebrow": "LUMINIFERA", "empty_title": "Describe what you want to achieve.",
                "empty_description": "Iris will help assemble a team, turn the goal into work, and retain the results.",
                "team_eyebrow": "WORKSPACE", "team_title": "{organization}",
                "team_description": "Your team is ready. Iris will determine the next step with you.",
                "primary": "Talk to Iris", "create": "Create a team", "demo": "Run demo", "work": "Open work",
                "team_heading": "Team", "team_body": "{count} members are ready to work", "goal_heading": "Current goal",
                "goal_empty": "There is no active goal yet", "artifacts_heading": "Recent results",
                "artifacts_empty": "Results will appear after work begins",
            },
        }[self._language]
        has_org = snapshot.has_organization
        self.eyebrow.setText(copy["team_eyebrow"] if has_org else copy["empty_eyebrow"])
        self.title.setText(copy["team_title"].format(organization=snapshot.organization_name) if has_org else copy["empty_title"])
        self.description.setText(copy["team_description"] if has_org else copy["empty_description"])
        self.primary.setText(copy["primary"])
        self.create_team.setText(copy["create"])
        self.demo.setText(copy["demo"])
        self.open_work.setText(copy["work"])
        self.create_team.setVisible(not has_org)
        self.demo.setVisible(not has_org)
        self.open_work.setVisible(has_org)

        team_heading, team_body = self._labels(self.team_card)
        goal_heading, goal_body = self._labels(self.goal_card)
        artifact_heading, artifact_body = self._labels(self.artifact_card)
        team_heading.setText(copy["team_heading"])
        team_body.setText(copy["team_body"].format(count=snapshot.team_size) if has_org else copy["goal_empty"])
        goal_heading.setText(copy["goal_heading"])
        goal_body.setText(snapshot.goal_title or copy["goal_empty"])
        artifact_heading.setText(copy["artifacts_heading"])
        artifact_body.setText("\n".join(item.title for item in snapshot.artifacts) or copy["artifacts_empty"])
        for card in (self.team_card, self.goal_card, self.artifact_card):
            card.setVisible(has_org)
