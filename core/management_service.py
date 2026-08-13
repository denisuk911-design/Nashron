from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Protocol

from .config_repository import ConfigurationRepository
from .database import Database
from .management_models import (
    AGENT_LIFECYCLE_STATES,
    LIFECYCLE_TRANSITIONS,
    OWNER_ONLY_PERMISSIONS,
    OWNER_ROLE,
    PERMISSIONS,
    PROVIDER_IDS,
    RISKY_PERMISSIONS,
    ROLE_IDS,
    ROLE_DEFAULT_PERMISSIONS,
    ROLE_TEMPLATES,
    AgentProfile,
)


@dataclass(frozen=True)
class ManagementPreview:
    ok: bool
    action: str
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    database_rows: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EmployeeSummary:
    agent_id: str
    display_name: str
    lifecycle_state: str
    provider_id: str
    persona_id: str | None
    roles: list[str]
    direct_permissions: list[str]
    permission_denies: list[str]
    effective_permissions: list[str]
    availability: str
    warnings: list[str]
    updated_at: str


class ProviderChecker(Protocol):
    def is_available(self) -> bool:
        ...


class ManagementService:
    def __init__(self, database: Database, config_repository: ConfigurationRepository) -> None:
        self.database = database
        self.config_repository = config_repository

    def ensure_foundations(self) -> None:
        """Install shared role templates without creating employees."""
        for role in ROLE_TEMPLATES:
            self.database.upsert_role_profile(role)

    def legacy_seed_agents(self) -> list[EmployeeSummary]:
        """Return old demo profiles for an explicit user cleanup flow only."""
        legacy_ids = {"agent-roman", "agent-petr", "agent-shushanna"}
        legacy_personas = {"roman_2050", "petr_2050", "shushanna_2050"}
        result: list[EmployeeSummary] = []
        for row in self.database.list_agent_profiles():
            if str(row["agent_id"]) in legacy_ids or str(row["persona_id"] or "") in legacy_personas:
                result.append(self._summary_from_row(row))
        return result

    def cleanup_legacy_seed_agents(self, action: str, actor_role: str = OWNER_ROLE) -> list[str]:
        """Archive or permanently remove legacy demo profiles explicitly."""
        action = str(action or "").upper()
        agents = self.legacy_seed_agents()
        if action not in {"ARCHIVE", "DELETE"}:
            raise ValueError("legacy_cleanup_action_required")
        for employee in agents:
            if action == "ARCHIVE":
                self.archive_agent(employee.agent_id, actor_role, "Legacy demo cleanup")
            else:
                self.delete_agent(employee.agent_id, actor_role, confirmed=True)
        return [employee.agent_id for employee in agents]

    @staticmethod
    def generate_agent_id(display_name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", display_name.lower()).strip("-")
        if not slug:
            slug = "employee"
        return f"agent-{slug[:24]}-{uuid.uuid4().hex[:6]}"

    def list_employees(self, status: str | None = None) -> list[EmployeeSummary]:
        employees = [self._summary_from_row(row) for row in self.database.list_agent_profiles()]
        if status and status != "ALL":
            employees = [employee for employee in employees if employee.lifecycle_state == status]
        return employees

    def get_employee(self, agent_id: str) -> EmployeeSummary | None:
        row = self.database.get_agent_profile(agent_id)
        if row is None:
            return None
        return self._summary_from_row(row)

    def list_roles(self):
        return self.database.list_role_profiles()

    def list_audit_events(self):
        return self.database.list_management_audit_events()

    def provider_status(self, provider_id: str, provider_checkers: dict[str, ProviderChecker] | None = None) -> str:
        if provider_id == "UNAVAILABLE":
            return "NOT_CONFIGURED"
        if provider_id == "FUTURE_PROVIDER":
            return "NOT_CONFIGURED"
        checker = (provider_checkers or {}).get(provider_id)
        if checker is None:
            return "UNKNOWN"
        try:
            return "AVAILABLE" if checker.is_available() else "EXECUTABLE_NOT_FOUND"
        except Exception:
            return "UNKNOWN"

    def inherited_permissions(self, role_ids: list[str]) -> set[str]:
        permissions: set[str] = set()
        for role_id in role_ids:
            permissions.update(ROLE_DEFAULT_PERMISSIONS.get(role_id, set()))
        return permissions

    def effective_permissions(self, role_ids: list[str], grants: list[str], denies: list[str]) -> set[str]:
        return (self.inherited_permissions(role_ids) | set(grants)) - set(denies)

    def configuration_warnings(
        self,
        role_ids: list[str],
        provider_id: str,
        lifecycle_state: str,
        effective_permissions: set[str],
        provider_status: str = "UNKNOWN",
    ) -> list[str]:
        warnings: list[str] = []
        if "DESIGN_ENGINEER" in role_ids and "QA_ENGINEER" in role_ids:
            warnings.append("BLOCKING: author_and_independent_reviewer")
        if "DOCUMENT_CONTROL_OFFICER" in role_ids and "DELETE_FILES" in effective_permissions:
            warnings.append("HIGH_RISK: document_control_with_delete_files")
        if "LEARNING_COORDINATOR" in role_ids and "GRANT_APPROVAL" in effective_permissions:
            warnings.append("BLOCKING: learning_coordinator_with_approval")
        if "QA_ENGINEER" in role_ids and {"WRITE_WORKSPACE", "MODIFY_PROJECT"} <= effective_permissions:
            warnings.append("HIGH_RISK: qa_with_silent_project_modification")
        if lifecycle_state == "ACTIVE" and provider_status not in ("AVAILABLE", "UNKNOWN"):
            warnings.append("BLOCKING: active_employee_provider_unavailable")
        if OWNER_ONLY_PERMISSIONS & effective_permissions:
            warnings.append("BLOCKING: owner_only_permission_on_employee")
        if "ACCESS_EXTERNAL_PATHS" in effective_permissions:
            warnings.append("HIGH_RISK: external_path_access")
        if RISKY_PERMISSIONS & effective_permissions:
            warnings.append("WARNING: risky_permissions_present")
        return warnings

    def preview_create_agent(
        self,
        profile: AgentProfile,
        role_ids: list[str],
        permissions: list[str],
        actor_role: str = OWNER_ROLE,
    ) -> ManagementPreview:
        errors = self._validate_profile(profile, role_ids, permissions, actor_role)
        warnings = []
        if any(
            employee.display_name.strip().lower() == profile.display_name.strip().lower()
            for employee in self.list_employees()
        ):
            warnings.append("WARNING: duplicate_display_name")
        rows = [f"agent_profiles:{profile.agent_id}"]
        rows.extend(f"agent_role_assignments:{profile.agent_id}:{role_id}" for role_id in role_ids)
        rows.extend(f"agent_permissions:{profile.agent_id}:{permission}" for permission in permissions)
        files = [f"employees/{profile.agent_id}/profile.json"]
        return ManagementPreview(not errors, "create_agent", warnings=warnings, errors=errors, database_rows=rows, files=files)

    def create_agent(
        self,
        profile: AgentProfile,
        role_ids: list[str],
        permissions: list[str],
        actor_role: str = OWNER_ROLE,
        reason: str = "",
        dry_run: bool = False,
    ) -> ManagementPreview:
        preview = self.preview_create_agent(profile, role_ids, permissions, actor_role)
        if dry_run or not preview.ok:
            return preview
        profile_path = f"employees/{profile.agent_id}/profile.json"
        payload = self._profile_payload(profile, role_ids, permissions, [])
        self.config_repository.write_json_atomic(profile_path, payload)
        try:
            self.database.create_agent_profile_with_assignments(profile, role_ids, permissions, actor_role, reason)
        except Exception:
            try:
                self.config_repository.resolve(profile_path).unlink(missing_ok=True)
            except OSError:
                pass
            raise
        return preview

    def update_employee(
        self,
        agent_id: str,
        *,
        display_name: str,
        description: str,
        provider_id: str,
        persona_id: str | None,
        roles: list[str],
        permission_grants: list[str],
        permission_denies: list[str],
        expected_updated_at: str | None,
        avatar_path: str | None = None,
        preferred_name: str | None = None,
        informal_name: str | None = None,
        communication_profile: dict[str, object] | None = None,
        actor_role: str = OWNER_ROLE,
        reason: str = "",
        dry_run: bool = False,
    ) -> ManagementPreview:
        self._require_owner(actor_role)
        current = self.database.get_agent_profile(agent_id)
        if current is None:
            return ManagementPreview(False, "edit_agent", errors=["unknown_agent_id"])
        errors = self._validate_common(
            agent_id=agent_id,
            lifecycle_state=str(current["lifecycle_state"]),
            provider_id=provider_id,
            role_ids=roles,
            permissions=permission_grants,
            denies=permission_denies,
            actor_role=actor_role,
            allow_existing_agent=True,
        )
        preview = ManagementPreview(
            not errors,
            "edit_agent",
            errors=errors,
            database_rows=[f"agent_profiles:{agent_id}", f"agent_role_assignments:{agent_id}", f"agent_permissions:{agent_id}"],
            files=[f"employees/{agent_id}/profile.json"],
        )
        if dry_run or not preview.ok:
            return preview
        old_payload = self.config_repository.read_json(f"employees/{agent_id}/profile.json", default=None)
        profile = AgentProfile(
            agent_id=agent_id,
            display_name=display_name,
            description=description,
            lifecycle_state=str(current["lifecycle_state"]),
            provider_id=provider_id,
            persona_id=persona_id,
            avatar_path=avatar_path,
            aliases=self._aliases_from_row(current),
            full_name=display_name,
            preferred_name=(
                str(current["preferred_name"] or "") if preferred_name is None and "preferred_name" in current.keys() else str(preferred_name or "")
            ),
            informal_name=(
                str(current["informal_name"] or "") if informal_name is None and "informal_name" in current.keys() else str(informal_name or "")
            ),
            communication_profile=(
                self._communication_profile_from_row(current) if communication_profile is None else dict(communication_profile)
            ),
        )
        self.config_repository.write_json_atomic(
            f"employees/{agent_id}/profile.json",
            self._profile_payload(profile, roles, permission_grants, permission_denies),
        )
        try:
            self.database.update_agent_profile(
                agent_id,
                display_name=display_name,
                description=description,
                provider_id=provider_id,
                persona_id=persona_id,
                avatar_path=avatar_path,
                expected_updated_at=expected_updated_at,
                actor=actor_role,
                reason=reason,
                aliases=list(profile.aliases),
                full_name=profile.full_name,
                preferred_name=profile.preferred_name,
                informal_name=profile.informal_name,
                communication_profile=profile.communication_profile,
            )
            self.database.replace_agent_roles(agent_id, roles, actor_role, reason)
            self.database.replace_agent_permission_overrides(agent_id, permission_grants, permission_denies, actor_role, reason)
        except Exception:
            if old_payload is None:
                self.config_repository.resolve(f"employees/{agent_id}/profile.json").unlink(missing_ok=True)
            else:
                self.config_repository.write_json_atomic(f"employees/{agent_id}/profile.json", old_payload)
            raise
        return preview

    def suspend_agent(self, agent_id: str, actor_role: str, reason: str) -> None:
        self._require_owner(actor_role)
        self._transition_lifecycle(agent_id, "SUSPENDED")
        self.database.set_agent_lifecycle(agent_id, "SUSPENDED", actor_role, reason)

    def reactivate_agent(self, agent_id: str, actor_role: str, reason: str) -> None:
        self._require_owner(actor_role)
        row = self.database.get_agent_profile(agent_id)
        if row is None:
            raise ValueError(f"Unknown agent profile: {agent_id}")
        current = str(row["lifecycle_state"])
        if current != "ARCHIVED":
            self._transition_lifecycle(agent_id, "ACTIVE")
        employee = self.get_employee(agent_id)
        if employee is None:
            raise ValueError(f"Unknown agent profile: {agent_id}")
        blocking = [warning for warning in employee.warnings if warning.startswith("BLOCKING")]
        if blocking:
            raise ValueError("; ".join(blocking))
        self.database.set_agent_lifecycle(agent_id, "ACTIVE", actor_role, reason)

    def archive_agent(self, agent_id: str, actor_role: str, reason: str) -> None:
        self._require_owner(actor_role)
        row = self.database.get_agent_profile(agent_id)
        if row is None:
            raise ValueError(f"Unknown agent profile: {agent_id}")
        current = str(row["lifecycle_state"])
        if current == "ARCHIVED":
            return
        if current not in {"DRAFT", "DISABLED"}:
            self.database.set_agent_lifecycle(agent_id, "DISABLED", actor_role, reason or "Archive requested")
        self.database.set_agent_lifecycle(agent_id, "ARCHIVED", actor_role, reason or "Archive requested")

    def delete_agent(self, agent_id: str, actor_role: str, confirmed: bool = False) -> None:
        self._require_owner(actor_role)
        if not confirmed:
            raise ValueError("owner_confirmation_required")
        row = self.database.get_agent_profile(agent_id)
        if row is None:
            raise ValueError(f"Unknown agent profile: {agent_id}")
        self.database.delete_agent_profile(agent_id, actor=actor_role, reason="Employee permanently deleted")
        self.config_repository.resolve(f"employees/{agent_id}/profile.json").unlink(missing_ok=True)

    def activate_agent(self, agent_id: str, actor_role: str, reason: str) -> None:
        self._require_owner(actor_role)
        self._transition_lifecycle(agent_id, "ACTIVE")
        employee = self.get_employee(agent_id)
        if employee is None:
            raise ValueError(f"Unknown agent profile: {agent_id}")
        blocking = [warning for warning in employee.warnings if warning.startswith("BLOCKING")]
        if blocking:
            raise ValueError("; ".join(blocking))
        self.database.set_agent_lifecycle(agent_id, "ACTIVE", actor_role, reason)

    def _validate_profile(
        self,
        profile: AgentProfile,
        role_ids: list[str],
        permissions: list[str],
        actor_role: str,
    ) -> list[str]:
        errors = self._validate_common(
            agent_id=profile.agent_id,
            lifecycle_state=profile.lifecycle_state,
            provider_id=profile.provider_id,
            role_ids=role_ids,
            permissions=permissions,
            denies=[],
            actor_role=actor_role,
            allow_existing_agent=False,
        )
        if not profile.display_name.strip():
            errors.append("empty_display_name")
        normalized_name = profile.display_name.strip().casefold()
        role_names = {
            str(row["display_name"] or "").strip().casefold()
            for row in self.database.list_role_profiles()
            if str(row["role_id"]) in role_ids
        }
        if normalized_name in role_names or normalized_name in {role_id.casefold() for role_id in role_ids}:
            errors.append("employee_name_must_be_human_not_role")
        return errors

    def _validate_common(
        self,
        *,
        agent_id: str,
        lifecycle_state: str,
        provider_id: str,
        role_ids: list[str],
        permissions: list[str],
        denies: list[str],
        actor_role: str,
        allow_existing_agent: bool,
    ) -> list[str]:
        errors: list[str] = []
        if actor_role != OWNER_ROLE:
            errors.append("owner_authority_required")
        if not agent_id.startswith("agent-"):
            errors.append("agent_id_must_be_stable_agent_id")
        if not allow_existing_agent and self.database.get_agent_profile(agent_id) is not None:
            errors.append("duplicate_agent_id")
        if lifecycle_state not in AGENT_LIFECYCLE_STATES:
            errors.append("invalid_lifecycle_state")
        configured_provider_ids = {str(row["provider_id"]) for row in self.database.list_provider_definitions()}
        if provider_id not in configured_provider_ids | PROVIDER_IDS:
            errors.append("invalid_provider")
        if provider_id == "UNAVAILABLE" and lifecycle_state == "ACTIVE":
            errors.append("active_employee_requires_available_provider")
        existing_roles = {str(row["role_id"]) for row in self.database.list_role_profiles()}
        for role_id in role_ids:
            if role_id not in ROLE_IDS:
                errors.append(f"invalid_role:{role_id}")
            elif role_id not in existing_roles:
                errors.append(f"unknown_role:{role_id}")
        for permission in permissions + denies:
            if permission not in PERMISSIONS:
                errors.append(f"invalid_permission:{permission}")
            if permission in OWNER_ONLY_PERMISSIONS and actor_role != OWNER_ROLE:
                errors.append(f"owner_only_permission:{permission}")
        for permission in permissions:
            if permission in OWNER_ONLY_PERMISSIONS:
                errors.append(f"owner_only_permission_not_assignable:{permission}")
        if "DESIGN_ENGINEER" in role_ids and "QA_ENGINEER" in role_ids:
            errors.append("unsafe_role_conflict:author_and_independent_reviewer")
        return errors

    @staticmethod
    def _require_owner(actor_role: str) -> None:
        if actor_role != OWNER_ROLE:
            raise PermissionError("owner_authority_required")

    def _transition_lifecycle(self, agent_id: str, next_state: str) -> None:
        row = self.database.get_agent_profile(agent_id)
        if row is None:
            raise ValueError(f"Unknown agent profile: {agent_id}")
        current = str(row["lifecycle_state"])
        if next_state not in LIFECYCLE_TRANSITIONS.get(current, set()):
            raise ValueError(f"invalid_lifecycle_transition:{current}->{next_state}")

    def _summary_from_row(self, row) -> EmployeeSummary:
        agent_id = str(row["agent_id"])
        roles = self.database.list_agent_roles(agent_id)
        grants = self.database.list_agent_permissions(agent_id)
        denies = self.database.list_agent_permission_denies(agent_id)
        effective = sorted(self.effective_permissions(roles, grants, denies))
        provider_id = str(row["provider_id"])
        status = "UNKNOWN"
        warnings = self.configuration_warnings(roles, provider_id, str(row["lifecycle_state"]), set(effective), status)
        availability = self._execution_eligibility(str(row["lifecycle_state"]), provider_id, set(effective), warnings)
        return EmployeeSummary(
            agent_id=agent_id,
            display_name=str(row["display_name"]),
            lifecycle_state=str(row["lifecycle_state"]),
            provider_id=provider_id,
            persona_id=str(row["persona_id"]) if row["persona_id"] else None,
            roles=roles,
            direct_permissions=grants,
            permission_denies=denies,
            effective_permissions=effective,
            availability=availability,
            warnings=warnings,
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _execution_eligibility(
        lifecycle_state: str,
        provider_id: str,
        effective_permissions: set[str],
        warnings: list[str],
    ) -> str:
        if lifecycle_state == "ARCHIVED":
            return "ARCHIVED"
        if lifecycle_state == "SUSPENDED":
            return "SUSPENDED"
        if lifecycle_state in ("DRAFT", "DISABLED"):
            return lifecycle_state
        if provider_id in ("UNAVAILABLE", "FUTURE_PROVIDER"):
            return "NO_AVAILABLE_PROVIDER"
        if any(warning.startswith("BLOCKING") for warning in warnings):
            return "CONFIGURATION_BLOCKED"
        if "CHAT" not in effective_permissions:
            return "NO_CHAT_PERMISSION"
        return "AVAILABLE"

    @staticmethod
    def _profile_payload(profile: AgentProfile, roles: list[str], grants: list[str], denies: list[str]) -> dict[str, object]:
        return {
            "schema_version": profile.schema_version,
            "agent_id": profile.agent_id,
            "display_name": profile.display_name,
            "description": profile.description,
            "lifecycle_state": profile.lifecycle_state,
            "provider_id": profile.provider_id,
            "persona_id": profile.persona_id,
            "avatar_path": profile.avatar_path,
            "aliases": list(profile.aliases),
            "full_name": profile.full_name or profile.display_name,
            "preferred_name": profile.preferred_name,
            "informal_name": profile.informal_name,
            "communication_profile": profile.communication_profile,
            "roles": roles,
            "permission_grants": grants,
            "permission_denies": denies,
        }

    @staticmethod
    def _aliases_from_row(row) -> tuple[str, ...]:
        try:
            raw = json.loads(str(row["aliases"] or "[]"))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return ()
        return tuple(str(alias).strip() for alias in raw if str(alias).strip()) if isinstance(raw, list) else ()

    @staticmethod
    def _communication_profile_from_row(row) -> dict[str, object]:
        try:
            raw = json.loads(str(row["communication_profile"] or "{}"))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return {}
        return raw if isinstance(raw, dict) else {}
