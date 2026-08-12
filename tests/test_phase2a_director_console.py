import pytest

from core.config_repository import ConfigurationRepository
from core.database import Database
from core.management_models import AgentProfile, OWNER_ROLE
from core.management_service import ManagementService


class MissingProvider:
    def is_available(self):
        return False


def make_service(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    service = ManagementService(db, ConfigurationRepository(tmp_path / "management"))
    service.ensure_foundations()
    fixtures = (
        ("agent-designer-fixture", "Design Fixture", "DESIGN_ENGINEER", "CODEX_CLI"),
        ("agent-reviewer-fixture", "Review Fixture", "QA_ENGINEER", "GEMINI_CLI"),
    )
    for agent_id, display_name, role_id, provider_id in fixtures:
        service.create_agent(
            AgentProfile(agent_id, display_name, "Test employee", "ACTIVE", provider_id),
            [role_id],
            ["CHAT"],
            reason="test fixture",
        )
    return db, service


def test_employee_list_contains_explicit_fixtures_with_stable_ids(tmp_path):
    _db, service = make_service(tmp_path)

    employees = {employee.agent_id: employee for employee in service.list_employees()}

    assert "agent-designer-fixture" in employees
    assert "agent-reviewer-fixture" in employees
    assert employees["agent-designer-fixture"].provider_id == "CODEX_CLI"
    assert employees["agent-reviewer-fixture"].provider_id == "GEMINI_CLI"


def test_archived_filter_works(tmp_path):
    _db, service = make_service(tmp_path)
    service.database.set_agent_lifecycle("agent-designer-fixture", "DISABLED", OWNER_ROLE, "prepare archive")
    service.archive_agent("agent-designer-fixture", OWNER_ROLE, "test archive")

    archived = service.list_employees("ARCHIVED")

    assert [employee.agent_id for employee in archived] == ["agent-designer-fixture"]


def test_valid_draft_employee_creation_and_audit(tmp_path):
    db, service = make_service(tmp_path)
    profile = AgentProfile(
        agent_id=service.generate_agent_id("Delovod"),
        display_name="Delovod",
        description="Document control",
        lifecycle_state="DRAFT",
        provider_id="CODEX_CLI",
        persona_id="document_control",
    )

    preview = service.create_agent(profile, ["DOCUMENT_CONTROL_OFFICER"], ["READ_WORKSPACE"], reason="phase2a test")

    assert preview.ok
    assert db.get_agent_profile(profile.agent_id) is not None
    assert any(row["object_id"] == profile.agent_id for row in db.list_management_audit_events())


def test_duplicate_display_name_is_warning_not_blocking_for_draft(tmp_path):
    _db, service = make_service(tmp_path)
    profile = AgentProfile(
        agent_id=service.generate_agent_id("Roman"),
        display_name="Roman",
        description="Duplicate readable name",
        lifecycle_state="DRAFT",
        provider_id="CODEX_CLI",
    )

    preview = service.preview_create_agent(profile, ["PROJECT_MANAGER"], ["CHAT"])

    assert preview.ok


def test_provider_status_reports_executable_missing(tmp_path):
    _db, service = make_service(tmp_path)

    assert service.provider_status("CODEX_CLI", {"CODEX_CLI": MissingProvider()}) == "EXECUTABLE_NOT_FOUND"


def test_edit_display_name_preserves_stable_id(tmp_path):
    db, service = make_service(tmp_path)
    before = db.get_agent_profile("agent-designer-fixture")

    service.update_employee(
        "agent-designer-fixture",
        display_name="Designer Updated",
        description="same id",
        provider_id="CODEX_CLI",
        persona_id="neutral_engineer",
        roles=["DESIGN_ENGINEER"],
        permission_grants=["CHAT"],
        permission_denies=[],
        expected_updated_at=before["updated_at"],
        reason="rename",
    )

    after = db.get_agent_profile("agent-designer-fixture")
    assert after["agent_id"] == "agent-designer-fixture"
    assert after["display_name"] == "Designer Updated"


def test_optimistic_lock_conflict_detected(tmp_path):
    _db, service = make_service(tmp_path)

    with pytest.raises(RuntimeError):
        service.update_employee(
            "agent-designer-fixture",
            display_name="Conflict",
            description="bad timestamp",
            provider_id="CODEX_CLI",
            persona_id="neutral_engineer",
            roles=["DESIGN_ENGINEER"],
            permission_grants=["CHAT"],
            permission_denies=[],
            expected_updated_at="old",
            reason="conflict",
        )


def test_inherited_and_direct_deny_permission_precedence(tmp_path):
    _db, service = make_service(tmp_path)
    effective = service.effective_permissions(["DESIGN_ENGINEER"], ["DELETE_FILES"], ["RUN_COMMANDS"])

    assert "WRITE_WORKSPACE" in effective
    assert "DELETE_FILES" in effective
    assert "RUN_COMMANDS" not in effective


def test_blocking_conflict_prevents_activation(tmp_path):
    _db, service = make_service(tmp_path)
    profile = AgentProfile(
        agent_id="agent-conflict-phase2a",
        display_name="Conflict",
        description="author and qa",
        lifecycle_state="DRAFT",
        provider_id="CODEX_CLI",
    )

    preview = service.preview_create_agent(profile, ["DESIGN_ENGINEER", "QA_ENGINEER"], ["CHAT"])

    assert not preview.ok
    assert "unsafe_role_conflict:author_and_independent_reviewer" in preview.errors


def test_lifecycle_invalid_transition_rejected(tmp_path):
    _db, service = make_service(tmp_path)

    service.archive_agent("agent-designer-fixture", OWNER_ROLE, "archive from the employee console")
    assert _db.get_agent_profile("agent-designer-fixture")["lifecycle_state"] == "ARCHIVED"


def test_draft_employee_can_be_deleted_permanently(tmp_path):
    db, service = make_service(tmp_path)
    profile = AgentProfile(
        agent_id=service.generate_agent_id("Temporary"),
        display_name="Temporary",
        description="No history",
        lifecycle_state="DRAFT",
        provider_id="CODEX_CLI",
    )
    service.create_agent(profile, ["DOCUMENT_CONTROL_OFFICER"], ["CHAT"], reason="delete test")

    service.delete_agent(profile.agent_id, OWNER_ROLE, confirmed=True)

    assert db.get_agent_profile(profile.agent_id) is None
    assert any(
        row["object_id"] == profile.agent_id and row["action"] == "delete"
        for row in db.list_management_audit_events()
    )


def test_active_employee_without_history_can_be_deleted_permanently(tmp_path):
    db, service = make_service(tmp_path)
    profile = AgentProfile(
        agent_id=service.generate_agent_id("Active temporary"),
        display_name="Active temporary",
        description="No history",
        lifecycle_state="ACTIVE",
        provider_id="CODEX_CLI",
    )
    service.create_agent(profile, ["DOCUMENT_CONTROL_OFFICER"], ["CHAT"], reason="delete test")

    service.delete_agent(profile.agent_id, OWNER_ROLE, confirmed=True)

    assert db.get_agent_profile(profile.agent_id) is None
