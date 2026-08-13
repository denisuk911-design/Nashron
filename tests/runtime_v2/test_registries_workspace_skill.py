import json

import pytest

from runtime_v2.models import ActionRisk, FindingStatus
from runtime_v2.registries import StateFindingRegistry
from runtime_v2.skill_package import ProficiencyLevel, SkillEvidence, SkillPackageValidator, evidence_level
from runtime_v2.workspace import WorkspacePolicy


def test_artifact_revision_and_finding_lifecycle(engine_factory):
    from runtime_v2.models import WorkflowDefinition, WorkflowStep

    engine, _, _ = engine_factory()
    state = engine.create_workflow("org", "Create", WorkflowDefinition("one", [WorkflowStep("a", "e", "CREATE", "DOC")]))
    state = engine.run_until_blocked(state.workflow_id)
    artifact_id = state.steps["a"].output_artifacts[0]
    engine.artifacts.add_revision(
        state,
        {"artifact_id": artifact_id, "artifact_type": "DOC", "content": "v2", "evidence": {"test": "passed"}},
        employee_id="e",
        provider_id="provider-b",
    )
    assert state.artifacts[artifact_id].current_revision == 2
    finding_id = engine.findings.add(
        state,
        {
            "artifact_id": artifact_id,
            "revision": 2,
            "description": "Incorrect section",
            "evidence": {"line": 4},
            "owner_employee_id": "e",
        },
    )
    for target in (FindingStatus.ASSIGNED, FindingStatus.RESOLVED, FindingStatus.CLOSED):
        engine.findings.transition(state, finding_id, target)
    assert state.findings[finding_id].status == FindingStatus.CLOSED


def test_workspace_is_scoped_and_dangerous_actions_require_approval(tmp_path):
    policy = WorkspacePolicy(tmp_path)
    target = policy.resolve_in_task("org", "project", "task", "docs/result.md")
    assert str(target).endswith("organizations\\org\\projects\\project\\tasks\\task\\docs\\result.md")
    with pytest.raises(PermissionError):
        policy.resolve_in_task("org", "project", "task", "../../outside.txt")
    assert policy.requires_owner_approval(ActionRisk.DELETE)
    assert not policy.requires_owner_approval(ActionRisk.READ)


def test_skill_package_and_evidence_levels(tmp_path):
    root = tmp_path / "skill"
    root.mkdir()
    (root / "SKILL.md").write_text("# PCB review", encoding="utf-8")
    (root / "metadata.json").write_text(
        json.dumps(
            {
                "skill_id": "pcb-review",
                "name": "PCB review",
                "version": "1.0.0",
                "domain": "hardware",
                "description": "Checks PCB evidence",
                "owner": "team2050",
                "compatibility": ["desktop"],
            }
        ),
        encoding="utf-8",
    )
    for directory in ("sources", "examples", "tests", "history"):
        (root / directory).mkdir()
    assert SkillPackageValidator().validate(root) == []
    assert evidence_level(SkillEvidence(studies=3)) == ProficiencyLevel.LEARNING
    assert evidence_level(SkillEvidence(successful_tasks=3, passed_tests=1, independent_validations=1)) == ProficiencyLevel.VALIDATED
    assert evidence_level(SkillEvidence(successful_tasks=20, passed_tests=10, independent_validations=5)) == ProficiencyLevel.EXPERT


def test_structured_finding_rework_creates_revision_without_repeating_unaffected_branch(engine_factory):
    from runtime_v2.benchmark import expense_app_definition
    from runtime_v2.models import FindingStatus, WorkflowStatus

    engine, _, _ = engine_factory()
    state = engine.create_workflow("org", "Expense app", expense_app_definition())
    state = engine.run_until_blocked(state.workflow_id)
    artifact_id = state.steps["technical"].output_artifacts[0]
    state = engine.request_rework(
        state.workflow_id,
        artifact_id=artifact_id,
        responsible_step_id="technical",
        reviewer_step_id="review",
        description="Offline storage is not specified",
        evidence={"requirement": "offline"},
    )
    state = engine.run_until_blocked(state.workflow_id)
    assert state.status == WorkflowStatus.WAITING_FOR_OWNER
    assert state.steps["product"].attempts == 1
    assert state.steps["technical"].attempts == 2
    assert state.artifacts[artifact_id].current_revision == 2
    assert {finding.status for finding in state.findings.values()} == {FindingStatus.CLOSED}
