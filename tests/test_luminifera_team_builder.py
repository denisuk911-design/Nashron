from __future__ import annotations

from types import SimpleNamespace

import pytest

from ui_luminifera.team import TeamBuilderDialog


def test_team_builder_shows_editable_professional_proposal():
    widgets = pytest.importorskip("PySide6.QtWidgets")
    app = widgets.QApplication.instance() or widgets.QApplication([])
    template = SimpleNamespace(
        name="ENGINEERING_PRODUCT_TEAM",
        template_id="engineering-product",
        roles=[
            {"position": "DESIGN_ENGINEER", "responsibility": "Проектирует решение"},
            {"position": "QA_ENGINEER", "responsibility": "Проверяет результат"},
        ],
    )

    class Service:
        def list_templates(self):
            return [template]

        def _select_template_for_brief(self, _brief, _templates):
            return template

        def build_professional_team(self, brief, name, *, template_id):
            return SimpleNamespace(brief=brief, name=name, template_id=template_id)

    dialog = TeamBuilderDialog(Service())
    dialog.brief.setPlainText("Создать инженерный продукт")
    dialog._propose_clicked(dialog.propose.button(widgets.QDialogButtonBox.Apply))
    assert dialog.roster.count() == 2
    assert not dialog.actions.isHidden()
    dialog.name.setText("Инженерная команда")
    dialog._create()
    assert dialog.build.template_id == "engineering-product"
    dialog.close()
