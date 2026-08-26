from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Protocol

from core.provider_execution import ProviderExecutionAdapter, ProviderExecutionRequest, ProviderExecutionResult

from .models import Action, ActionType, ProviderRun, WorkItem, new_id, utc_now


@dataclass
class AgentDecision:
    message: str = ""
    actions: list[Action] = field(default_factory=list)
    claim_completed: bool = False
    failure_kind: str = ""
    provider_run: ProviderRun | None = None
    provider_runs: list[ProviderRun] = field(default_factory=list)
    hitl_request: dict[str, object] | None = None


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
                "Source evidence: TI LM5146 datasheet, https://www.ti.com/lit/ds/symlink/lm5146.pdf.\n"
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
    """Executes assigned production work through provider adapters with local retry fallback."""

    def __init__(
        self,
        providers: dict[str, ProviderExecutionAdapter],
        employee_provider_ids: dict[str, str],
        fallback_provider_ids: dict[str, list[str]] | None = None,
        fallback: DeterministicAgentRuntime | None = None,
    ) -> None:
        self.providers = dict(providers)
        self.employee_provider_ids = dict(employee_provider_ids)
        self.fallback_provider_ids = {key: list(value) for key, value in (fallback_provider_ids or {}).items()}
        self.fallback = fallback or DeterministicAgentRuntime()
        self.provider_work_item_ids: set[str] = set()

    def restore_completed_work_items(self, work_item_ids: set[str]) -> None:
        """Restore idempotency markers from durable runtime state after restart."""
        self.provider_work_item_ids.update(work_item_ids)

    def decide(self, employee_id: str, work_item: WorkItem, attempt: int) -> AgentDecision:
        primary_provider_id = self.employee_provider_ids.get(employee_id, "")
        if not primary_provider_id or work_item.work_item_id in self.provider_work_item_ids:
            return self.fallback.decide(employee_id, work_item, attempt)

        provider_ids = [primary_provider_id, *self.fallback_provider_ids.get(employee_id, [])]
        runs: list[ProviderRun] = []
        for provider_id in dict.fromkeys(provider_ids):
            provider = self.providers.get(provider_id)
            if provider is None:
                continue
            request = ProviderExecutionRequest(new_id("provider-run"), employee_id, provider_id, work_item.work_item_id, self._prompt_for(work_item), utc_now())
            try:
                result = provider.execute(request)
            except Exception as exc:
                result = ProviderExecutionResult(
                    request.run_id,
                    employee_id,
                    provider_id,
                    work_item.work_item_id,
                    "FAILED",
                    request.started_at,
                    utc_now(),
                    error=f"{type(exc).__name__}: {exc}",
                )
            provider_run = ProviderRun(result.run_id, result.employee_id, result.provider_id, result.work_item_id, result.status, result.started_at, result.finished_at, result.error)
            runs.append(provider_run)
            if result.status == "SUCCEEDED":
                self.provider_work_item_ids.add(work_item.work_item_id)
                decision = self._parse_action(work_item, employee_id, result.content, provider_run)
                decision.provider_runs = runs
                return decision
        detail = runs[-1].error if runs else "no provider adapter is available"
        return AgentDecision(message=detail or "provider failure", failure_kind="PROVIDER_FAILURE", provider_run=runs[-1] if runs else None, provider_runs=runs)

    @staticmethod
    def _prompt_for(work_item: WorkItem) -> str:
        output_path = f"v3_provider_output/{work_item.work_item_id}.md"
        return "\n".join(
            [
                "You are an execution adapter inside Team2050 Runtime V3.",
                "Return exactly one JSON object. No Markdown, no prose, no tool calls.",
                "The only accepted action is filesystem.write.",
                f"Write only to this relative path: {output_path}",
                "Write a concise factual work product satisfying the objective.",
                "For a technical specification, include the word controller.",
                "For controller research, include a 'Source evidence' section with an authoritative source URL.",
                f'{{"action":"filesystem.write","path":"{output_path}","content":"..."}}',
                f"Objective: {work_item.objective}",
                f"Acceptance criteria: {', '.join(work_item.acceptance_criteria) or 'artifact created'}",
            ]
        )

    @staticmethod
    def _parse_action(work_item: WorkItem, employee_id: str, content: str, provider_run: ProviderRun) -> AgentDecision:
        try:
            payload = json.loads(content.strip())
        except json.JSONDecodeError:
            return AgentDecision(message="provider response is not valid JSON", failure_kind="PROVIDER_INVALID_ACTION", provider_run=provider_run)
        if not isinstance(payload, dict) or payload.get("action") != ActionType.FILESYSTEM_WRITE.value:
            return AgentDecision(message="provider proposed an unsupported action", failure_kind="PROVIDER_INVALID_ACTION", provider_run=provider_run)
        path = str(payload.get("path") or "").replace("\\", "/").strip()
        artifact_content = str(payload.get("content") or "").strip()
        if not path.startswith("v3_provider_output/") or not path.endswith(".md") or not artifact_content:
            return AgentDecision(message="provider action failed validation", failure_kind="PROVIDER_INVALID_ACTION", provider_run=provider_run)
        provider_run.action_count = 1
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
            provider_run=provider_run,
        )
