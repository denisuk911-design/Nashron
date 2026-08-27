from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QSizePolicy, QScrollArea, QVBoxLayout
from gui.dialog_chrome import apply_team_dialog_chrome


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}


class ImageThumbnail(QLabel):
    def __init__(self, image_path: Path) -> None:
        super().__init__()
        self.image_path = image_path
        self.setObjectName("imageThumbnail")
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(str(image_path))
        pixmap = QPixmap(str(image_path))
        if not pixmap.isNull():
            self.setPixmap(pixmap.scaled(220, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.setFixedSize(230, 150)
        self.setAlignment(Qt.AlignCenter)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._open_preview()
            event.accept()
            return
        super().mousePressEvent(event)

    def _open_preview(self) -> None:
        dialog = QDialog(self)
        apply_team_dialog_chrome(dialog, minimum_width=700)
        dialog.setWindowTitle(self.image_path.name)
        dialog.resize(900, 700)
        layout = QVBoxLayout(dialog)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(str(self.image_path))
        label.setPixmap(pixmap)
        scroll.setWidget(label)
        layout.addWidget(scroll)
        dialog.exec()


class MessageWidget(QFrame):
    """A standalone message card; the history is never rendered into one text editor."""

    def __init__(
        self,
        role: str,
        content: str,
        created_at: str = "",
        author_name: str | None = None,
        avatar_path: str | None = None,
        author_title: str | None = None,
        attachment_paths: list[Path] | None = None,
    ) -> None:
        super().__init__()
        self.role = role
        self.content = content
        object_name = "messageCardUser" if role == "user" else "messageCard"
        self._max_card_width = 560 if role == "user" else 840
        self.setObjectName("messageRow")
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(18, 8, 18, 8)
        outer.setSpacing(12)
        if role == "user":
            outer.addStretch(1)
        elif avatar_path:
            avatar = self._make_avatar(avatar_path)
            if avatar is not None:
                outer.addWidget(avatar)

        self.card = QFrame()
        card = self.card
        card.setObjectName(object_name)
        card.setMaximumWidth(self._max_card_width)
        card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(6)

        header = QHBoxLayout()
        author = QLabel(author_name or ("Вы" if role == "user" else "Сотрудник"))
        author.setObjectName("pageTitle")
        meta = QLabel(created_at or "сейчас")
        meta.setObjectName("messageMeta")
        header.addWidget(author)
        if author_title:
            title = QLabel(author_title)
            title.setObjectName("messageRole")
            header.addWidget(title)
        header.addStretch(1)
        header.addWidget(meta)
        card_layout.addLayout(header)

        self.body = QLabel()
        self.body.setObjectName("messageBody")
        self.body.setTextFormat(Qt.PlainText)
        self.body.setWordWrap(True)
        self.body.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.body.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        card_layout.addWidget(self.body)
        self.activity = QLabel()
        self.activity.setObjectName("messageActivity")
        self.activity.setTextFormat(Qt.PlainText)
        self.activity.setWordWrap(True)
        self.activity.setVisible(False)
        card_layout.addWidget(self.activity)
        self.image_row = QHBoxLayout()
        self.image_row.setSpacing(8)
        card_layout.addLayout(self.image_row)
        self.set_content(content, attachment_paths)

        outer.addWidget(card)
        if role == "user" and avatar_path:
            avatar = self._make_avatar(avatar_path)
            if avatar is not None:
                outer.addWidget(avatar)
        if role != "user":
            outer.addStretch(1)

    def set_content(self, content: str, attachment_paths: list[Path] | None = None) -> None:
        self.content = content
        self.body.setText(content)
        self._set_images(attachment_paths if attachment_paths is not None else self._extract_image_paths(content))
        self._sync_body_width()
        self.updateGeometry()
        self.adjustSize()

    def set_activity(self, text: str) -> None:
        clean = text.strip()
        self.activity.setText(clean)
        self.activity.setVisible(bool(clean))
        self._sync_body_width()
        self.updateGeometry()
        self.adjustSize()

    def set_selected(self, selected: bool) -> None:
        self.card.setProperty("selected", bool(selected))
        self.card.style().unpolish(self.card)
        self.card.style().polish(self.card)
        self.card.update()

    def sizeHint(self) -> QSize:
        width = max(220, self.width() or 720)
        layout_hint = self.layout().sizeHint()
        total_height = max(layout_hint.height(), self.card.layout().sizeHint().height() + 16)
        return QSize(width, total_height)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_body_width()

    @staticmethod
    def _make_avatar(avatar_path: str) -> QLabel | None:
        pixmap = QPixmap(avatar_path)
        if pixmap.isNull():
            return None
        avatar = QLabel()
        avatar.setObjectName("messageAvatar")
        avatar.setPixmap(pixmap.scaled(44, 44, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        avatar.setFixedSize(48, 48)
        avatar.setAlignment(Qt.AlignCenter)
        return avatar

    def _sync_body_width(self) -> None:
        outer_margins = self.layout().contentsMargins()
        available_width = max(220, self.width() - outer_margins.left() - outer_margins.right()) if self.width() else 720
        avatar_width = 60 if self.layout().count() > 1 else 0
        available_width = max(220, available_width - avatar_width)
        card_margins = self.card.layout().contentsMargins()
        max_text_width = max(140, min(self._max_card_width, available_width) - card_margins.left() - card_margins.right())
        natural_width = self._natural_text_width()
        card_width = min(self._max_card_width, max(220, natural_width + card_margins.left() + card_margins.right()))
        card_width = min(card_width, max(220, available_width))
        self.card.setFixedWidth(card_width)
        text_width = max(140, min(max_text_width, card_width - card_margins.left() - card_margins.right()))
        self.body.setFixedWidth(text_width)
        self.body.adjustSize()
        self.body.setFixedHeight(self._wrapped_text_height(self.body.text(), text_width, self.body))
        self.activity.setFixedWidth(text_width)
        if self.activity.isVisible():
            self.activity.adjustSize()
            self.activity.setFixedHeight(self._wrapped_text_height(self.activity.text(), text_width, self.activity))
        else:
            self.activity.setFixedHeight(0)

    def _natural_text_width(self) -> int:
        lines = [self.body.text(), self.activity.text() if self.activity.isVisible() else ""]
        width = max((self.body.fontMetrics().horizontalAdvance(line) for text in lines for line in text.splitlines()), default=0)
        header_width = self.card.layout().itemAt(0).sizeHint().width() if self.card.layout().count() else 0
        image_width = 238 if self.image_row.count() else 0
        return max(220, min(self._max_card_width - 32, max(width, header_width, image_width)))

    @staticmethod
    def _wrapped_text_height(text: str, width: int, label: QLabel) -> int:
        if not text:
            return label.fontMetrics().lineSpacing()
        rect = label.fontMetrics().boundingRect(
            QRect(0, 0, max(80, width), 100000),
            Qt.TextWordWrap | Qt.TextExpandTabs,
            text,
        )
        return max(label.fontMetrics().lineSpacing() + 8, rect.height() + 8)

    def _set_images(self, paths: list[Path]) -> None:
        while self.image_row.count():
            item = self.image_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for path in paths[:4]:
            self.image_row.addWidget(ImageThumbnail(path))
        if paths:
            self.image_row.addStretch(1)

    @staticmethod
    def _extract_image_paths(content: str) -> list[Path]:
        candidates = set()
        for match in re.finditer(r"[`'\"]([^`'\"]+\.(?:png|jpg|jpeg|bmp|gif))[`'\"]", content, re.IGNORECASE):
            candidates.add(match.group(1))
        for match in re.finditer(r"([A-Za-z]:\\[^\n\r`'\"]+\.(?:png|jpg|jpeg|bmp|gif))", content, re.IGNORECASE):
            candidates.add(match.group(1).rstrip(" .,)"))
        paths: list[Path] = []
        for candidate in candidates:
            path = Path(candidate)
            if path.suffix.lower() in IMAGE_EXTENSIONS and path.exists():
                paths.append(path)
        return sorted(paths, key=lambda item: str(item).lower())
