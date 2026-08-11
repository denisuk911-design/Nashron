from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .database import Database
from .management_models import AgentProfile, ROLE_DEFAULT_PERMISSIONS, RoleProfile


@dataclass(frozen=True)
class Profession:
    profession_id: str
    name: str
    description: str
    responsibilities: tuple[str, ...]
    typical_results: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    initial_skills: tuple[str, ...]
    recommended_tools: tuple[str, ...]
    knowledge_sources: tuple[str, ...]
    qualification_method: str
    status: str


@dataclass(frozen=True)
class Organization:
    organization_id: str
    name: str
    purpose: str
    description: str
    status: str
    management_model_id: str | None = None
    domain_package: str = ""
    responsibility_model_id: str | None = None


@dataclass(frozen=True)
class OrganizationTemplate:
    template_id: str
    name: str
    purpose: str
    recommended_team_size: str
    roles: tuple[dict[str, Any], ...]
    workflow_id: str | None
    version: str
    source_rationale: str
    limitations: tuple[str, ...]
    management_model_id: str | None = None
    domain_package: str = ""
    responsibility_model_id: str | None = None
    catalog_category: str = "Other"
    review_required: bool = False
    research_required: bool = False
    learning_support: bool = False


@dataclass(frozen=True)
class ManagementModel:
    management_model_id: str
    name: str
    description: str
    category: str
    structure_type: str
    decision_model: str
    responsibility_model: str
    workflow_style: str
    recommended_team_size: str
    advantages: tuple[str, ...]
    limitations: tuple[str, ...]
    source_rationale: str


@dataclass(frozen=True)
class OrganizationActivation:
    organization: Organization
    member_ids: tuple[str, ...]
    employee_ids: tuple[str, ...]
    workspace_id: str
    status: str
    missing_providers: tuple[str, ...]


@dataclass(frozen=True)
class WorkflowDefinition:
    workflow_id: str
    name: str
    version: str
    description: str
    steps: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class LearningSource:
    source_id: str
    title: str
    source_type: str
    location: str
    processed_state: str


