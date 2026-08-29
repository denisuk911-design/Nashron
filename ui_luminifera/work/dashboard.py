from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget

from core.luminifera_work_service import WorkSnapshot


class WorkDashboard(QWidget):
    talk_to_iris = Signal()

    def __init__(self, language: str = "ru", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("luminiferaWork")
        self.language = language if language in {"ru", "uk", "en"} else "ru"
        self._build()
        self.render(WorkSnapshot())

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(42, 32, 42, 32)
        layout.setSpacing(18)
        heading_row = QHBoxLayout()
        self.heading = QLabel()
        self.heading.setObjectName("luminiferaWorkHeading")
        heading_row.addWidget(self.heading)
        heading_row.addStretch(1)
        self.iris_button = QPushButton()
        self.iris_button.setObjectName("luminiferaHomePrimary")
        self.iris_button.clicked.connect(self.talk_to_iris)
        heading_row.addWidget(self.iris_button)
        layout.addLayout(heading_row)

        self.goal_card = QFrame()
        self.goal_card.setObjectName("luminiferaWorkGoal")
        goal_layout = QVBoxLayout(self.goal_card)
        goal_layout.setContentsMargins(24, 20, 24, 20)
        self.goal_title = QLabel()
        self.goal_title.setObjectName("luminiferaWorkGoalTitle")
        self.goal_title.setWordWrap(True)
        goal_layout.addWidget(self.goal_title)
        self.goal_status = QLabel()
        self.goal_status.setObjectName("luminiferaWorkMuted")
        goal_layout.addWidget(self.goal_status)
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        goal_layout.addWidget(self.progress)
        self.goal_next = QLabel()
        self.goal_next.setObjectName("luminiferaWorkNext")
        goal_layout.addWidget(self.goal_next)
        layout.addWidget(self.goal_card)

        cards = QHBoxLayout()
        self.team_card = self._card()
        self.artifacts_card = self._card()
        self.review_card = self._card()
        cards.addWidget(self.team_card)
        cards.addWidget(self.artifacts_card)
        cards.addWidget(self.review_card)
        layout.addLayout(cards)
        layout.addStretch(1)

    @staticmethod
    def _card() -> QFrame:
        card = QFrame()
        card.setObjectName("luminiferaWorkCard")
        content = QVBoxLayout(card)
        content.setContentsMargins(18, 16, 18, 16)
        content.addWidget(QLabel(objectName="luminiferaWorkCardHeading"))
        content.addWidget(QLabel(objectName="luminiferaWorkCardBody"))
        return card

    @staticmethod
    def _labels(card: QFrame) -> tuple[QLabel, QLabel]:
        labels = card.findChildren(QLabel)
        return labels[0], labels[1]

    def set_language(self, language: str) -> None:
        self.language = language if language in {"ru", "uk", "en"} else "ru"

    def render(self, snapshot: WorkSnapshot) -> None:
        copy = {
            "ru": {"heading": "Работа", "iris": "Сформулировать цель с Iris", "empty": "Цель ещё не сформулирована", "empty_body": "Опишите Iris, какой результат нужно получить.", "status": "Статус: {state}", "next": "Следующее действие: {next}", "team": "Команда", "team_body": "{count} участников", "artifacts": "Результаты", "artifacts_empty": "Пока нет артефактов", "review": "Проверка", "review_body": "Замечаний: {count}"},
            "uk": {"heading": "Робота", "iris": "Сформулювати ціль з Iris", "empty": "Ціль ще не сформульована", "empty_body": "Опишіть Iris, який результат потрібно отримати.", "status": "Статус: {state}", "next": "Наступна дія: {next}", "team": "Команда", "team_body": "{count} учасників", "artifacts": "Результати", "artifacts_empty": "Результатів поки немає", "review": "Перевірка", "review_body": "Зауважень: {count}"},
            "en": {"heading": "Work", "iris": "Define a goal with Iris", "empty": "No goal has been defined yet", "empty_body": "Tell Iris what result you want.", "status": "Status: {state}", "next": "Next action: {next}", "team": "Team", "team_body": "{count} members", "artifacts": "Results", "artifacts_empty": "No artifacts yet", "review": "Review", "review_body": "Findings: {count}"},
        }[self.language]
        self.heading.setText(copy["heading"])
        self.iris_button.setText(copy["iris"])
        self.goal_title.setText(snapshot.goal_title or copy["empty"])
        state = snapshot.goal_state.replace("_", " ").title() if snapshot.goal_state else copy["empty_body"]
        self.goal_status.setText(copy["status"].format(state=state) if snapshot.goal_state else copy["empty_body"])
        self.progress.setValue(snapshot.goal_progress)
        next_action = "Проверить результат" if snapshot.goal_progress >= 75 else "Начать выполнение" if snapshot.goal_title else "Поговорить с Iris"
        self.goal_next.setText(copy["next"].format(next=next_action))
        team_heading, team_body = self._labels(self.team_card)
        artifacts_heading, artifacts_body = self._labels(self.artifacts_card)
        review_heading, review_body = self._labels(self.review_card)
        team_heading.setText(copy["team"])
        team_body.setText(copy["team_body"].format(count=snapshot.team_size))
        artifacts_heading.setText(copy["artifacts"])
        artifacts_body.setText("\n".join(item.title for item in snapshot.artifacts) or copy["artifacts_empty"])
        review_heading.setText(copy["review"])
        review_body.setText(copy["review_body"].format(count=snapshot.findings))
