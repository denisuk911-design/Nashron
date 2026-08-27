from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from core.branding import BRAND_NAME, BRAND_TAGLINE


class StartupSplash(QWidget):
    def __init__(self, mark_path: Path | None = None) -> None:
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setObjectName("startupSplash")
        self.setFixedSize(420, 190)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(12)
        mark = QLabel()
        mark.setObjectName("splashMark")
        mark.setFixedSize(42, 42)
        if mark_path is not None and mark_path.is_file():
            mark.setPixmap(QPixmap(str(mark_path)).scaled(42, 42, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.setWindowIcon(QIcon(str(mark_path)))
        header.addWidget(mark)
        title = QLabel(BRAND_NAME)
        title.setObjectName("splashTitle")
        subtitle = QLabel(f"{BRAND_TAGLINE} · запускаю рабочее пространство")
        subtitle.setObjectName("splashSubtitle")
        self.status = QLabel("Подготовка интерфейса")
        self.status.setObjectName("splashStatus")
        progress = QProgressBar()
        progress.setRange(0, 0)
        progress.setTextVisible(False)

        header.addWidget(title)
        header.addStretch(1)
        layout.addLayout(header)
        layout.addWidget(subtitle)
        layout.addStretch(1)
        layout.addWidget(self.status)
        layout.addWidget(progress)
        self.setStyleSheet(
            """
            QWidget#startupSplash {
                background: #151b23;
                color: #f3f6fb;
                border: 1px solid #2a3442;
                border-radius: 10px;
            }
            QLabel#splashTitle {
                color: #f3f6fb;
                font: 700 18pt "Segoe UI";
            }
            QLabel#splashSubtitle {
                color: #b6c0ce;
                font: 10pt "Segoe UI";
            }
            QLabel#splashStatus {
                color: #58c4dd;
                font: 9pt "Segoe UI";
            }
            QLabel#splashMark { background: transparent; }
            QProgressBar {
                background: #0f141b;
                border: 1px solid #2a3442;
                border-radius: 5px;
                height: 8px;
            }
            QProgressBar::chunk {
                background: #58c4dd;
                border-radius: 5px;
            }
            """
        )

    def set_status(self, text: str) -> None:
        self.status.setText(text)
