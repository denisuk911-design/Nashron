from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .database import Database


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

    def __init__(self, database: Database) -> None:
        self.database = database

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

    def create_organization(self, name: str, purpose: str = "", description: str = "") -> Organization:
        name = name.strip()
        if not name:
            raise ValueError("organization_name_required")
        organization_id = self.database.create_organization({"name": name, "purpose": purpose.strip(), "description": description.strip()})
        row = next(row for row in self.database.list_organizations() if str(row["id"]) == organization_id)
        return self._organization(row)

    def list_organizations(self) -> list[Organization]:
        return [self._organization(row) for row in self.database.list_organizations()]

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

    def seed_demo_fixtures(self) -> dict[str, str]:
        """Create two domain fixtures using the same generic core."""
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

    @classmethod
    def _profession(cls, row: Any) -> Profession:
        return Profession(str(row["id"]), str(row["name"]), str(row["description"] or ""), tuple(map(str, cls._json_list(row["responsibilities"]))), tuple(map(str, cls._json_list(row["typical_results"]))), tuple(map(str, cls._json_list(row["required_capabilities"]))), tuple(map(str, cls._json_list(row["initial_skills"]))), tuple(map(str, cls._json_list(row["recommended_tools"]))), tuple(map(str, cls._json_list(row["knowledge_sources"]))), str(row["qualification_method"] or ""), str(row["status"]))

    @staticmethod
    def _organization(row: Any) -> Organization:
        return Organization(str(row["id"]), str(row["name"]), str(row["purpose"] or ""), str(row["description"] or ""), str(row["status"]))

    @classmethod
    def _template(cls, row: Any) -> OrganizationTemplate:
        roles = cls._json_list(row["roles"])
        return OrganizationTemplate(str(row["id"]), str(row["name"]), str(row["purpose"] or ""), str(row["recommended_team_size"] or ""), tuple(item for item in roles if isinstance(item, dict)), str(row["workflow_id"]) if row["workflow_id"] else None, str(row["version"]), str(row["source_rationale"] or ""), tuple(map(str, cls._json_list(row["limitations"]))))

    def _workflow(self, row: Any) -> WorkflowDefinition:
        with self.database.connect() as conn:
            steps = conn.execute("SELECT * FROM workflow_steps WHERE workflow_id = ? ORDER BY step_order ASC", (row["id"],)).fetchall()
        return WorkflowDefinition(str(row["id"]), str(row["name"]), str(row["version"]), str(row["description"] or ""), tuple(dict(step) for step in steps))
