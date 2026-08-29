from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from core.luminifera_files_service import ProductArtifact


class FilesBrowser(QWidget):
    open_workspace_requested = Signal()

    def __init__(self, language: str = "ru", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.language = language if language in {"ru", "uk", "en"} else "ru"
        self._artifacts: tuple[ProductArtifact, ...] = ()
        self.setObjectName("luminiferaFiles")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(42, 32, 42, 32)
        layout.setSpacing(14)
        header = QHBoxLayout()
        self.heading = QLabel()
        self.heading.setObjectName("luminiferaFilesHeading")
        header.addWidget(self.heading)
        header.addStretch(1)
        self.open_button = QPushButton()
        self.open_button.setObjectName("luminiferaHomeSecondary")
        self.open_button.clicked.connect(self.open_workspace_requested)
        header.addWidget(self.open_button)
        layout.addLayout(header)
        self.subtitle = QLabel()
        self.subtitle.setObjectName("luminiferaWorkMuted")
        layout.addWidget(self.subtitle)
        self.list = QListWidget()
        self.list.setObjectName("luminiferaFilesList")
        self.list.setSpacing(8)
        layout.addWidget(self.list, 1)
        self.set_language(self.language)

    def set_language(self, language: str) -> None:
        self.language = language if language in {"ru", "uk", "en"} else "ru"
        labels = {
            "ru": ("Файлы и результаты", "Артефакты, созданные и проверенные командой.", "Открыть рабочую папку", "Результатов пока нет"),
            "uk": ("Файли та результати", "Артефакти, створені та перевірені командою.", "Відкрити робочу папку", "Результатів поки немає"),
            "en": ("Files and results", "Artifacts created and reviewed by the team.", "Open workspace", "No results yet"),
        }[self.language]
        self.heading.setText(labels[0])
        self.subtitle.setText(labels[1])
        self.open_button.setText(labels[2])
        self._empty_text = labels[3]
        if hasattr(self, "list"):
            self.render(self._artifacts)

    def render(self, artifacts: tuple[ProductArtifact, ...]) -> None:
        self._artifacts = artifacts
        self.list.clear()
        if not artifacts:
            item = QListWidgetItem(self._empty_text)
            item.setTextAlignment(Qt.AlignCenter)
            self.list.addItem(item)
            return
        for artifact in artifacts:
            card = QFrame()
            card.setObjectName("luminiferaFileCard")
            row = QHBoxLayout(card)
            row.setContentsMargins(16, 12, 16, 12)
            icon = QLabel("▣")
            icon.setObjectName("luminiferaFileIcon")
            row.addWidget(icon)
            text = QVBoxLayout()
            title = QLabel(artifact.title)
            title.setObjectName("luminiferaFileTitle")
            meta = QLabel(
                f"{self._artifact_type_label(artifact.artifact_type)}  •  "
                f"{self._status_label(artifact.status)}  •  {artifact.modified[:16]}"
            )
            meta.setObjectName("luminiferaWorkMuted")
            text.addWidget(title)
            text.addWidget(meta)
            row.addLayout(text, 1)
            item = QListWidgetItem()
            item.setSizeHint(card.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, card)

    def _artifact_type_label(self, value: str) -> str:
        labels = {
            "ru": {"BOM": "Спецификация", "DOC": "Документ", "REPORT": "Отчёт", "WORK_PRODUCT": "Рабочий результат", "IMAGE": "Изображение"},
            "uk": {"BOM": "Специфікація", "DOC": "Документ", "REPORT": "Звіт", "WORK_PRODUCT": "Робочий результат", "IMAGE": "Зображення"},
            "en": {"BOM": "Bill of materials", "DOC": "Document", "REPORT": "Report", "WORK_PRODUCT": "Work product", "IMAGE": "Image"},
        }
        return labels[self.language].get(str(value or "").upper(), str(value or "Результат"))

    def _status_label(self, value: str) -> str:
        labels = {
            "ru": {"DRAFT": "Черновик", "READY": "Готов", "VERIFIED": "Проверен", "APPROVED": "Одобрен", "REJECTED": "Нужна доработка"},
            "uk": {"DRAFT": "Чернетка", "READY": "Готовий", "VERIFIED": "Перевірений", "APPROVED": "Схвалений", "REJECTED": "Потрібне доопрацювання"},
            "en": {"DRAFT": "Draft", "READY": "Ready", "VERIFIED": "Verified", "APPROVED": "Approved", "REJECTED": "Needs revision"},
        }
        return labels[self.language].get(str(value or "").upper(), str(value or ("Готовится" if self.language == "ru" else "Готується" if self.language == "uk" else "Preparing")))
