from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog


def apply_team_dialog_chrome(dialog: QDialog, *, minimum_width: int = 460) -> None:
    """Apply the shared Team2050 window contract without replacing OS controls."""
    dialog.setObjectName("teamDialog")
    dialog.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
    dialog.setMinimumWidth(minimum_width)
    dialog.setModal(True)
