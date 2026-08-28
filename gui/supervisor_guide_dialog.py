from __future__ import annotations

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from core.supervisor_guide_service import SupervisorGuideService
from gui.dialog_chrome import apply_team_dialog_chrome


class SupervisorGuideDialog(QDialog):
    """Small non-modal guide surface for the current Team2050 screen."""

    def __init__(self, service: SupervisorGuideService, screen: str, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.screen = screen
        apply_team_dialog_chrome(self, minimum_width=520)
        self.setWindowTitle("Supervisor Guide")
        self.setModal(False)
        self.resize(620, 270)

        state = self.service.mark_seen(screen)
        self.title_label = QLabel(state["title"])
        self.message_label = QLabel(state["message"])
        self.message_label.setWordWrap(True)
        self.target_label = QLabel(f"\u0426\u0435\u043b\044c: {state['target']}  |  \u0417\043d\0430\043a\u043e\043c\0441\0442\0432\043e: {state['familiarity']}")
        self.result_label = QLabel()
        self.result_label.setWordWrap(True)

        show = QPushButton("\u041f\u043e\043a\u0430\0437\0430\0442\044c")
        show.clicked.connect(self._show)
        do = QPushButton("\u0421\0434\0435\u043b\0430\0442\044c \u0437\0430 \u043c\0435\u043d\044f")
        do.clicked.connect(self._do)
        close = QPushButton("\u0417\u0430\u043a\u0440\044b\0442\044c")
        close.clicked.connect(self.close)
        buttons = QHBoxLayout()
        buttons.addWidget(show)
        buttons.addWidget(do)
        buttons.addStretch(1)
        buttons.addWidget(close)
        layout = QVBoxLayout(self)
        layout.addWidget(self.title_label)
        layout.addWidget(self.message_label)
        layout.addWidget(self.target_label)
        layout.addWidget(self.result_label)
        layout.addStretch(1)
        layout.addLayout(buttons)

    def _show(self) -> None:
        state = self.service.show(self.screen)
        if self.parent() is not None and hasattr(self.parent(), "highlight_guide_target"):
            self.parent().highlight_guide_target(state["target"])
        self.result_label.setText("\u041d\u0430\u0432\u0435\u0434\0435\u043d\u0430 \u043d\u0430 \u043d\0443\u0436\043d\044b\0439 \u044d\043b\0435\u043c\0435\u043d\0442. \u041e\043a\043d\043e \u043d\0435 \u0431\u043b\u043e\u043a\0438\u0440\0443\u0435\u0442 \u0440\0430\u0431\u043e\u0442\u0443.")

    def _do(self) -> None:
        state = self.service.do(self.screen)
        self.result_label.setText(
            "\u0412\044b\043f\043e\043b\043d\0435\043d\043e."
            if state.get("ok")
            else "\u041d\0435 \u0443\0434\0430\043b\043e\0441\044c \u0432\044b\043f\043e\043b\043d\0438\0442\044c: " + str(state.get("error", "unknown"))
        )
