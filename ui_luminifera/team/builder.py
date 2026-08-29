from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QTextEdit, QVBoxLayout

from gui.localization import catalog_label


COPY = {
    "ru": {"title": "Собрать команду", "question": "Что хотите реализовать?", "description": "Опишите желаемый результат или область работы.", "name": "Название команды", "placeholder": "Например: Команда запуска продукта", "show": "Показать состав", "proposal": "Предложенный состав", "create": "Создать команду", "cancel": "Отмена", "role": "Специалист", "responsibility": "Отвечает за свой участок работы"},
    "uk": {"title": "Зібрати команду", "question": "Що хочете реалізувати?", "description": "Опишіть бажаний результат або сферу роботи.", "name": "Назва команди", "placeholder": "Наприклад: Команда запуску продукту", "show": "Показати склад", "proposal": "Запропонований склад", "create": "Створити команду", "cancel": "Скасувати", "role": "Спеціаліст", "responsibility": "Відповідає за свою ділянку роботи"},
    "en": {"title": "Build a team", "question": "What do you want to build?", "description": "Describe the desired result or area of work.", "name": "Team name", "placeholder": "For example: Product launch team", "show": "Show team", "proposal": "Suggested team", "create": "Create team", "cancel": "Cancel", "role": "Specialist", "responsibility": "Owns a part of the work"},
}


class TeamBuilderDialog(QDialog):
    """Human-readable team proposal before the universal service is invoked."""

    def __init__(self, service, language: str = "ru", parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.language = language if language in COPY else "ru"
        self.build = None
        self._template = None
        copy = COPY[self.language]
        self.setWindowTitle(copy["title"])
        self.setMinimumSize(660, 520)
        layout = QVBoxLayout(self)
        intro = QLabel(copy["question"], objectName="luminiferaTeamBuilderTitle")
        layout.addWidget(intro)
        self.brief = QTextEdit()
        self.brief.setPlaceholderText(copy["description"])
        self.brief.setMinimumHeight(92)
        layout.addWidget(self.brief)
        form = QFormLayout()
        self.name = QLineEdit()
        self.name.setPlaceholderText(copy["placeholder"])
        form.addRow(copy["name"], self.name)
        layout.addLayout(form)
        self.propose = QDialogButtonBox(QDialogButtonBox.Apply | QDialogButtonBox.Cancel)
        self.propose.button(QDialogButtonBox.Apply).setText(copy["show"])
        self.propose.button(QDialogButtonBox.Cancel).setText(copy["cancel"])
        self.propose.clicked.connect(self._propose_clicked)
        layout.addWidget(self.propose)
        self.proposal_title = QLabel(copy["proposal"], objectName="luminiferaTeamBuilderSection")
        self.proposal_title.setVisible(False)
        layout.addWidget(self.proposal_title)
        self.roster = QListWidget()
        self.roster.setVisible(False)
        self.roster.setSpacing(4)
        layout.addWidget(self.roster, 1)
        self.actions = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.actions.button(QDialogButtonBox.Ok).setText(copy["create"])
        self.actions.button(QDialogButtonBox.Cancel).setText(copy["cancel"])
        self.actions.accepted.connect(self._create)
        self.actions.rejected.connect(self.reject)
        self.actions.setVisible(False)
        layout.addWidget(self.actions)

    def _propose_clicked(self, button) -> None:
        if button == self.propose.button(QDialogButtonBox.Cancel):
            self.reject()
            return
        brief = self.brief.toPlainText().strip()
        if not brief:
            return
        templates = self.service.list_templates()
        self._template = self.service._select_template_for_brief(brief, templates) if templates else None
        if self._template is None:
            return
        if not self.name.text().strip():
            self.name.setText(self._template.name.replace("_", " ").title())
        self.roster.clear()
        copy = COPY[self.language]
        for role in self._template.roles:
            position = str(role.get("position") or role.get("role") or copy["role"])
            responsibility = str(role.get("responsibility") or role.get("description") or copy["responsibility"])
            item = QListWidgetItem(f"{catalog_label(self.language, position)}\n{responsibility}")
            item.setData(Qt.UserRole, position)
            self.roster.addItem(item)
        self.proposal_title.setVisible(True)
        self.roster.setVisible(True)
        self.actions.setVisible(True)
        self.propose.setVisible(False)

    def _create(self) -> None:
        if self._template is None or not self.name.text().strip():
            return
        self.build = self.service.build_professional_team(self.brief.toPlainText().strip(), self.name.text().strip(), template_id=self._template.template_id)
        self.accept()
