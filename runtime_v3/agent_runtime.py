from __future__ import annotations

from dataclasses import dataclass, field

from .models import Action, ActionType, WorkItem, new_id


@dataclass
class AgentDecision:
    message: str = ""
    actions: list[Action] = field(default_factory=list)
    claim_completed: bool = False


class DeterministicAgentRuntime:
    """Provider-neutral local agent runtime for the first V3 vertical slice."""

    def decide(self, employee_id: str, work_item: WorkItem, attempt: int) -> AgentDecision:
        objective = work_item.objective.lower()
        if "fake claim" in objective:
            return AgentDecision("I created docs/fake.md", [], claim_completed=True)
        if "review" in objective:
            return AgentDecision(
                "Review artifact",
                [
                    Action(
                        new_id("action"),
                        work_item.work_item_id,
                        employee_id,
                        ActionType.REVIEW_ARTIFACT,
                        {"artifact_ids": work_item.input_artifact_ids},
                    )
                ],
            )
        filename = "artifacts/specification.md" if "specification" in objective else "artifacts/controller_research.md"
        content = self._content_for(work_item, attempt)
        return AgentDecision(
            f"Write {filename}",
            [
                Action(
                    new_id("action"),
                    work_item.work_item_id,
                    employee_id,
                    ActionType.FILESYSTEM_WRITE,
                    {"path": filename, "content": content},
                )
            ],
        )

    @staticmethod
    def _content_for(work_item: WorkItem, attempt: int) -> str:
        if "controller research" in work_item.objective.lower():
            return (
                "# Controller research\n\n"
                "Candidate: TI LM5146 buck controller.\n"
                "Input: 24 V. Output: 12 V 5 A.\n"
                "Source evidence: datasheet review placeholder for V3 prototype.\n"
            )
        if attempt == 0 and "force rework" in work_item.objective.lower():
            return "# Technical specification\n\n24 V to 12 V converter draft. Control section is missing.\n"
        return (
            "# Technical specification\n\n"
            "Input: 24 V DC.\n"
            "Output: 12 V DC, 5 A.\n"
            "Topology: synchronous buck.\n"
            "Controller requirement: documented and cross-checked.\n"
        )
