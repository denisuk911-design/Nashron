from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget

from core.luminifera_work_service import WorkSnapshot


COPY = {
    "ru": {"heading": "Работа", "iris": "Сформулировать цель с Iris", "empty": "Цель ещё не сформулирована", "empty_body": "Опишите Iris, какой результат нужно получить.", "status": "Статус: {state}", "next": "Следующее действие: {action}", "start": "Начать выполнение", "review_next": "Проверить результат", "talk": "Поговорить с Iris", "team": "Команда", "members": "{count} участников", "results": "Результаты", "no_results": "Артефактов пока нет", "review": "Проверка", "findings": "Замечаний: {count}"},
    "uk": {"heading": "Робота", "iris": "Сформулювати ціль з Iris", "empty": "Ціль ще не сформульована", "empty_body": "Опишіть Iris, який результат потрібно отримати.", "status": "Статус: {state}", "next": "Наступна дія: {action}", "start": "Почати виконання", "review_next": "Перевірити результат", "talk": "Поговорити з Iris", "team": "Команда", "members": "{count} учасників", "results": "Результати", "no_results": "Артефактів поки немає", "review": "Перевірка", "findings": "Зауважень: {count}"},
    "en": {"heading": "Work", "iris": "Define a goal with Iris", "empty": "No goal has been defined yet", "empty_body": "Tell Iris what result you want.", "status": "Status: {state}", "next": "Next action: {action}", "start": "Start work", "review_next": "Review result", "talk": "Talk to Iris", "team": "Team", "members": "{count} members", "results": "Results", "no_results": "No artifacts yet", "review": "Review", "findings": "Findings: {count}"},
}


