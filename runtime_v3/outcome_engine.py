from __future__ import annotations

from dataclasses import dataclass

from .models import Goal, OutcomeCriterion, RuntimeState, WorkReceipt, new_id


@dataclass(frozen=True)
class OutcomeEvaluation:
    passed: bool
    artifact_ids: list[str]
    evidence_ids: list[str]
    missing_criteria: list[str]


class OutcomeEngine:
    """Derives and verifies completion from durable runtime records only."""

    def derive_definition_of_done(self, goal: Goal) -> list[OutcomeCriterion]:
        text = goal.objective.lower()
        if any(token in text for token in ("one file", "single file", "один файл", "простая заметка")):
            return [
                OutcomeCriterion(new_id("dod"), "Создан проверяемый рабочий файл", "WORK_PRODUCT", "TOOL_OBSERVATION"),
            ]
        if any(token in text for token in ("исслед", "research", "подбер", "controller", "контроллер")):
            subject = "исследования и обоснованного выбора"
        elif any(token in text for token in ("специфик", "документ", "тз", "specification")):
            subject = "технической спецификации"
        else:
            subject = "рабочего результата"
        return [
            OutcomeCriterion(new_id("dod"), f"Создан проверяемый артефакт {subject}", "WORK_PRODUCT", "TOOL_OBSERVATION"),
            OutcomeCriterion(new_id("dod"), "Исследование содержит подтвержденные источники", "SOURCE_RESEARCH", "SOURCE_RECORD"),
            OutcomeCriterion(new_id("dod"), "Независимая проверка артефактов завершена без открытых замечаний", "", "REVIEW_RECORD"),
        ]

    def evaluate(self, state: RuntimeState, goal: Goal) -> OutcomeEvaluation:
        artifact_ids: list[str] = []
        evidence_ids: list[str] = []
        missing: list[str] = []
        goal_artifacts = [artifact for artifact in state.artifacts.values() if artifact.goal_id == goal.goal_id]
        goal_evidence = [evidence for evidence in state.evidence.values() if evidence.goal_id == goal.goal_id and evidence.passed]
        for criterion in goal.definition_of_done:
            artifacts = [artifact for artifact in goal_artifacts if artifact.artifact_type == criterion.required_artifact_type] if criterion.required_artifact_type else []
            evidence = [item for item in goal_evidence if item.evidence_type == criterion.required_evidence_type]
            valid_artifacts = [artifact for artifact in artifacts if self._artifact_has_observation(state, artifact.artifact_id)]
            if (criterion.required_artifact_type and not valid_artifacts) or (criterion.required_evidence_type and not evidence):
                missing.append(criterion.description)
                continue
            artifact_ids.extend(artifact.artifact_id for artifact in valid_artifacts)
            evidence_ids.extend(item.evidence_id for item in evidence)
        return OutcomeEvaluation(
            not missing,
            list(dict.fromkeys(artifact_ids)),
            list(dict.fromkeys(evidence_ids)),
            missing,
        )

    def issue_receipt(self, state: RuntimeState, goal: Goal) -> WorkReceipt | None:
        evaluation = self.evaluate(state, goal)
        if not evaluation.passed:
            return None
        if goal.work_receipt_id and goal.work_receipt_id in state.work_receipts:
            return state.work_receipts[goal.work_receipt_id]
        receipt = WorkReceipt(
            new_id("receipt"), goal.goal_id,
            [criterion.criterion_id for criterion in goal.definition_of_done],
            evaluation.artifact_ids, evaluation.evidence_ids,
        )
        state.work_receipts[receipt.receipt_id] = receipt
        goal.work_receipt_id = receipt.receipt_id
        return receipt

    @staticmethod
    def _artifact_has_observation(state: RuntimeState, artifact_id: str) -> bool:
        artifact = state.artifacts[artifact_id]
        observation = state.observations.get(artifact.created_from_observation_id)
        return observation is not None and observation.status.value == "OK"
