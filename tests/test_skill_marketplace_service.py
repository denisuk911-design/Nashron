from pathlib import Path

from core.database import Database
from core.skill_marketplace_service import SkillMarketplaceService, SkillPackManifest
from core.skill_package_service import SkillPackageService


def _database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    with database.connect() as conn:
        conn.execute("INSERT INTO organizations (id, name, purpose, status) VALUES ('org-a', 'A', '', 'ACTIVE')")
        conn.execute("INSERT INTO organizations (id, name, purpose, status) VALUES ('org-b', 'B', '', 'ACTIVE')")
    return database


def _manifest(version: str = "1.0.0") -> SkillPackManifest:
    return SkillPackManifest(
        name="PCB review", purpose="Review production PCB evidence.", procedures="Read evidence before review.",
        references=("IPC-2221",), checklists=("ERC reviewed",), tools=("workspace.read",),
        tests=("Review a known defect",), acceptance=("No open high findings",),
        examples=("Known good review",), failure_patterns=("Prompt-only claim",),
        supported_roles=("QA_ENGINEER",), version=version,
    )


def test_skill_pack_requires_qualification_before_activation_and_drives_assignment_and_dod(tmp_path):
    database = _database(tmp_path)
    packages = SkillPackageService(database)
    marketplace = SkillMarketplaceService(packages)
    skill_id = marketplace.install("org-a", _manifest())

    package = packages.list_packages("org-a")[0]
    assert package.test_cases == ["Review a known defect"]
    assert package.failure_patterns == ["Prompt-only claim"]
    try:
        marketplace.activate(skill_id, "org-a")
    except ValueError as exc:
        assert "reviewed" in str(exc)
    else:
        raise AssertionError("draft skill pack activated")

    packages.update_status(skill_id, "VERIFIED", actor="reviewer", reason="evidence:review_run:RUN-1", organization_id="org-a")
    try:
        packages.assign_to_employee("agent-reviewer", skill_id, state="QUALIFIED", actor="owner", reason="chat claim")
    except ValueError as exc:
        assert "review evidence" in str(exc)
    else:
        raise AssertionError("chat-only qualification was accepted")
    packages.assign_to_employee("agent-reviewer", skill_id, state="QUALIFIED", actor="reviewer", reason="review_run:RUN-1")
    marketplace.activate(skill_id, "org-a")

    assert marketplace.qualified_candidates(skill_id, "org-a") == ["agent-reviewer"]
    assert marketplace.definition_of_done(skill_id, "org-a") == [
        "ERC reviewed", "Review a known defect", "No open high findings",
    ]
    assert packages.list_packages("org-a")[0].status == "ACTIVE"

    reopened = SkillMarketplaceService(SkillPackageService(Database(database.path)))
    assert reopened.qualified_candidates(skill_id, "org-a") == ["agent-reviewer"]
    try:
        reopened.qualified_candidates(skill_id, "org-b")
    except ValueError as exc:
        assert "outside" in str(exc)
    else:
        raise AssertionError("organization isolation was bypassed")


def test_skill_pack_versioning_uninstall_and_manifest_completeness(tmp_path):
    database = _database(tmp_path)
    marketplace = SkillMarketplaceService(SkillPackageService(database))
    skill_id = marketplace.install("org-a", _manifest())
    marketplace.version(skill_id, "org-a", "1.1.0")

    package = next(item for item in marketplace.packages.list_packages("org-a") if item.skill_id == skill_id)
    assert package.version == "1.1.0"
    assert marketplace.uninstall(skill_id, "org-a") is True
    assert marketplace.packages.list_packages("org-a") == []

    incomplete = SkillPackManifest("Bad", "", "", (), (), (), (), (), (), ())
    try:
        marketplace.install("org-a", incomplete)
    except ValueError as exc:
        assert "incomplete" in str(exc)
    else:
        raise AssertionError("incomplete prompt-like pack was installed")
