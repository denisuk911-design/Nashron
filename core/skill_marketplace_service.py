from __future__ import annotations

from dataclasses import dataclass

from .skill_package_service import EmployeeSkillAssignment, SkillPackage, SkillPackageService


@dataclass(frozen=True)
class SkillPackManifest:
    name: str
    purpose: str
    procedures: str
    references: tuple[str, ...]
    checklists: tuple[str, ...]
    tools: tuple[str, ...]
    tests: tuple[str, ...]
    acceptance: tuple[str, ...]
    examples: tuple[str, ...]
    failure_patterns: tuple[str, ...]
    supported_roles: tuple[str, ...] = ()
    version: str = "1.0.0"


class SkillMarketplaceService:
    """Organization-scoped installable skill packs, never prompt-only skills."""

    def __init__(self, packages: SkillPackageService) -> None:
        self.packages = packages

    def install(self, organization_id: str, manifest: SkillPackManifest, *, actor: str = "owner") -> str:
        self._validate(manifest)
        return self.packages.create_package(
            name=manifest.name, purpose=manifest.purpose, supported_roles=list(manifest.supported_roles),
            source_material=list(manifest.references), instructions=manifest.procedures,
            tools=list(manifest.tools), expected_outputs="; ".join(manifest.acceptance),
            validation_checklist=list(manifest.checklists), examples=list(manifest.examples),
            negative_examples=list(manifest.failure_patterns), qualification_tasks=list(manifest.tests),
            test_cases=list(manifest.tests), failure_patterns=list(manifest.failure_patterns),
            version=manifest.version, status="DRAFT", actor=actor, organization_id=organization_id,
        )

    def activate(self, skill_id: str, organization_id: str, *, actor: str = "owner") -> None:
        package = self._package(skill_id, organization_id)
        if package.status not in {"VERIFIED", "MATURE"}:
            raise ValueError("skill activation requires a reviewed and verified pack")
        self.packages.update_status(skill_id, "ACTIVE", actor=actor, organization_id=organization_id)

    def uninstall(self, skill_id: str, organization_id: str, *, actor: str = "owner") -> bool:
        return self.packages.uninstall_package(skill_id, organization_id, actor=actor)

    def version(self, skill_id: str, organization_id: str, version: str, *, actor: str = "owner") -> None:
        self._package(skill_id, organization_id)
        self.packages.set_version(skill_id, version, actor=actor, organization_id=organization_id)

    def qualified_candidates(self, skill_id: str, organization_id: str) -> list[str]:
        self._package(skill_id, organization_id)
        return [item.agent_id for item in self.packages.list_assignments() if item.skill_id == skill_id and item.state == "QUALIFIED"]

    def definition_of_done(self, skill_id: str, organization_id: str) -> list[str]:
        package = self._package(skill_id, organization_id)
        return list(dict.fromkeys([*package.validation_checklist, *package.test_cases, package.expected_outputs]))

    def _package(self, skill_id: str, organization_id: str) -> SkillPackage:
        package = next((item for item in self.packages.list_packages(organization_id) if item.skill_id == skill_id), None)
        if package is None or self.packages.database.get_skill_package(skill_id)["organization_id"] != organization_id:
            raise ValueError("skill pack is outside this organization")
        return package

    @staticmethod
    def _validate(manifest: SkillPackManifest) -> None:
        required = {
            "name": manifest.name, "purpose": manifest.purpose, "procedures": manifest.procedures,
            "references": manifest.references, "checklists": manifest.checklists, "tools": manifest.tools,
            "tests": manifest.tests, "acceptance": manifest.acceptance, "examples": manifest.examples,
            "failure_patterns": manifest.failure_patterns,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError("skill pack is incomplete: " + ", ".join(missing))
