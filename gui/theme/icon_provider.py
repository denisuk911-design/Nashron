from __future__ import annotations

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QStyle


class IconProvider:
    """Uses the platform icon set for utility actions when a glyph is not enough."""

    @staticmethod
    def standard(kind: QStyle.StandardPixmap) -> QIcon:
        app = QApplication.instance()
        if app is None:
            return QIcon()
        return app.style().standardIcon(kind)
