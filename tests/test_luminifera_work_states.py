from __future__ import annotations

import pytest

from core.luminifera_work_service import WorkSnapshot
from ui_luminifera.work import WorkDashboard


def test_work_state_is_shown_in_user_language():
    widgets = pytest.importorskip("PySide6.QtWidgets")
    app = widgets.QApplication.instance() or widgets.QApplication([])
    dashboard = WorkDashboard("ru")
    dashboard.render(WorkSnapshot(goal_title="Плата", goal_state="IN_PROGRESS", goal_progress=50))
    assert dashboard.goal_status.text() == "Статус: В работе"
    dashboard.close()
