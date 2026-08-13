from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class ProficiencyLevel(StrEnum):
    LEARNING = "LEARNING"
    PRACTICED = "PRACTICED"
    VALIDATED = "VALIDATED"
    PROFICIENT = "PROFICIENT"
    EXPERT = "EXPERT"


@dataclass(frozen=True)
class SkillEvidence:
    studies: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    passed_tests: int = 0
    independent_validations: int = 0
    repeated_uses: int = 0


def evidence_level(evidence: SkillEvidence) -> ProficiencyLevel:
    if evidence.independent_validations >= 5 and evidence.successful_tasks >= 20 and evidence.passed_tests >= 10:
        return ProficiencyLevel.EXPERT
    if evidence.independent_validations >= 3 and evidence.successful_tasks >= 10 and evidence.passed_tests >= 5:
        return ProficiencyLevel.PROFICIENT
    if evidence.independent_validations >= 1 and evidence.successful_tasks >= 3 and evidence.passed_tests >= 1:
        return ProficiencyLevel.VALIDATED
    if evidence.successful_tasks >= 1 or evidence.repeated_uses >= 2:
        return ProficiencyLevel.PRACTICED
    return ProficiencyLevel.LEARNING


class SkillPackageValidator:
    REQUIRED_METADATA = {
        "skill_id",
        "name",
        "version",
        "domain",
        "description",
        "owner",
        "compatibility",
    }

    def validate(self, root: Path) -> list[str]:
        errors: list[str] = []
        root = Path(root)
        for relative in ("SKILL.md", "metadata.json", "sources", "examples", "tests", "history"):
            if not (root / relative).exists():
                errors.append(f"missing:{relative}")
        metadata_path = root / "metadata.json"
        if metadata_path.exists():
            try:
                data: dict[str, Any] = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                errors.append("invalid:metadata.json")
            else:
                for field in sorted(self.REQUIRED_METADATA - data.keys()):
                    errors.append(f"metadata_missing:{field}")
        return errors
