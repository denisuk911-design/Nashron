from __future__ import annotations

import pytest

from core.agent_directory import ChatAgent
from ui_luminifera.team import TeamDashboard


def test_team_dashboard_renders_roster_and_localizes_heading():
    widgets = pytest.importorskip("PySide6.QtWidgets")
    app = widgets.QApplication.instance() or widgets.QApplication([])
    dashboard = TeamDashboard("ru")
    agent = ChatAgent(
        key="roman", agent_id="agent-roman", display_name="Роман", provider_id="CODEX_CLI",
        roles=["DESIGN_ENGINEER"], persona_id=None, description="Проектирует решение", avatar_path=None,
    )
    dashboard.render((agent,))
    assert dashboard.heading.text() == "Команда"
    assert dashboard.list.count() == 1
    card = dashboard.list.itemWidget(dashboard.list.item(0))
    assert card is not None
    dashboard.set_language("en")
    assert dashboard.heading.text() == "Team"
    dashboard.close()
