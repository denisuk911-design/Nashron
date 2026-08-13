from __future__ import annotations

from pathlib import Path

from .models import ActionRisk


OWNER_APPROVAL_RISKS = {
    ActionRisk.INSTALL,
    ActionRisk.DELETE,
    ActionRisk.PUBLISH,
    ActionRisk.EXTERNAL_SIDE_EFFECT,
}


class WorkspacePolicy:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()

    def task_root(self, organization_id: str, project_id: str, task_id: str) -> Path:
        for value in (organization_id, project_id, task_id):
            if not value or any(char in value for char in "\\/:*?\"<>|"):
                raise ValueError("invalid_workspace_identifier")
        return self.root / "organizations" / organization_id / "projects" / project_id / "tasks" / task_id

    def resolve_in_task(self, organization_id: str, project_id: str, task_id: str, relative_path: str) -> Path:
        task_root = self.task_root(organization_id, project_id, task_id).resolve()
        candidate = (task_root / relative_path).resolve()
        if candidate != task_root and task_root not in candidate.parents:
            raise PermissionError("workspace_scope_violation")
        return candidate

    @staticmethod
    def requires_owner_approval(risk: ActionRisk) -> bool:
        return risk in OWNER_APPROVAL_RISKS