class WorkDashboard(QWidget):
    talk_to_iris = Signal()

    def __init__(self, language: str = "ru", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("luminiferaWork")
        self.language = language if language in COPY else "ru"
        self._snapshot = WorkSnapshot()
        self._build()
        self.render(WorkSnapshot())

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(42, 32, 42, 32)
        layout.setSpacing(18)
        heading_row = QHBoxLayout()
        self.heading = QLabel(objectName="luminiferaWorkHeading")
        heading_row.addWidget(self.heading)
        heading_row.addStretch(1)
        self.iris_button = QPushButton(objectName="luminiferaHomePrimary")
        self.iris_button.clicked.connect(self.talk_to_iris)
        heading_row.addWidget(self.iris_button)
        layout.addLayout(heading_row)
        self.goal_card = QFrame(objectName="luminiferaWorkGoal")
        goal_layout = QVBoxLayout(self.goal_card)
        goal_layout.setContentsMargins(24, 20, 24, 20)
        self.goal_title = QLabel(objectName="luminiferaWorkGoalTitle")
        self.goal_title.setWordWrap(True)
        goal_layout.addWidget(self.goal_title)
        self.goal_status = QLabel(objectName="luminiferaWorkMuted")
        goal_layout.addWidget(self.goal_status)
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        goal_layout.addWidget(self.progress)
        self.goal_next = QLabel(objectName="luminiferaWorkNext")
        goal_layout.addWidget(self.goal_next)
        layout.addWidget(self.goal_card)
        cards = QHBoxLayout()
        self.team_card, self.team_heading, self.team_body = self._card()
        self.artifacts_card, self.artifacts_heading, self.artifacts_body = self._card()
        self.review_card, self.review_heading, self.review_body = self._card()
        self.steps_card, self.steps_heading, self.steps_body = self._card()
        self.result_card, self.result_heading, self.result_body = self._card()
        for card in (self.team_card, self.artifacts_card, self.review_card, self.steps_card, self.result_card):
            cards.addWidget(card)
        layout.addLayout(cards)
        layout.addStretch(1)

    @staticmethod
    def _card() -> tuple[QFrame, QLabel, QLabel]:
        card = QFrame(objectName="luminiferaWorkCard")
        content = QVBoxLayout(card)
        content.setContentsMargins(18, 16, 18, 16)
        heading = QLabel(objectName="luminiferaWorkCardHeading")
        body = QLabel(objectName="luminiferaWorkCardBody")
        body.setWordWrap(True)
        content.addWidget(heading)
        content.addWidget(body)
        return card, heading, body

    def set_language(self, language: str) -> None:
        self.language = language if language in COPY else "ru"
        self.render(self._snapshot)

    def render(self, snapshot: WorkSnapshot) -> None:
        self._snapshot = snapshot
        copy = COPY[self.language]
        self.heading.setText(copy["heading"])
        self.iris_button.setText(copy["iris"])
        self.goal_title.setText(snapshot.goal_title or copy["empty"])
        state_labels = {
            "ru": {"PENDING": "Ожидает запуска", "PLANNED": "Запланирована", "IN_PROGRESS": "В работе", "REVIEW": "На проверке", "COMPLETED": "Завершена", "BLOCKED": "Заблокирована", "CANCELLED": "Отменена"},
            "uk": {"PENDING": "Очікує запуску", "PLANNED": "Запланована", "IN_PROGRESS": "У роботі", "REVIEW": "На перевірці", "COMPLETED": "Завершена", "BLOCKED": "Заблокована", "CANCELLED": "Скасована"},
            "en": {"PENDING": "Waiting to start", "PLANNED": "Planned", "IN_PROGRESS": "In progress", "REVIEW": "In review", "COMPLETED": "Completed", "BLOCKED": "Blocked", "CANCELLED": "Cancelled"},
        }
        for labels in state_labels.values():
            labels.update({"RUNNING": labels.get("IN_PROGRESS", "In progress"), "REWORK": labels.get("BLOCKED", "Blocked"), "FAILED": labels.get("BLOCKED", "Blocked")})
        fallback_state = {"ru": "В работе", "uk": "У роботі", "en": "In progress"}[self.language]
        state = state_labels[self.language].get(snapshot.goal_state.upper(), fallback_state) if snapshot.goal_state else ""
        self.goal_status.setText(copy["status"].format(state=state) if state else copy["empty_body"])
        self.progress.setValue(snapshot.goal_progress)
        action = copy["review_next"] if snapshot.goal_progress >= 75 else copy["start"] if snapshot.goal_title else copy["talk"]
        self.goal_next.setText(copy["next"].format(action=action))
        self.team_heading.setText(copy["team"])
        self.team_body.setText(copy["members"].format(count=snapshot.team_size))
        self.artifacts_heading.setText(copy["results"])
        self.artifacts_body.setText("\n".join(item.title for item in snapshot.artifacts) or copy["no_results"])
        self.review_heading.setText(copy["review"])
        self.review_body.setText(copy["findings"].format(count=snapshot.findings))
        result_labels = {
            "ru": ("Проверенный результат", "Готов: {artifacts} материалов, {evidence} подтверждений", "Проверка еще не завершена"),
            "uk": ("Перевірений результат", "Готово: {artifacts} матеріалів, {evidence} підтверджень", "Перевірку ще не завершено"),
            "en": ("Verified result", "Ready: {artifacts} artifacts, {evidence} evidence records", "Review is not complete yet"),
        }[self.language]
        self.result_heading.setText(result_labels[0])
        self.result_body.setText(
            result_labels[1].format(artifacts=len(snapshot.artifacts), evidence=snapshot.evidence_count)
            if snapshot.receipt_ready else result_labels[2]
        )
        self.steps_heading.setText({"ru": "Этапы", "uk": "Етапи", "en": "Steps"}[self.language])
        step_labels = {
            "ASSIGNED": {"ru": "Назначен", "uk": "Призначено", "en": "Assigned"},
            "RUNNING": {"ru": "В работе", "uk": "У роботі", "en": "Working"},
            "AWAITING_REVIEW": {"ru": "На проверке", "uk": "На перевірці", "en": "In review"},
            "COMPLETED": {"ru": "Завершён", "uk": "Завершено", "en": "Completed"},
        }
        fallback_step = {"ru": "В работе", "uk": "У роботі", "en": "In progress"}[self.language]
        steps = [f"{item.title}: {step_labels.get(item.status, {}).get(self.language, fallback_step)}" for item in snapshot.steps]
        self.steps_body.setText("\n".join(steps) or {"ru": "Этапы появятся после запуска цели", "uk": "Етапи з'являться після запуску цілі", "en": "Steps appear after the goal starts"}[self.language])
