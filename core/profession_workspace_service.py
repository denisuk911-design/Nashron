from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .database import Database
from .skill_marketplace_service import SkillMarketplaceService
from .skill_package_service import SkillPackageService


@dataclass(frozen=True)
class ProfessionWorkspace:
    organization_id: str
    agent_id: str
    profession_id: str
    profession_name: str
    root: Path
    skills: tuple[str, ...]
    tools: tuple[str, ...]
    policies: tuple[str, ...]
    definition_of_done: tuple[str, ...]


class ProfessionWorkspaceService:
    """Projects a bounded work environment from persisted profession contracts."""

    def __init__(self, database: Database, workspace_root: Path) -> None:
        self.database = database
        self.workspace_root = Path(workspace_root)
        self.marketplace = SkillMarketplaceService(SkillPackageService(database))

    def for_employee(self, organization_id: str, agent_id: str) -> ProfessionWorkspace:
        with self.database.connect() as conn:
            row = conn.execute(
                """SELECT p.* FROM organization_members m JOIN professions p ON p.id=m.profession_id
                   WHERE m.organization_id=? AND m.agent_id=? AND m.status='ACTIVE'""",
                (organization_id, agent_id),
            ).fetchone()
        if row is None:
            raise ValueError("active profession membership is required")
        packages = SkillPackageService(self.database)
        skills = [item for item in packages.list_assignments(agent_id)
                  if item.state == "QUALIFIED" and item.skill_status == "ACTIVE"]
        relevant = skills
        skill_names = tuple(item.skill_name for item in relevant)
        skill_dod: list[str] = []
        for item in relevant:
            skill_dod.extend(self.marketplace.definition_of_done(item.skill_id, organization_id))
        root = self.workspace_root / organization_id / "professions" / str(row["id"])
        root.mkdir(parents=True, exist_ok=True)
        tools = tuple(Database.loads(str(row["recommended_tools"]), []))
        return ProfessionWorkspace(
            organization_id, agent_id, str(row["id"]), str(row["name"]), root, skill_names, tools,
            ("workspace_scoped", "profession_tools_only", "evidence_required"),
            tuple(dict.fromkeys([*Database.loads(str(row["typical_results"]), []), *skill_dod])),
        )
