from __future__ import annotations

import json

from core.database import Database
from core.universal_platform_service import UniversalPlatformService


def test_builder_selects_relevant_domain_and_persists_operational_contract(tmp_path):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    service = UniversalPlatformService(database, workspace_root=tmp_path / "workspace")

    result = service.build_professional_team(
        "Спроектировать PCB плату в KiCad, проверить BOM, DRC и подготовить выпуск",
        "PCB проект",
    )

    assert database.get_organization_template(result.template_id)["name"] == "PCB_ENGINEERING_TEAM"
    assert result.selection_mode == "SUPERVISOR_CATALOG_MATCH"
    assert result.activation.employee_ids
    workspace = database.get_organization_workspace(result.organization.organization_id)
    config = json.loads(workspace["routing_config"])
    assert config["builder"] == "PROFESSIONAL_TEAM_BUILDER"
    assert config["roles"]
    assert all(role["skills"] and role["tools"] and role["definition_of_done"] for role in config["roles"])
    assert config["definition_of_done"]


def test_builder_accepts_explicit_template_without_provider_or_manual_roster(tmp_path):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    service = UniversalPlatformService(database)
    service.seed_management_library()
    template = next(item for item in service.list_templates() if item.name == "CULINARY_BRIGADE")

    result = service.build_professional_team(
        "Меню для ресторана",
        "Кулинарная команда",
        template_id=template.template_id,
        team_size="STANDARD",
    )

    assert result.selection_mode == "EXPLICIT_TEMPLATE"
    assert result.activation.status == "READY_WITH_UNASSIGNED"
    assert len(database.list_organization_members(result.organization.organization_id)) >= 3
