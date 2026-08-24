from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Protocol

from .models import Action, ActionType, WorkItem, new_id


@dataclass
class AgentDecision:
    message: str = ""
    actions: list[Action] = field(default_factory=list)
    claim_completed: bool = False
    failure_kind: str = ""


class ProviderClient(Protocol):
    def generate(self, prompt: str, allow_full_access: bool = False):
        ...


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


class ProviderAgentRuntime:
    """Uses one real provider-backed work item and delegates the rest to fallback."""

    def __init__(
        self,
        providers: dict[str, ProviderClient],
        employee_provider_ids: dict[str, str],
        fallback: DeterministicAgentRuntime | None = None,
    ) -> None:
        self.providers = dict(providers)
        self.employee_provider_ids = dict(employee_provider_ids)
        self.fallback = fallback or DeterministicAgentRuntime()
        self.provider_work_item_ids: set[str] = set()

    def decide(self, employee_id: str, work_item: WorkItem, attempt: int) -> AgentDecision:
        provider_id = self.employee_provider_ids.get(employee_id, "")
        provider = self.providers.get(provider_id)
        if provider is None or work_item.work_item_id in self.provider_work_item_ids:
            return self.fallback.decide(employee_id, work_item, attempt)

        self.provider_work_item_ids.add(work_item.work_item_id)
        result = provider.generate(self._prompt_for(work_item), allow_full_access=False)
        if not getattr(result, "ok", False):
            detail = str(getattr(result, "error", "provider returned no usable result")).strip()
            return AgentDecision(message=detail or "provider failure", failure_kind="PROVIDER_FAILURE")
        return self._parse_action(work_item, employee_id, str(getattr(result, "content", "")))

    @staticmethod
    def _prompt_for(work_item: WorkItem) -> str:
        return "\n".join(
            [
                "You are an execution adapter inside Team2050 Runtime V3.",
                "Return exactly one JSON object. No Markdown, no prose, no tool calls.",
                "The only accepted action is filesystem.write.",
                "Use a relative .md path under v3_provider_output/.",
                "Write a concise factual work product satisfying the objective.",
                "For a technical specification, include the word controller.",
                '{"action":"filesystem.write","path":"v3_provider_output/result.md","content":"..."}',
                f"Objective: {work_item.objective}",
                f"Acceptance criteria: {', '.join(work_item.acceptance_criteria) or 'artifact created'}",
            ]
        )

    @staticmethod
    def _parse_action(work_item: WorkItem, employee_id: str, content: str) -> AgentDecision:
        try:
            payload = json.loads(content.strip())
        except json.JSONDecodeError:
            return AgentDecision(message="provider response is not valid JSON", failure_kind="PROVIDER_INVALID_ACTION")
        if not isinstance(payload, dict) or payload.get("action") != ActionType.FILESYSTEM_WRITE.value:
            return AgentDecision(message="provider proposed an unsupported action", failure_kind="PROVIDER_INVALID_ACTION")
        path = str(payload.get("path") or "").replace("\\", "/").strip()
        artifact_content = str(payload.get("content") or "").strip()
        if not path.startswith("v3_provider_output/") or not path.endswith(".md") or not artifact_content:
            return AgentDecision(message="provider action failed validation", failure_kind="PROVIDER_INVALID_ACTION")
        return AgentDecision(
            message="provider action accepted",
            actions=[
                Action(
                    new_id("action"),
                    work_item.work_item_id,
                    employee_id,
                    ActionType.FILESYSTEM_WRITE,
                    {"path": path, "content": artifact_content},
                )
            ],
        )