class UniversalPlatformService:
    """Domain-neutral U1 control-plane and fixture service.

    PCB, software and culinary data enter through the same generic records.
    This service is deliberately independent from providers and chat personas.
    """

    def __init__(
        self,
        database: Database,
        management_service: Any | None = None,
        workspace_root: Path | None = None,
        conversation_id: int | None = None,
    ) -> None:
        self.database = database
        self.management_service = management_service
        self.workspace_root = workspace_root
        self.conversation_id = conversation_id

    def create_profession(self, name: str, description: str = "", **values: Any) -> Profession:
        name = name.strip()
        if not name:
            raise ValueError("profession_name_required")
        profession_id = self.database.create_profession({"name": name, "description": description.strip(), **values})
        row = self.database.get_profession(profession_id)
        assert row is not None
        return self._profession(row)

    def list_professions(self) -> list[Profession]:
        return [self._profession(row) for row in self.database.list_professions()]

    def create_organization(self, name: str, purpose: str = "", description: str = "", **values: Any) -> Organization:
        name = name.strip()
        if not name:
            raise ValueError("organization_name_required")
        organization_id = self.database.create_organization({"name": name, "purpose": purpose.strip(), "description": description.strip(), **values})
        organization_conversation_id = self.database.ensure_organization_conversation(organization_id, name)
        workspace_id = self.database.create_organization_workspace(
            {
                "organization_id": organization_id,
                "conversation_id": organization_conversation_id,
                "workspace_path": str(self.workspace_root or ""),
                "routing_config": {},
                "status": "READY_EMPTY",
            }
        )
        self.database.create_organization_activation_event(organization_id, "WORKSPACE_CREATED", "READY_EMPTY", {"workspace_id": workspace_id})
        row = next(row for row in self.database.list_organizations() if str(row["id"]) == organization_id)
        return self._organization(row)

    def list_organizations(self) -> list[Organization]:
        return [self._organization(row) for row in self.database.list_organizations()]

    def set_organization_status(self, organization_id: str, status: str) -> Organization:
        status = str(status).upper().strip()
        self.database.set_organization_status(organization_id, status)
        if status == "ACTIVE":
            self.database.set_active_organization(organization_id)
        row = next(row for row in self.database.list_organizations() if str(row["id"]) == organization_id)
        return self._organization(row)

    def archive_organization(self, organization_id: str) -> Organization:
        return self.set_organization_status(organization_id, "ARCHIVED")

    def restore_organization(self, organization_id: str) -> Organization:
        return self.set_organization_status(organization_id, "ACTIVE")

    def delete_organization(self, organization_id: str) -> None:
        self.database.delete_organization(organization_id)

    def list_management_models(self) -> list[ManagementModel]:
        return [self._management_model(row) for row in self.database.list_management_models()]

    def create_management_model(self, name: str, **values: Any) -> ManagementModel:
        model_id = self.database.create_management_model({"name": name.strip(), **values})
        row = self.database.get_management_model(model_id)
        assert row is not None
        return self._management_model(row)

    def list_responsibility_models(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self.database.list_responsibility_models()]

    def create_workflow(self, name: str, steps: list[dict[str, Any]], description: str = "") -> WorkflowDefinition:
        workflow_id = self.database.create_workflow({"name": name.strip(), "description": description.strip()}, steps)
        row = next(row for row in self.database.list_workflows() if str(row["id"]) == workflow_id)
        return self._workflow(row)

    def create_template(self, name: str, purpose: str, roles: list[dict[str, Any]], workflow_id: str | None = None, **values: Any) -> OrganizationTemplate:
        template_id = self.database.create_organization_template(
            {
                "name": name.strip(),
                "purpose": purpose.strip(),
                "roles": roles,
                "workflow_id": workflow_id,
                "source_rationale": values.pop("source_rationale", "Created by organization owner"),
                **values,
            }
        )
        row = self.database.get_organization_template(template_id)
        assert row is not None
        return self._template(row)

    def list_templates(self) -> list[OrganizationTemplate]:
        return [self._template(row) for row in self.database.list_organization_templates()]

    def add_learning_source(self, title: str, source_type: str, location: str = "", trust_metadata: dict[str, Any] | None = None) -> LearningSource:
        source_id = self.database.create_learning_source({"title": title.strip(), "source_type": source_type, "location": location, "trust_metadata": trust_metadata or {}})
        row = next(row for row in self.database.list_learning_sources() if str(row["id"]) == source_id)
        return LearningSource(source_id, str(row["title"]), str(row["source_type"]), str(row["location"] or ""), str(row["processed_state"]))

    def update_runtime_state(self, agent_id: str, **values: Any) -> None:
        self.database.upsert_agent_runtime_state(agent_id, values)

    def instantiate_template(self, template_id: str, organization_name: str, purpose: str = "") -> Organization:
        template = self.database.get_organization_template(template_id)
        if template is None:
            raise ValueError("unknown_organization_template")
        organization = self.create_organization(organization_name, purpose or str(template["purpose"] or ""))
        for role in self._json_list(template["roles"]):
            profession_id = str(role.get("profession_id")) if role.get("profession_id") else None
            if profession_id is None and role.get("profession"):
                profession = next((item for item in self.list_professions() if item.name.lower() == str(role["profession"]).lower()), None)
                profession_id = profession.profession_id if profession else None
            self.database.create_organization_member(
                {
                    "organization_id": organization.organization_id,
                    "profession_id": profession_id,
                    "role_id": role.get("role_id"),
                    "position": role.get("position") or role.get("role") or "",
                    "responsibilities": role.get("responsibilities", []),
                }
            )
        self.database.audit_event("organization_instantiated", None, {"organization_id": organization.organization_id, "template_id": template_id})
        return organization

    def activate_template(
        self,
        template_id: str,
        organization_name: str,
        *,
        purpose: str = "",
        team_size: str = "STANDARD",
        provider_assignments: dict[str, str] | None = None,
        use_existing_agents: dict[str, str] | None = None,
        workspace_path: str = "",
    ) -> OrganizationActivation:
        """Turn a template into an operational organization and chat roster."""
        row = self.database.get_organization_template(template_id)
        if row is None:
            raise ValueError("unknown_organization_template")
        provider_assignments = provider_assignments or {}
        use_existing_agents = use_existing_agents or {}
        organization_id = self.database.create_organization(
            {
                "name": organization_name.strip(),
                "purpose": purpose.strip() or str(row["purpose"] or ""),
                "active_template_id": template_id,
                "management_model_id": row["management_model_id"],
                "domain_package": str(row["domain_package"] or ""),
                "responsibility_model_id": row["responsibility_model_id"],
            }
        )
        organization_conversation_id = self.database.ensure_organization_conversation(organization_id, organization_name.strip())
        self.database.create_organization_activation_event(organization_id, "ACTIVATION_REQUESTED", "STARTED", {"template_id": template_id, "name": organization_name})
        roles = self._json_list(row["roles"])
        roles = [role for role in roles if isinstance(role, dict) and self._role_in_variant(role, team_size)]
        variants = self._json_value(row["team_size_variants"]) if "team_size_variants" in row.keys() else {}
        selected_positions = variants.get(team_size) if isinstance(variants, dict) else None
        if isinstance(selected_positions, list) and selected_positions:
            allowed = {str(item).strip().lower() for item in selected_positions}
            roles = [role for role in roles if str(role.get("position") or role.get("role") or "").strip().lower() in allowed]
        department_ids: dict[str, str] = {}
        member_ids: list[str] = []
        employee_ids: list[str] = []
        missing_providers: list[str] = []
        for index, role in enumerate(roles, start=1):
            department_name = str(role.get("department") or "")
            department_id = None
            if department_name:
                department_id = department_ids.get(department_name)
                if department_id is None:
                    department_id = self.database.create_organization_department({"organization_id": organization_id, "name": department_name})
                    department_ids[department_name] = department_id
            position = str(role.get("position") or role.get("role") or f"Специалист {index}").strip()
            role_id = self._ensure_role_profile(role)
            provider = str(provider_assignments.get(position) or provider_assignments.get(str(role.get("role") or "")) or role.get("provider_id") or "UNAVAILABLE")
            existing_agent_id = use_existing_agents.get(position) or use_existing_agents.get(str(role.get("role") or ""))
            assignment_mode = "USE_EXISTING" if existing_agent_id else "AUTO_CREATE"
            agent_id = existing_agent_id
            if existing_agent_id and provider == "UNAVAILABLE":
                existing_profile = self.database.get_agent_profile(existing_agent_id)
                if existing_profile is not None:
                    provider = str(existing_profile["provider_id"] or "UNAVAILABLE")
            if agent_id is None:
                agent_id = self._create_operational_employee(position, role_id, provider, role)
            if agent_id:
                employee_ids.append(agent_id)
            provisioning = "READY" if provider in {"CODEX_CLI", "GEMINI_CLI", "CLAUDE_CLI"} else "UNASSIGNED"
            missing_reason = "" if provisioning == "READY" else "Требуется AI-движок"
            if provisioning != "READY":
                missing_providers.append(position)
            member_id = self.database.create_organization_member(
                {
                    "organization_id": organization_id,
                    "department_id": department_id,
                    "agent_id": agent_id,
                    "profession_id": self._profession_id_for_role(role),
                    "role_id": role_id,
                    "position": position,
                    "responsibilities": role.get("responsibilities", []),
                    "provider_id": provider,
                    "assignment_mode": assignment_mode,
                    "provisioning_status": provisioning,
                    "missing_reason": missing_reason,
                    "required_capabilities": role.get("required_capabilities", []),
                    "permissions": role.get("permissions", ["CHAT"]),
                    "recommended_tools": role.get("recommended_tools", []),
                }
            )
            member_ids.append(member_id)
        workspace_id = self.database.create_organization_workspace(
            {
                "organization_id": organization_id,
                "conversation_id": organization_conversation_id,
                "workspace_path": workspace_path or str(self.workspace_root or ""),
                "routing_config": {"template_id": template_id, "workflow_id": row["workflow_id"], "team_size": team_size},
                "status": "READY_WITH_UNASSIGNED" if missing_providers else "READY",
                "is_active": True,
            }
        )
        self.database.set_active_organization(organization_id)
        self.database.create_organization_activation_event(
            organization_id, "ACTIVATION_COMPLETED", "READY_WITH_UNASSIGNED" if missing_providers else "READY",
            {"members": len(member_ids), "employees": len(employee_ids), "missing_providers": missing_providers},
        )
        org_row = next(item for item in self.database.list_organizations() if str(item["id"]) == organization_id)
        return OrganizationActivation(self._organization(org_row), tuple(member_ids), tuple(employee_ids), workspace_id, "READY_WITH_UNASSIGNED" if missing_providers else "READY", tuple(missing_providers))

    def organization_dashboard(self, organization_id: str) -> dict[str, Any]:
        dashboard = self.database.organization_dashboard(organization_id)
        dashboard["members"] = [dict(row) for row in self.database.list_organization_members(organization_id)]
        dashboard["workspace"] = dict(self.database.get_organization_workspace(organization_id) or {})
        dashboard["activation_events"] = [dict(row) for row in self.database.list_organization_activation_events(organization_id)]
        return dashboard

    def seed_demo_fixtures(self) -> dict[str, str]:
        """Create management library and domain fixtures using the same core."""
        self.seed_management_library()
        professions = {item.name.lower(): item for item in self.list_professions()}
        definitions = [
            ("Product Manager", "Owns objective, plan and approvals."),
            ("Software Engineer", "Creates and verifies software artifacts."),
            ("QA Engineer", "Reviews results independently."),
            ("Head Chef", "Owns culinary product concept and final approval."),
            ("Cook / Recipe Developer", "Creates reproducible recipes."),
            ("Food Researcher", "Verifies sources and food risks."),
            ("Recipe Reviewer", "Reviews recipe quality and consistency."),
            ("Learning Coordinator", "Maintains practice and qualification."),
        ]
        for name, description in definitions:
            if name.lower() not in professions:
                professions[name.lower()] = self.create_profession(name, description, responsibilities=[description])
        existing_templates = {item.name for item in self.list_templates()}
        result: dict[str, str] = {}
        software_workflow = self._ensure_fixture_workflow(
            "SOFTWARE_PRODUCT_WORKFLOW",
            [
                {"responsibility": "Project Manager", "operation": "PLAN", "expected_outputs": ["task plan"]},
                {"responsibility": "Software Engineer", "operation": "CREATE", "expected_outputs": ["source artifact"]},
                {"responsibility": "QA Engineer", "operation": "REVIEW", "expected_outputs": ["review findings"]},
                {"responsibility": "Software Engineer", "operation": "MODIFY", "expected_outputs": ["corrected artifact"]},
            ],
        )
        culinary_workflow = self._ensure_fixture_workflow(
            "CULINARY_PRODUCT_WORKFLOW",
            [
                {"responsibility": "Head Chef", "operation": "CREATE", "expected_outputs": ["concept"]},
                {"responsibility": "Cook / Recipe Developer", "operation": "CREATE", "expected_outputs": ["recipe"]},
                {"responsibility": "Food Researcher", "operation": "VERIFY", "expected_outputs": ["source evidence"]},
                {"responsibility": "Recipe Reviewer", "operation": "REVIEW", "expected_outputs": ["review findings"]},
                {"responsibility": "Head Chef", "operation": "APPROVE", "expected_outputs": ["approved recipe"]},
            ],
        )
        if "SOFTWARE_PRODUCT_TEAM" not in existing_templates:
            result["software_template_id"] = self.create_template(
                "SOFTWARE_PRODUCT_TEAM", "Generic software product team", [
                    {"profession": "Product Manager", "position": "Project Manager"},
                    {"profession": "Software Engineer", "position": "Developer"},
                    {"profession": "QA Engineer", "position": "QA"},
                ], software_workflow.workflow_id, recommended_team_size="MINI/STANDARD", source_rationale="Demonstration fixture; not a universal best practice.", limitations=["Requires project-specific tools and review policy."]
            ).template_id
        if "CULINARY_PRODUCT_TEAM" not in existing_templates:
            result["culinary_template_id"] = self.create_template(
                "CULINARY_PRODUCT_TEAM", "Generic culinary product team", [
                    {"profession": "Head Chef", "position": "Head Chef"},
                    {"profession": "Cook / Recipe Developer", "position": "Recipe Developer"},
                    {"profession": "Food Researcher", "position": "Researcher"},
                    {"profession": "Recipe Reviewer", "position": "Reviewer"},
                    {"profession": "Learning Coordinator", "position": "Learning Coordinator"},
                ], culinary_workflow.workflow_id, recommended_team_size="STANDARD", source_rationale="Domain-independence architecture fixture; not a business guarantee.", limitations=["Food safety and local regulations require qualified human review."]
            ).template_id
        return result

    def seed_management_library(self) -> None:
        existing = {str(row["name"]) for row in self.database.list_management_models()}
        models = [
            ("FUNCTIONAL", "Specialized departments with stable ownership.", "GENERAL", "FUNCTIONAL", "Owner delegates by specialty.", "RACI", "SPECIALIZED", "STANDARD", ["Clear expertise"], ["Cross-team handoffs can be slow"], "General organizational pattern."),
            ("PROJECTIZED", "Temporary project team around one outcome.", "GENERAL", "PROJECTIZED", "Project lead decides within mandate.", "RACI", "PROJECT", "MINI/STANDARD", ["Fast focus"], ["Weak long-term specialization"], "General organizational pattern."),
            ("MATRIX", "Functional and project responsibility relations coexist.", "GENERAL", "MATRIX", "Decision depends on responsibility context.", "RACI", "MATRIX", "STANDARD", ["Shares experts"], ["Conflicting managers require explicit RACI"], "General organizational pattern."),
            ("FLAT", "Minimal hierarchy for a small team.", "GENERAL", "FLAT", "Consensus or owner decision.", "RACI", "LIGHTWEIGHT", "MINI", ["Low coordination overhead"], ["Ambiguous escalation at scale"], "General organizational pattern."),
            ("CROSS_FUNCTIONAL", "Different specialties jointly deliver one outcome.", "GENERAL", "CROSS_FUNCTIONAL", "Lead coordinates; specialists self-manage their work.", "RACI", "PRODUCT", "STANDARD", ["End-to-end delivery"], ["Needs clear scope"], "General organizational pattern."),
        ]
        for name, description, category, structure, decision, responsibility, workflow, size, advantages, limitations, source in models:
            if name not in existing:
                self.database.create_management_model({"id": f"MGMT-{name}", "name": name, "description": description, "category": category, "structure_type": structure, "decision_model": decision, "responsibility_model": responsibility, "workflow_style": workflow, "recommended_team_size": size, "advantages": advantages, "limitations": limitations, "source_rationale": source})
        if not self.database.list_responsibility_models():
            self.database.create_responsibility_model({"id": "RESP-RACI", "name": "RACI", "description": "Responsible, Accountable, Consulted, Informed.", "accountabilities": ["Responsible", "Accountable", "Consulted", "Informed"], "source_rationale": "Standard project responsibility concept."})
            self.database.create_responsibility_model({"id": "RESP-CRA", "name": "CREATOR_REVIEWER_APPROVER", "description": "A lightweight create, review and approval chain.", "accountabilities": ["Creator", "Reviewer", "Approver"], "source_rationale": "Generic quality workflow preset."})
            self.database.create_responsibility_model({"id": "RESP-KANBAN", "name": "KANBAN_OVERLAY", "description": "Flow overlay applied to an organization, not an organization hierarchy.", "accountabilities": ["BACKLOG", "READY", "IN_PROGRESS", "REVIEW", "DONE"], "source_rationale": "Kanban work management concept."})

        existing_templates = {str(item["name"]) for item in self.database.list_organization_templates()}
        presets = self._preset_catalog()
        for preset in presets:
            if preset["name"] in existing_templates:
                continue
            workflow = self._ensure_fixture_workflow(preset["workflow_name"], preset["steps"])
            self.create_template(
                preset["name"], preset["purpose"], preset["roles"], workflow.workflow_id,
                management_model_id=f"MGMT-{preset['management_model']}",
                responsibility_model_id=preset["responsibility_model"],
                domain_package=preset.get("domain", ""),
                recommended_team_size=preset["team_size"],
                catalog_category=preset["category"],
                source_rationale=preset["source"],
                limitations=preset["limitations"],
                review_required=preset.get("review_required", True),
                research_required=preset.get("research_required", False),
                learning_support=preset.get("learning_support", False),
                team_size_variants=preset.get("variants", {}),
            )

    def _preset_catalog(self) -> list[dict[str, Any]]:
        common_roles = [
            {"profession": "Product Manager", "position": "Project Manager", "role": "Project Manager", "department": "Operations", "provider_id": "UNAVAILABLE"},
            {"profession": "Software Engineer", "position": "Developer", "role": "Developer", "department": "Engineering", "provider_id": "UNAVAILABLE"},
            {"profession": "QA Engineer", "position": "Reviewer", "role": "Reviewer", "department": "QA", "provider_id": "UNAVAILABLE"},
        ]
        presets = [
            {"name": "SCRUM_SOFTWARE_TEAM", "purpose": "Small cross-functional software team based on Scrum accountabilities.", "management_model": "CROSS_FUNCTIONAL", "responsibility_model": "RESP-RACI", "category": "Development", "team_size": "10 OR LESS", "workflow_name": "SCRUM_PRODUCT_WORKFLOW", "roles": [{"position": "Product Owner", "role": "Product Owner", "department": "Product"}, {"position": "Scrum Master", "role": "Scrum Master", "department": "Operations"}, {"position": "Developer", "role": "Developer", "department": "Developers"}, {"position": "QA", "role": "QA", "department": "Developers"}], "steps": [{"responsibility": "Product Owner", "operation": "PLAN", "expected_outputs": ["backlog"]}, {"responsibility": "Developers", "operation": "CREATE", "expected_outputs": ["increment"]}, {"responsibility": "QA", "operation": "REVIEW", "expected_outputs": ["findings"]}], "source": "Scrum Guide; accountabilities are not a hierarchy.", "limitations": ["Needs a product backlog and owner decisions."], "variants": {"MINI": ["Product Owner", "Developer", "QA"], "STANDARD": ["Product Owner", "Scrum Master", "Developer", "QA"]}},
            {"name": "SOFTWARE_PRODUCT_TEAM", "purpose": "Product development with plan, build, review and documentation.", "management_model": "CROSS_FUNCTIONAL", "responsibility_model": "RESP-RACI", "category": "Development", "team_size": "MINI/STANDARD", "workflow_name": "SOFTWARE_PRODUCT_WORKFLOW", "roles": common_roles + [{"position": "Documentation", "role": "Documentation", "department": "Documentation"}], "steps": [{"responsibility": "Project Manager", "operation": "PLAN", "expected_outputs": ["task plan"]}, {"responsibility": "Developer", "operation": "CREATE", "expected_outputs": ["source artifact"]}, {"responsibility": "Reviewer", "operation": "REVIEW", "expected_outputs": ["review findings"]}], "source": "Team2050 software domain fixture.", "limitations": ["Project-specific tools and review policy are required."], "learning_support": True},
            {"name": "ENGINEERING_PRODUCT_TEAM", "purpose": "Domain-neutral engineering product team.", "management_model": "PROJECTIZED", "responsibility_model": "RESP-RACI", "category": "Engineering", "domain": "ENGINEERING", "team_size": "STANDARD", "workflow_name": "ENGINEERING_PRODUCT_WORKFLOW", "roles": [{"position": "Project Lead", "role": "Project Lead", "department": "Engineering"}, {"position": "Design Engineer", "role": "Design Engineer", "department": "Engineering"}, {"position": "Component Specialist", "role": "Specialist", "department": "Research"}, {"position": "Independent Reviewer", "role": "Reviewer", "department": "QA"}, {"position": "Test Engineer", "role": "Test Engineer", "department": "QA"}, {"position": "Documentation", "role": "Documentation", "department": "Documentation"}], "steps": [{"responsibility": "Design Engineer", "operation": "CREATE", "expected_outputs": ["engineering artifact"]}, {"responsibility": "Independent Reviewer", "operation": "REVIEW", "expected_outputs": ["findings"]}, {"responsibility": "Test Engineer", "operation": "VERIFY", "expected_outputs": ["test evidence"]}], "source": "Generic engineering product pattern.", "limitations": ["Electrical, mechanical and PCB specializations belong in domain packages." ]},
            {"name": "RESEARCH_TEAM", "purpose": "Evidence-led research and synthesis.", "management_model": "FUNCTIONAL", "responsibility_model": "RESP-RACI", "category": "Research", "team_size": "STANDARD", "workflow_name": "RESEARCH_WORKFLOW", "roles": [{"position": "Research Lead", "role": "Research Lead", "department": "Research"}, {"position": "Primary Researcher", "role": "Researcher", "department": "Research"}, {"position": "Source Researcher", "role": "Source Researcher", "department": "Research"}, {"position": "Critical Reviewer", "role": "Critical Reviewer", "department": "QA"}, {"position": "Documentation", "role": "Documentation", "department": "Documentation"}], "steps": [{"responsibility": "Research Lead", "operation": "PLAN", "expected_outputs": ["research plan"]}, {"responsibility": "Primary Researcher", "operation": "COLLECT", "expected_outputs": ["evidence"]}, {"responsibility": "Critical Reviewer", "operation": "REVIEW", "expected_outputs": ["critical findings"]}], "source": "Generic research workflow.", "limitations": ["Sources require provenance and review."], "research_required": True},
            {"name": "CONSULTING_TEAM", "purpose": "Client problem to reviewed recommendation.", "management_model": "PROJECTIZED", "responsibility_model": "RESP-RACI", "category": "Business", "team_size": "STANDARD", "workflow_name": "CONSULTING_WORKFLOW", "roles": [{"position": "Engagement Lead", "role": "Engagement Lead"}, {"position": "Domain Specialist", "role": "Domain Specialist"}, {"position": "Researcher", "role": "Researcher"}, {"position": "Analyst", "role": "Analyst"}, {"position": "Reviewer", "role": "Reviewer"}, {"position": "Documentation", "role": "Documentation"}], "steps": [{"responsibility": "Engagement Lead", "operation": "CLARIFY", "expected_outputs": ["scope"]}, {"responsibility": "Researcher", "operation": "RESEARCH", "expected_outputs": ["evidence"]}, {"responsibility": "Reviewer", "operation": "REVIEW", "expected_outputs": ["findings"]}], "source": "Generic consulting workflow.", "limitations": ["Recommendations need client acceptance."], "research_required": True},
            {"name": "DOCUMENT_PRODUCTION_TEAM", "purpose": "Controlled document creation with review and approval.", "management_model": "FUNCTIONAL", "responsibility_model": "RESP-CRA", "category": "Documents", "team_size": "MINI/STANDARD", "workflow_name": "CRA_WORKFLOW", "roles": [{"position": "Request Owner", "role": "Request Owner"}, {"position": "Author", "role": "Author"}, {"position": "Technical Reviewer", "role": "Reviewer"}, {"position": "Document Controller", "role": "Documentation"}, {"position": "Approver", "role": "Approver"}], "steps": [{"responsibility": "Author", "operation": "CREATE", "expected_outputs": ["document artifact"]}, {"responsibility": "Technical Reviewer", "operation": "REVIEW", "expected_outputs": ["findings"]}, {"responsibility": "Approver", "operation": "APPROVE", "expected_outputs": ["decision"]}], "source": "Team2050 controlled document workflow.", "limitations": ["Document Controller must receive an artifact handoff, not invent a memo." ]},
            {"name": "CREATIVE_TEAM", "purpose": "Research, creation, editing and fact checking.", "management_model": "CROSS_FUNCTIONAL", "responsibility_model": "RESP-RACI", "category": "Creative", "team_size": "STANDARD", "workflow_name": "CREATIVE_WORKFLOW", "roles": [{"position": "Creative Lead", "role": "Creative Lead"}, {"position": "Researcher", "role": "Researcher"}, {"position": "Creator", "role": "Creator"}, {"position": "Editor", "role": "Editor"}, {"position": "Fact Checker", "role": "Fact Checker"}, {"position": "Documentation", "role": "Documentation"}], "steps": [{"responsibility": "Creator", "operation": "CREATE", "expected_outputs": ["draft"]}, {"responsibility": "Editor", "operation": "EDIT", "expected_outputs": ["edited draft"]}, {"responsibility": "Fact Checker", "operation": "VERIFY", "expected_outputs": ["fact checks"]}], "source": "Generic creative production pattern.", "limitations": ["Not every member speaks on every message." ]},
            {"name": "CULINARY_BRIGADE", "purpose": "AI-scale brigade de cuisine structure for recipe products.", "management_model": "FUNCTIONAL", "responsibility_model": "RESP-RACI", "category": "Culinary", "domain": "CULINARY", "team_size": "STANDARD", "workflow_name": "CULINARY_PRODUCT_WORKFLOW", "roles": [{"profession": "Head Chef", "position": "Head Chef", "role": "Head Chef", "department": "Kitchen"}, {"position": "Sous Chef", "role": "Sous Chef", "department": "Kitchen"}, {"profession": "Cook / Recipe Developer", "position": "Recipe Developer", "role": "Recipe Developer", "department": "Kitchen"}, {"profession": "Food Researcher", "position": "Food Researcher", "role": "Researcher", "department": "Research"}, {"profession": "Recipe Reviewer", "position": "Recipe Reviewer", "role": "Reviewer", "department": "QA"}], "steps": [{"responsibility": "Head Chef", "operation": "CREATE", "expected_outputs": ["concept"]}, {"responsibility": "Recipe Developer", "operation": "CREATE", "expected_outputs": ["recipe"]}, {"responsibility": "Researcher", "operation": "VERIFY", "expected_outputs": ["source evidence"]}, {"responsibility": "Reviewer", "operation": "REVIEW", "expected_outputs": ["findings"]}], "source": "Brigade de cuisine / Escoffier structure adapted to AI-team scale.", "limitations": ["Food safety requires qualified human review."], "research_required": True},
            {"name": "LEARNING_TEAM", "purpose": "Controlled development of employee skills and knowledge.", "management_model": "FUNCTIONAL", "responsibility_model": "RESP-CRA", "category": "Learning", "team_size": "STANDARD", "workflow_name": "LEARNING_WORKFLOW", "roles": [{"position": "Learning Coordinator", "role": "Learning Coordinator"}, {"position": "Subject Specialist", "role": "Specialist"}, {"position": "Researcher", "role": "Researcher"}, {"position": "Trainer", "role": "Trainer"}, {"position": "Examiner", "role": "Reviewer"}], "steps": [{"responsibility": "Researcher", "operation": "COLLECT", "expected_outputs": ["learning source"]}, {"responsibility": "Trainer", "operation": "PRACTICE", "expected_outputs": ["practice result"]}, {"responsibility": "Examiner", "operation": "QUALIFY", "expected_outputs": ["qualification decision"]}], "source": "Team2050 learning architecture.", "limitations": ["Learning is not proven by narrative alone."], "learning_support": True},
            {"name": "SMALL_BUSINESS_TEAM", "purpose": "Compact owner-led operations team.", "management_model": "FLAT", "responsibility_model": "RESP-RACI", "category": "Business", "team_size": "MINI/STANDARD", "workflow_name": "SMALL_BUSINESS_WORKFLOW", "roles": [{"position": "Owner", "role": "Owner"}, {"position": "Operations", "role": "Operations Specialist"}, {"position": "Domain Specialist", "role": "Specialist"}, {"position": "Finance/Admin", "role": "Finance"}], "steps": [{"responsibility": "Owner", "operation": "PLAN", "expected_outputs": ["decision"]}, {"responsibility": "Operations", "operation": "EXECUTE", "expected_outputs": ["result"]}, {"responsibility": "Finance/Admin", "operation": "REVIEW", "expected_outputs": ["record"]}], "source": "Generic small business pattern.", "limitations": ["Owner remains accountable for consequential decisions." ]},
            {"name": "SOLO_PROFESSIONAL", "purpose": "One user supported by focused AI roles.", "management_model": "FLAT", "responsibility_model": "RESP-CRA", "category": "Other", "team_size": "MINI", "workflow_name": "SOLO_SUPPORT_WORKFLOW", "roles": [{"position": "Assistant", "role": "Assistant"}, {"position": "Researcher", "role": "Researcher"}, {"position": "Reviewer", "role": "Reviewer"}], "steps": [{"responsibility": "Assistant", "operation": "EXECUTE", "expected_outputs": ["draft"]}, {"responsibility": "Reviewer", "operation": "REVIEW", "expected_outputs": ["findings"]}], "source": "Team2050 solo support preset.", "limitations": ["User remains the owner and final approver." ]},
            {"name": "ADVISORY_BOARD", "purpose": "A small board of specialists consulted on demand.", "management_model": "FLAT", "responsibility_model": "RESP-RACI", "category": "Business", "team_size": "MINI", "workflow_name": "ADVISORY_WORKFLOW", "roles": [{"position": "Domain Expert A", "role": "Expert"}, {"position": "Domain Expert B", "role": "Expert"}, {"position": "Critical Reviewer", "role": "Reviewer"}, {"position": "Researcher", "role": "Researcher"}], "steps": [{"responsibility": "Researcher", "operation": "RESEARCH", "expected_outputs": ["evidence"]}, {"responsibility": "Critical Reviewer", "operation": "REVIEW", "expected_outputs": ["risks"]}], "source": "Team2050 advisory preset.", "limitations": ["Members answer only when consulted or directly addressed." ]},
            {"name": "INCIDENT_COMMAND_STYLE", "purpose": "Operations coordination inspired by incident command functions.", "management_model": "FUNCTIONAL", "responsibility_model": "RESP-RACI", "category": "Operations", "team_size": "STANDARD", "workflow_name": "INCIDENT_WORKFLOW", "roles": [{"position": "Coordinator", "role": "Coordinator", "department": "Command"}, {"position": "Operations", "role": "Operations", "department": "Operations"}, {"position": "Planning", "role": "Planning", "department": "Planning"}, {"position": "Resource Coordinator", "role": "Resource Coordinator", "department": "Logistics"}, {"position": "Documentation/Admin", "role": "Documentation", "department": "Finance/Admin"}], "steps": [{"responsibility": "Coordinator", "operation": "COMMAND", "expected_outputs": ["objective"]}, {"responsibility": "Operations", "operation": "EXECUTE", "expected_outputs": ["status"]}, {"responsibility": "Planning", "operation": "REVIEW", "expected_outputs": ["plan update"]}], "source": "Conceptual inspiration from official ICS structural principles; not an ICS replacement.", "limitations": ["Not official emergency command software." ]},
            {"name": "OPERATIONS_SUPPORT_TEAM", "purpose": "Shared operational support for tools, resources and administration.", "management_model": "FUNCTIONAL", "responsibility_model": "RESP-RACI", "category": "Operations", "team_size": "STANDARD", "workflow_name": "OPERATIONS_SUPPORT_WORKFLOW", "roles": [{"position": "Operations Lead", "role": "Operations Lead"}, {"position": "Tool Coordinator", "role": "Resource Coordinator"}, {"position": "Specialist", "role": "Specialist"}, {"position": "Reviewer", "role": "Reviewer"}], "steps": [{"responsibility": "Operations Lead", "operation": "PLAN", "expected_outputs": ["work order"]}, {"responsibility": "Specialist", "operation": "EXECUTE", "expected_outputs": ["result"]}, {"responsibility": "Reviewer", "operation": "REVIEW", "expected_outputs": ["status"]}], "source": "Generic operations support pattern.", "limitations": ["Tool access remains capability and provider dependent." ]},
        ]
        presets.extend(
            {
                "name": name,
                "purpose": purpose,
                "management_model": model,
                "responsibility_model": responsibility,
                "category": category,
                "team_size": size,
                "workflow_name": workflow,
                "roles": roles,
                "steps": steps,
                "source": source,
                "limitations": limitations,
            }
            for name, purpose, model, responsibility, category, size, workflow, roles, steps, source, limitations in [
                ("FLAT_TEAM", "Small team with minimal hierarchy.", "FLAT", "RESP-RACI", "Other", "MINI", "FLAT_TEAM_WORKFLOW", [{"position": "Owner", "role": "Owner"}, {"position": "Specialist A", "role": "Specialist"}, {"position": "Specialist B", "role": "Specialist"}, {"position": "Reviewer", "role": "Reviewer"}], [{"responsibility": "Specialist A", "operation": "CREATE", "expected_outputs": ["result"]}, {"responsibility": "Reviewer", "operation": "REVIEW", "expected_outputs": ["findings"]}], "General flat-team pattern.", ["Escalation needs an explicit owner."]),
                ("PROJECTIZED_TEAM", "Temporary team assembled around a project.", "PROJECTIZED", "RESP-RACI", "Development", "STANDARD", "PROJECTIZED_WORKFLOW", [{"position": "Project Manager", "role": "Project Manager"}, {"position": "Specialist A", "role": "Specialist"}, {"position": "Specialist B", "role": "Specialist"}, {"position": "QA", "role": "QA"}, {"position": "Documentation", "role": "Documentation"}], [{"responsibility": "Project Manager", "operation": "PLAN", "expected_outputs": ["plan"]}, {"responsibility": "Specialist A", "operation": "CREATE", "expected_outputs": ["artifact"]}, {"responsibility": "QA", "operation": "REVIEW", "expected_outputs": ["findings"]}], "General projectized pattern.", ["Long-term functional ownership must be defined."]),
                ("MATRIX_TEAM", "Team with functional and project responsibility relations.", "MATRIX", "RESP-RACI", "Development", "STANDARD", "MATRIX_WORKFLOW", [{"position": "Functional Manager", "role": "Manager"}, {"position": "Project Manager", "role": "Project Manager"}, {"position": "Engineer", "role": "Design Engineer"}, {"position": "Reviewer", "role": "Reviewer"}], [{"responsibility": "Project Manager", "operation": "PLAN", "expected_outputs": ["plan"]}, {"responsibility": "Engineer", "operation": "CREATE", "expected_outputs": ["artifact"]}, {"responsibility": "Reviewer", "operation": "REVIEW", "expected_outputs": ["findings"]}], "General matrix pattern; multiple relations are data, not GUI logic.", ["Conflicting direction requires RACI."]),
                ("CROSS_FUNCTIONAL_TEAM", "Cross-functional team that can deliver an outcome end to end.", "CROSS_FUNCTIONAL", "RESP-RACI", "Development", "STANDARD", "CROSS_FUNCTIONAL_WORKFLOW", [{"position": "Product Lead", "role": "Product Lead"}, {"position": "Developer", "role": "Developer"}, {"position": "Designer", "role": "Designer"}, {"position": "Researcher", "role": "Researcher"}, {"position": "QA", "role": "QA"}], [{"responsibility": "Product Lead", "operation": "PLAN", "expected_outputs": ["objective"]}, {"responsibility": "Developer", "operation": "CREATE", "expected_outputs": ["increment"]}, {"responsibility": "QA", "operation": "REVIEW", "expected_outputs": ["findings"]}], "General cross-functional pattern.", ["Requires clear decision authority."]),
                ("RACI_REVIEW_TEAM", "Creator, reviewer and accountable owner with explicit RACI.", "FUNCTIONAL", "RESP-RACI", "Documents", "MINI", "CRA_WORKFLOW", [{"position": "Creator", "role": "Creator"}, {"position": "Reviewer", "role": "Reviewer"}, {"position": "Approver", "role": "Approver"}], [{"responsibility": "Creator", "operation": "CREATE", "expected_outputs": ["artifact"]}, {"responsibility": "Reviewer", "operation": "REVIEW", "expected_outputs": ["findings"]}, {"responsibility": "Approver", "operation": "APPROVE", "expected_outputs": ["decision"]}], "Generic RACI/CRA quality preset.", ["Informed participants are not required to answer."]),
                ("KANBAN_PRODUCT_TEAM", "Existing team with a Kanban flow overlay.", "CROSS_FUNCTIONAL", "RESP-KANBAN", "Development", "STANDARD", "KANBAN_PRODUCT_WORKFLOW", common_roles, [{"responsibility": "Project Manager", "operation": "PULL", "expected_outputs": ["ready item"]}, {"responsibility": "Developer", "operation": "IN_PROGRESS", "expected_outputs": ["artifact"]}, {"responsibility": "Reviewer", "operation": "REVIEW", "expected_outputs": ["decision"]}], "Kanban is a workflow overlay, not a hierarchy.", ["WIP limits must be configured for the project."]),
            ]
        )
        return presets

    def _role_in_variant(self, role: dict[str, Any], team_size: str) -> bool:
        variants = role.get("team_size_variants")
        return not variants or team_size in variants or team_size.upper() in {str(item).upper() for item in variants}

    def _ensure_role_profile(self, role: dict[str, Any]) -> str:
        raw = str(role.get("role_id") or role.get("role") or role.get("position") or "CUSTOM_ROLE").strip()
        normalized = raw.upper().replace(" ", "_").replace("/", "_").replace("-", "_")
        aliases = {
            "PROJECT_MANAGER": "PROJECT_MANAGER", "PROJECT_LEAD": "PROJECT_MANAGER", "PRODUCT_MANAGER": "PROJECT_MANAGER", "PRODUCT_OWNER": "PROJECT_MANAGER",
            "DEVELOPER": "DESIGN_ENGINEER", "SOFTWARE_ENGINEER": "DESIGN_ENGINEER", "DESIGN_ENGINEER": "DESIGN_ENGINEER", "ARCHITECT": "DESIGN_ENGINEER",
            "QA": "QA_ENGINEER", "REVIEWER": "QA_ENGINEER", "TECHNICAL_REVIEWER": "QA_ENGINEER", "CRITICAL_REVIEWER": "QA_ENGINEER",
            "DOCUMENTATION": "DOCUMENT_CONTROL_OFFICER", "DOCUMENT_CONTROLLER": "DOCUMENT_CONTROL_OFFICER",
            "RESEARCHER": "RESEARCH_ASSISTANT", "SOURCE_RESEARCHER": "RESEARCH_ASSISTANT",
            "LEARNING_COORDINATOR": "LEARNING_COORDINATOR",
        }
        role_id = aliases.get(normalized, normalized if normalized in ROLE_DEFAULT_PERMISSIONS else f"CUSTOM_{re.sub(r'[^A-Z0-9_]', '_', normalized)[:36]}")
        if not any(str(row["role_id"]) == role_id for row in self.database.list_role_profiles()):
            self.database.upsert_role_profile(RoleProfile(role_id, raw, str(role.get("description") or "Роль организации"), [str(item) for item in role.get("responsibilities", [])], [], "1.0"))
        return role_id

    def _create_operational_employee(self, position: str, role_id: str, provider: str, role: dict[str, Any]) -> str:
        if self.management_service is not None and hasattr(self.management_service, "generate_agent_id"):
            agent_id = self.management_service.generate_agent_id(position)
        else:
            agent_id = f"agent-{re.sub(r'[^a-z0-9]+', '-', position.lower()).strip('-') or 'employee'}-{uuid.uuid4().hex[:6]}"
        permissions = set(ROLE_DEFAULT_PERMISSIONS.get(role_id, {"CHAT"})) | {"CHAT"}
        profile = AgentProfile(agent_id, position, str(role.get("description") or f"Сотрудник организации: {position}"), "ACTIVE", provider, str(role.get("persona_id") or ""), None, ())
        self.database.create_agent_profile_with_assignments(profile, [role_id], sorted(permissions), "ORGANIZATION_OWNER", "organization activation")
        return agent_id

    def _profession_id_for_role(self, role: dict[str, Any]) -> str | None:
        wanted = str(role.get("profession") or "").strip().lower()
        if not wanted:
            return None
        for item in self.list_professions():
            if item.name.lower() == wanted:
                return item.profession_id
        return None

    def _ensure_fixture_workflow(self, name: str, steps: list[dict[str, Any]]) -> WorkflowDefinition:
        existing = next((row for row in self.database.list_workflows() if str(row["name"]) == name), None)
        if existing is not None:
            return self._workflow(existing)
        return self.create_workflow(name, steps, "Generic deterministic demonstration workflow")

    @staticmethod
    def _json_list(value: Any) -> list[Any]:
        try:
            result = json.loads(value or "[]") if isinstance(value, str) else value
            return result if isinstance(result, list) else []
        except (TypeError, ValueError):
            return []

    @staticmethod
    def _json_value(value: Any) -> Any:
        try:
            return json.loads(value or "{}") if isinstance(value, str) else value
        except (TypeError, ValueError):
            return {}

    @classmethod
    def _profession(cls, row: Any) -> Profession:
        return Profession(str(row["id"]), str(row["name"]), str(row["description"] or ""), tuple(map(str, cls._json_list(row["responsibilities"]))), tuple(map(str, cls._json_list(row["typical_results"]))), tuple(map(str, cls._json_list(row["required_capabilities"]))), tuple(map(str, cls._json_list(row["initial_skills"]))), tuple(map(str, cls._json_list(row["recommended_tools"]))), tuple(map(str, cls._json_list(row["knowledge_sources"]))), str(row["qualification_method"] or ""), str(row["status"]))

    @staticmethod
    def _organization(row: Any) -> Organization:
        return Organization(
            str(row["id"]), str(row["name"]), str(row["purpose"] or ""), str(row["description"] or ""), str(row["status"]),
            str(row["management_model_id"]) if "management_model_id" in row.keys() and row["management_model_id"] else None,
            str(row["domain_package"] or "") if "domain_package" in row.keys() else "",
            str(row["responsibility_model_id"]) if "responsibility_model_id" in row.keys() and row["responsibility_model_id"] else None,
        )

    @classmethod
    def _template(cls, row: Any) -> OrganizationTemplate:
        roles = cls._json_list(row["roles"])
        return OrganizationTemplate(
            str(row["id"]), str(row["name"]), str(row["purpose"] or ""), str(row["recommended_team_size"] or ""),
            tuple(item for item in roles if isinstance(item, dict)), str(row["workflow_id"]) if row["workflow_id"] else None,
            str(row["version"]), str(row["source_rationale"] or ""), tuple(map(str, cls._json_list(row["limitations"]))),
            str(row["management_model_id"]) if "management_model_id" in row.keys() and row["management_model_id"] else None,
            str(row["domain_package"] or "") if "domain_package" in row.keys() else "",
            str(row["responsibility_model_id"]) if "responsibility_model_id" in row.keys() and row["responsibility_model_id"] else None,
            str(row["catalog_category"] or "Other") if "catalog_category" in row.keys() else "Other",
            bool(row["review_required"]) if "review_required" in row.keys() else False,
            bool(row["research_required"]) if "research_required" in row.keys() else False,
            bool(row["learning_support"]) if "learning_support" in row.keys() else False,
        )

    @classmethod
    def _management_model(cls, row: Any) -> ManagementModel:
        return ManagementModel(
            str(row["id"]), str(row["name"]), str(row["description"] or ""), str(row["category"] or ""),
            str(row["structure_type"] or ""), str(row["decision_model"] or ""), str(row["responsibility_model"] or ""),
            str(row["workflow_style"] or ""), str(row["recommended_team_size"] or ""),
            tuple(map(str, cls._json_list(row["advantages"]))), tuple(map(str, cls._json_list(row["limitations"]))),
            str(row["source_rationale"] or ""),
        )

    def _workflow(self, row: Any) -> WorkflowDefinition:
        with self.database.connect() as conn:
            steps = conn.execute("SELECT * FROM workflow_steps WHERE workflow_id = ? ORDER BY step_order ASC", (row["id"],)).fetchall()
        return WorkflowDefinition(str(row["id"]), str(row["name"]), str(row["version"]), str(row["description"] or ""), tuple(dict(step) for step in steps))
