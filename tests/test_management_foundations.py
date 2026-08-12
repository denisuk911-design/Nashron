import pytest

from core.config_repository import ConfigurationRepository
from core.agent_router import AgentRouter
from core.database import Database
from core.management_models import AgentProfile, OWNER_ROLE
from core.management_service import ManagementService


def make_service(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    repository = ConfigurationRepository(tmp_path / "management")
    service = ManagementService(db, repository)
    service.ensure_foundations()
    return db, service


def test_management_foundations_do_not_seed_demo_agents(tmp_path):
    db, _service = make_service(tmp_path)

    assert db.list_agent_profiles() == []


def test_duplicate_employee_id_rejected(tmp_path):
    _db, service = make_service(tmp_path)
    existing = AgentProfile(
        agent_id="agent-existing",
        display_name="Existing",
        description="Existing employee",
        lifecycle_state="DRAFT",
        provider_id="CODEX_CLI",
    )
    service.create_agent(existing, ["CUSTOM_ROLE"], ["CHAT"])
    profile = AgentProfile(
        agent_id="agent-existing",
        display_name="Duplicate",
        description="Should fail",
        lifecycle_state="ACTIVE",
        provider_id="CODEX_CLI",
    )

    preview = service.preview_create_agent(profile, ["DESIGN_ENGINEER"], ["CHAT"])

    assert not preview.ok
    assert "duplicate_agent_id" in preview.errors


def test_unavailable_active_provider_rejected(tmp_path):
    _db, service = make_service(tmp_path)
    profile = AgentProfile(
        agent_id="agent-new",
        display_name="New",
        description="Unavailable provider",
        lifecycle_state="ACTIVE",
        provider_id="UNAVAILABLE",
    )

    preview = service.preview_create_agent(profile, ["PROJECT_MANAGER"], ["CHAT"])

    assert not preview.ok
    assert "active_employee_requires_available_provider" in preview.errors


def test_unsafe_author_and_qa_role_conflict_detected(tmp_path):
    _db, service = make_service(tmp_path)
    profile = AgentProfile(
        agent_id="agent-conflict",
        display_name="Conflict",
        description="Bad role mix",
        lifecycle_state="DRAFT",
        provider_id="CODEX_CLI",
    )

    preview = service.preview_create_agent(profile, ["DESIGN_ENGINEER", "QA_ENGINEER"], ["CHAT"])

    assert not preview.ok
    assert "unsafe_role_conflict:author_and_independent_reviewer" in preview.errors


def test_unauthorized_agent_cannot_manage_employees(tmp_path):
    _db, service = make_service(tmp_path)
    profile = AgentProfile(
        agent_id="agent-managed",
        display_name="Managed",
        description="No owner",
        lifecycle_state="DRAFT",
        provider_id="CODEX_CLI",
    )

    preview = service.preview_create_agent(profile, ["PROJECT_MANAGER"], ["MANAGE_EMPLOYEES"], actor_role="DESIGN_ENGINEER")

    assert not preview.ok
    assert "owner_authority_required" in preview.errors


def test_dry_run_makes_no_persistent_changes(tmp_path):
    db, service = make_service(tmp_path)
    profile = AgentProfile(
        agent_id="agent-dry-run",
        display_name="Dry Run",
        description="No write",
        lifecycle_state="DRAFT",
        provider_id="CODEX_CLI",
    )

    preview = service.create_agent(profile, ["PROJECT_MANAGER"], ["CHAT"], dry_run=True)

    assert preview.ok
    assert db.get_agent_profile("agent-dry-run") is None


def test_create_employee_writes_audit_and_profile_file(tmp_path):
    db, service = make_service(tmp_path)
    profile = AgentProfile(
        agent_id="agent-doc",
        display_name="Document Officer",
        description="Document control foundation",
        lifecycle_state="DRAFT",
        provider_id="CODEX_CLI",
    )

    preview = service.create_agent(profile, ["DOCUMENT_CONTROL_OFFICER"], ["CHAT", "READ_WORKSPACE"], reason="test")

    assert preview.ok
    assert db.get_agent_profile("agent-doc") is not None
    assert (tmp_path / "management" / "employees" / "agent-doc" / "profile.json").exists()
    assert any(row["object_id"] == "agent-doc" for row in db.list_management_audit_events())


def test_create_employee_with_custom_role_is_seeded(tmp_path):
    db, service = make_service(tmp_path)
    profile = AgentProfile(
        agent_id="agent-custom",
        display_name="Custom Employee",
        description="User-defined role",
        lifecycle_state="DRAFT",
        provider_id="CODEX_CLI",
    )

    preview = service.create_agent(profile, ["CUSTOM_ROLE"], ["CHAT"], reason="test")

    assert preview.ok
    assert db.get_agent_profile("agent-custom") is not None
    assert "CUSTOM_ROLE" in db.list_agent_roles("agent-custom")
    employee = service.get_employee("agent-custom")
    assert employee is not None
    assert {"READ_WORKSPACE", "WRITE_WORKSPACE", "CREATE_DOCUMENTS", "RUN_COMMANDS"} <= set(employee.effective_permissions)


def test_agent_router_uses_created_employee_profile(tmp_path):
    db, service = make_service(tmp_path)
    profile = AgentProfile(
        agent_id="agent-shushan",
        display_name="Шушан",
        description="Document control",
        lifecycle_state="ACTIVE",
        provider_id="GEMINI_CLI",
        persona_id="document_control",
    )
    service.create_agent(profile, ["DOCUMENT_CONTROL_OFFICER"], ["CHAT"], reason="test")

    route = AgentRouter(db).route("shushan")

    assert route.agent_id == "agent-shushan"
    assert route.role == "DOCUMENT_CONTROL_OFFICER"
    assert route.provider == "GEMINI_CLI"


def test_owner_can_suspend_and_reactivate_employee(tmp_path):
    db, service = make_service(tmp_path)
    profile = AgentProfile(
        agent_id="agent-lifecycle",
        display_name="Lifecycle Employee",
        description="Lifecycle fixture",
        lifecycle_state="ACTIVE",
        provider_id="CODEX_CLI",
    )
    service.create_agent(profile, ["CUSTOM_ROLE"], ["CHAT"])

    service.suspend_agent("agent-lifecycle", OWNER_ROLE, "pause")
    assert db.get_agent_profile("agent-lifecycle")["lifecycle_state"] == "SUSPENDED"

    service.reactivate_agent("agent-lifecycle", OWNER_ROLE, "return")
    assert db.get_agent_profile("agent-lifecycle")["lifecycle_state"] == "ACTIVE"


def test_configuration_repository_rejects_path_traversal(tmp_path):
    repository = ConfigurationRepository(tmp_path / "management")

    with pytest.raises(ValueError):
        repository.write_json_atomic("../escape.json", {"bad": True}, dry_run=True)
