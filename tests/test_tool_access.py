from core.config_repository import ConfigurationRepository
from core.database import Database
from core.management_models import AgentProfile
from core.management_service import ManagementService
from core.tool_access import agent_can_use_local_tools, effective_permissions_for_agent


def make_service(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    service = ManagementService(db, ConfigurationRepository(tmp_path / "management"))
    service.ensure_foundations()
    return db, service


def test_custom_employee_gets_practical_file_tools_from_role(tmp_path):
    db, service = make_service(tmp_path)
    service.create_agent(
        AgentProfile(
            agent_id="agent-custom",
            display_name="Custom",
            description="custom employee",
            lifecycle_state="ACTIVE",
            provider_id="CODEX_CLI",
        ),
        ["CUSTOM_ROLE"],
        ["CHAT"],
        reason="test",
    )

    permissions = effective_permissions_for_agent(db, "agent-custom")

    assert {"READ_WORKSPACE", "WRITE_WORKSPACE", "CREATE_DOCUMENTS", "RUN_COMMANDS"} <= permissions
    assert agent_can_use_local_tools(db, "agent-custom", global_enabled=True)


def test_document_control_employee_can_create_files_and_run_helpers(tmp_path):
    db, service = make_service(tmp_path)
    service.create_agent(
        AgentProfile(
            agent_id="agent-doc",
            display_name="Docs",
            description="documents",
            lifecycle_state="ACTIVE",
            provider_id="GEMINI_CLI",
        ),
        ["DOCUMENT_CONTROL_OFFICER"],
        ["CHAT"],
        reason="test",
    )

    permissions = effective_permissions_for_agent(db, "agent-doc")

    assert {"WRITE_WORKSPACE", "CREATE_DOCUMENTS", "RUN_COMMANDS"} <= permissions
    assert agent_can_use_local_tools(db, "agent-doc", global_enabled=True)


def test_explicit_denies_disable_local_tools_for_employee(tmp_path):
    db, service = make_service(tmp_path)
    service.create_agent(
        AgentProfile(
            agent_id="agent-limited",
            display_name="Limited",
            description="limited employee",
            lifecycle_state="ACTIVE",
            provider_id="CODEX_CLI",
        ),
        ["CUSTOM_ROLE"],
        ["CHAT"],
        reason="test",
    )
    db.replace_agent_permission_overrides(
        "agent-limited",
        grants=["CHAT"],
        denies=["WRITE_WORKSPACE", "CREATE_DOCUMENTS", "RUN_COMMANDS"],
        actor="ORGANIZATION_OWNER",
        reason="test",
    )

    assert not agent_can_use_local_tools(db, "agent-limited", global_enabled=True)


def test_global_tool_switch_still_disables_cli_tools(tmp_path):
    db, _service = make_service(tmp_path)

    assert not agent_can_use_local_tools(db, "agent-roman", global_enabled=False)
