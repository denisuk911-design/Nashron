from __future__ import annotations

from .database import Database
from .management_models import ROLE_DEFAULT_PERMISSIONS


LOCAL_TOOL_PERMISSIONS = {
    "WRITE_WORKSPACE",
    "CREATE_DOCUMENTS",
    "RUN_COMMANDS",
}


def effective_permissions_for_agent(database: Database, agent_id: str) -> set[str]:
    roles = database.list_agent_roles(agent_id)
    inherited: set[str] = set()
    for role_id in roles:
        inherited.update(ROLE_DEFAULT_PERMISSIONS.get(role_id, set()))
    grants = set(database.list_agent_permissions(agent_id))
    denies = set(database.list_agent_permission_denies(agent_id))
    return (inherited | grants) - denies


def agent_can_use_local_tools(database: Database, agent_id: str, global_enabled: bool) -> bool:
    if not global_enabled:
        return False
    return bool(effective_permissions_for_agent(database, agent_id) & LOCAL_TOOL_PERMISSIONS)
