from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QTextEdit, QVBoxLayout

from gui.localization import catalog_label


class TeamBuilderDialog(QDialog):
    """Human-readable team proposal before the universal service is invoked."""

    def __init__(self, service, language: str = "ru", parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.language = language if language in {"ru", "uk", "en"} else "ru"
        self.build = None
        self._template = None
        self.setWindowTitle({"ru": "Собрать команду", "uk": "Зібрати команду", "en": "Build a team"}[self.language])
        self.setMinimumSize(660, 520)
        self._build_ui()

    def _build_ui(self) -> None:
        copy = {
            "ru": ("Что хотите реализовать?", "Опишите желаемый результат или область работы.", "Название команды", "Например: Команда запуска продукта", "Показать состав", "Предложенный состав", "Создать команду"),
            "uk": ("Що хочете реалізувати?", "Опишіть бажаний результат або сферу роботи.", "Назва команди", "Наприклад: Команда запуску продукту", "Показати склад", "Запропонований склад", "Створити команду"),
            "en": ("What do you want to build?", "Describe the desired result or area of work.", "Team name", "For example: Product launch team", "Show team", "Suggested team", "Create team"),
        }[self.language]
        layout = QVBoxLayout(self)
        intro = QLabel(copy[0])
        intro.setObjectName("luminiferaTeamBuilderTitle")
        layout.addWidget(intro)
        self.brief = QTextEdit()
        self.brief.setPlaceholderText(copy[1])
        self.brief.setMinimumHeight(92)
        layout.addWidget(self.brief)
        form = QFormLayout()
        self.name = QLineEdit()
        self.name.setPlaceholderText(copy[3])
        form.addRow(copy[2], self.name)
        layout.addLayout(form)
        self.propose = QDialogButtonBox(QDialogButtonBox.Apply | QDialogButtonBox.Cancel)
        self.propose.button(QDialogButtonBox.Apply).setText(copy[4])
        self.propose.button(QDialogButtonBox.Cancel).setText("Отмена" if self.language == "ru" else "Cancel")
        self.propose.clicked.connect(self._propose_clicked)
        layout.addWidget(self.propose)
        self.proposal_title = QLabel(copy[5])
        self.proposal_title.setObjectName("luminiferaTeamBuilderSection")
        self.proposal_title.setVisible(False)
        layout.addWidget(self.proposal_title)
        self.roster = QListWidget()
        self.roster.setVisible(False)
        self.roster.setSpacing(4)
        layout.addWidget(self.roster, 1)
        self.actions = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.actions.button(QDialogButtonBox.Ok).setText(copy[6])
        self.actions.button(QDialogButtonBox.Cancel).setText("Отмена" if self.language == "ru" else "Cancel")
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
        for role in self._template.roles:
            position = str(role.get("position") or role.get("role") or "Специалист")
            responsibility = str(role.get("responsibility") or role.get("description") or "Отвечает за свой участок работы")
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
        self.build = self.service.build_professional_team(
            self.brief.toPlainText().strip(), self.name.text().strip(), template_id=self._template.template_id
        )
        self.accept()
