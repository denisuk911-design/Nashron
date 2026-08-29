from __future__ import annotations

import pytest

from core.luminifera_work_service import WorkArtifact, WorkSnapshot
from ui_luminifera.work import WorkDashboard


def test_work_state_is_shown_in_user_language():
    widgets = pytest.importorskip("PySide6.QtWidgets")
    app = widgets.QApplication.instance() or widgets.QApplication([])
    dashboard = WorkDashboard("ru")
    dashboard.render(WorkSnapshot(goal_title="Плата", goal_state="IN_PROGRESS", goal_progress=50))
    assert dashboard.goal_status.text() == "Статус: В работе"
    dashboard.close()


def test_work_view_marks_receipt_only_when_evidence_is_ready():
    widgets = pytest.importorskip("PySide6.QtWidgets")
    app = widgets.QApplication.instance() or widgets.QApplication([])
    dashboard = WorkDashboard("en")
    dashboard.render(
        WorkSnapshot(
            goal_title="Brief",
            receipt_ready=True,
            evidence_count=2,
            artifacts=(WorkArtifact("brief.md", "verified"),),
        )
    )
    assert "2" in dashboard.result_body.text()
    assert "1" in dashboard.result_body.text()
    dashboard.close()


def test_work_product_view_does_not_expose_runtime_enum_states():
    widgets = pytest.importorskip("PySide6.QtWidgets")
    app = widgets.QApplication.instance() or widgets.QApplication([])
    dashboard = WorkDashboard("en")
    dashboard.render(WorkSnapshot(goal_title="Brief", goal_state="RUNNING"))
    assert "RUNNING" not in dashboard.goal_status.text()
    dashboard.close()
