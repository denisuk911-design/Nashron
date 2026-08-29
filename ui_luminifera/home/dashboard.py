from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from core.luminifera_home_service import HomeSnapshot


COPY = {
    "ru": {"eyebrow": "LUMINIFERA", "title": "Опишите, чего хотите добиться.", "description": "Iris поможет собрать команду, превратить цель в работу и сохранить проверенный результат.", "talk": "Поговорить с Iris", "create": "Создать команду", "demo": "Запустить демо", "work": "Открыть работу", "team": "Команда", "members": "{count} участников готовы к работе", "goal": "Текущая цель", "no_goal": "Активной цели пока нет", "results": "Последние результаты", "no_results": "Результаты появятся после начала работы", "workspace": "РАБОЧЕЕ ПРОСТРАНСТВО", "ready": "Команда готова. Следующий шаг определим вместе с Iris."},
    "uk": {"eyebrow": "LUMINIFERA", "title": "Опишіть, чого хочете досягти.", "description": "Iris допоможе зібрати команду, перетворити ціль на роботу та зберегти перевірений результат.", "talk": "Поговорити з Iris", "create": "Створити команду", "demo": "Запустити демо", "work": "Відкрити роботу", "team": "Команда", "members": "{count} учасників готові до роботи", "goal": "Поточна ціль", "no_goal": "Активної цілі поки немає", "results": "Останні результати", "no_results": "Результати з'являться після початку роботи", "workspace": "РОБОЧИЙ ПРОСТІР", "ready": "Команда готова. Наступний крок визначимо разом з Iris."},
    "en": {"eyebrow": "LUMINIFERA", "title": "Describe what you want to achieve.", "description": "Iris will assemble a team, turn the goal into work, and retain a verified result.", "talk": "Talk to Iris", "create": "Create a team", "demo": "Run demo", "work": "Open work", "team": "Team", "members": "{count} members are ready to work", "goal": "Current goal", "no_goal": "There is no active goal yet", "results": "Recent results", "no_results": "Results will appear after work begins", "workspace": "WORKSPACE", "ready": "Your team is ready. We will choose the next step with Iris."},
}


class HomeDashboard(QWidget):
    talk_to_iris = Signal()
    create_team_requested = Signal()
    demo_requested = Signal()
    work_requested = Signal()

    def __init__(self, language: str = "ru", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("luminiferaHome")
        self._language = language if language in COPY else "ru"
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
        self.eyebrow = QLabel(objectName="luminiferaHomeEyebrow")
        self.eyebrow.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(self.eyebrow)
        self.title = QLabel(objectName="luminiferaHomeTitle")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setWordWrap(True)
        hero_layout.addWidget(self.title)
        self.description = QLabel(objectName="luminiferaHomeDescription")
        self.description.setAlignment(Qt.AlignCenter)
        self.description.setWordWrap(True)
        hero_layout.addWidget(self.description)
        self.primary = QPushButton(objectName="luminiferaHomePrimary")
        self.primary.clicked.connect(self.talk_to_iris)
        hero_layout.addWidget(self.primary, 0, Qt.AlignHCenter)
        secondary = QHBoxLayout()
        secondary.setSpacing(10)
        self.create_team = QPushButton(objectName="luminiferaHomeSecondary")
        self.create_team.clicked.connect(self.create_team_requested)
        self.demo = QPushButton(objectName="luminiferaHomeSecondary")
        self.demo.clicked.connect(self.demo_requested)
        self.open_work = QPushButton(objectName="luminiferaHomeSecondary")
        self.open_work.clicked.connect(self.work_requested)
        secondary.addStretch(1)
        secondary.addWidget(self.create_team)
        secondary.addWidget(self.demo)
        secondary.addWidget(self.open_work)
        secondary.addStretch(1)
        hero_layout.addLayout(secondary)
        layout.addWidget(self.hero, 0, Qt.AlignHCenter)
        summary = QHBoxLayout()
        summary.setSpacing(14)
        self.team_card, self.team_heading, self.team_body = self._summary_card()
        self.goal_card, self.goal_heading, self.goal_body = self._summary_card()
        self.artifact_card, self.artifact_heading, self.artifact_body = self._summary_card()
        for card in (self.team_card, self.goal_card, self.artifact_card):
            summary.addWidget(card)
        layout.addLayout(summary)
        layout.addStretch(2)

    @staticmethod
    def _summary_card() -> tuple[QFrame, QLabel, QLabel]:
        card = QFrame(objectName="luminiferaHomeSummary")
        content = QVBoxLayout(card)
        content.setContentsMargins(18, 16, 18, 16)
        heading = QLabel(objectName="luminiferaHomeSummaryHeading")
        body = QLabel(objectName="luminiferaHomeSummaryBody")
        body.setWordWrap(True)
        content.addWidget(heading)
        content.addWidget(body)
        return card, heading, body

    def set_language(self, language: str) -> None:
        self._language = language if language in COPY else "ru"

    def render(self, snapshot: HomeSnapshot) -> None:
        copy = COPY[self._language]
        has_org = snapshot.has_organization
        self.eyebrow.setText(copy["workspace"] if has_org else copy["eyebrow"])
        self.title.setText(snapshot.organization_name if has_org else copy["title"])
        self.description.setText(copy["ready"] if has_org else copy["description"])
        self.primary.setText(copy["talk"])
        self.create_team.setText(copy["create"])
        self.demo.setText(copy["demo"])
        self.open_work.setText(copy["work"])
        self.create_team.setVisible(not has_org)
        self.demo.setVisible(not has_org)
        self.open_work.setVisible(has_org)
        self.team_heading.setText(copy["team"])
        self.team_body.setText(copy["members"].format(count=snapshot.team_size) if has_org else copy["no_goal"])
        self.goal_heading.setText(copy["goal"])
        self.goal_body.setText(snapshot.goal_title or copy["no_goal"])
        self.artifact_heading.setText(copy["results"])
        self.artifact_body.setText("\n".join(item.title for item in snapshot.artifacts) or copy["no_results"])
        for card in (self.team_card, self.goal_card, self.artifact_card):
            card.setVisible(has_org)
