from __future__ import annotations

import pytest

from core.agent_directory import ChatAgent
from ui_luminifera.team import TeamDashboard


def test_team_dashboard_renders_roster_and_localizes_heading():
    widgets = pytest.importorskip("PySide6.QtWidgets")
    app = widgets.QApplication.instance() or widgets.QApplication([])
    dashboard = TeamDashboard("ru")
    assert dashboard.create_button.text() == "Собрать команду"
    agent = ChatAgent(
        key="roman", agent_id="agent-roman", display_name="Роман", provider_id="CODEX_CLI",
        roles=["DESIGN_ENGINEER"], persona_id=None, description="Проектирует решение", avatar_path=None,
        skills=("BOM audit", "ERC review"),
    )
    dashboard.render((agent,))
    assert dashboard.heading.text() == "Команда"
    assert dashboard.list.count() == 1
    card = dashboard.list.itemWidget(dashboard.list.item(0))
    assert card is not None
    assert any("BOM audit" in label.text() for label in card.findChildren(widgets.QLabel))
    dashboard.set_language("en")
    assert dashboard.heading.text() == "Team"
    assert dashboard.create_button.text() == "Build a team"
    dashboard.close()
