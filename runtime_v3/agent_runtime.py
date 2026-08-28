from __future__ import annotations

from dataclasses import dataclass, field
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
import json
import threading
from typing import Protocol

from core.provider_execution import (
    ContextWindowPolicy,
    ProviderCircuitBreaker,
    ProviderExecutionAdapter,
    ProviderExecutionRequest,
    ProviderExecutionResult,
    PROVIDER_ADAPTER_CONTRACT_VERSION,
    provider_adapter_handshake,
    redact_provider_text,
)

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
        filename = "artifacts/research.md" if "research" in objective else "artifacts/work_product.md"
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
        if "research" in work_item.objective.lower():
            return (
                f"# Research notes\n\nObjective: {work_item.objective}\n\n"
                "Source evidence: research requires an authoritative source before release.\n"
            )
        return (
            f"# Work product\n\nObjective: {work_item.objective}\n\n"
            "Result: a concise draft prepared for independent review.\n"
        )


class ProviderAgentRuntime:
    """Executes assigned production work through provider adapters with local retry fallback."""

    def __init__(
        self,
        providers: dict[str, ProviderExecutionAdapter],
        employee_provider_ids: dict[str, str],
        fallback_provider_ids: dict[str, list[str]] | None = None,
        fallback: DeterministicAgentRuntime | None = None,
        context_policy: ContextWindowPolicy | None = None,
        max_concurrent_runs: int = 4,
        provider_timeout_seconds: float = 45.0,
        circuit_breaker: ProviderCircuitBreaker | None = None,
        provider_contract_versions: dict[str, str] | None = None,
    ) -> None:
        self.providers = dict(providers)
        self.employee_provider_ids = dict(employee_provider_ids)
        self.fallback_provider_ids = {key: list(value) for key, value in (fallback_provider_ids or {}).items()}
        self.fallback = fallback or DeterministicAgentRuntime()
        self.context_policy = context_policy or ContextWindowPolicy()
        self._executor = ThreadPoolExecutor(max_workers=max(1, max_concurrent_runs), thread_name_prefix="team2050-provider")
        self._provider_executor = ThreadPoolExecutor(
            max_workers=max(1, max_concurrent_runs), thread_name_prefix="team2050-provider-call"
        )
        self.provider_timeout_seconds = max(0.1, float(provider_timeout_seconds))
        self._cancelled = threading.Event()
        self.circuit_breaker = circuit_breaker or ProviderCircuitBreaker()
        self.provider_contract_versions = dict(provider_contract_versions or {})
        self.provider_work_item_ids: set[str] = set()

    def restore_completed_work_items(self, work_item_ids: set[str]) -> None:
        """Restore idempotency markers from durable runtime state after restart."""
        self.provider_work_item_ids.update(work_item_ids)

    def submit(self, employee_id: str, work_item: WorkItem, attempt: int) -> Future[AgentDecision]:
        """Bounded async provider execution used by concurrent work graph nodes."""
        return self._executor.submit(self.decide, employee_id, work_item, attempt)

    def cancel_active_runs(self) -> None:
        self._cancelled.set()
        for provider in self.providers.values():
            cancel = getattr(provider, "cancel", None)
            if callable(cancel):
                cancel()

    def migrate_contract_snapshots(self, snapshots: dict[str, dict[str, object]]) -> None:
        """Upgrade compatible persisted contract metadata without touching work state."""
        for snapshot in snapshots.values():
            provider_id = str(snapshot.get("provider_binding_id") or "")
            provider = self.providers.get(provider_id)
            if provider is None:
                continue
            profile = getattr(provider, "capability_profile", None)
            handshake = provider_adapter_handshake(
                str(snapshot.get("provider_contract_version") or PROVIDER_ADAPTER_CONTRACT_VERSION),
                str(getattr(profile, "contract_version", PROVIDER_ADAPTER_CONTRACT_VERSION)),
            )
            snapshot["provider_contract_status"] = "COMPATIBLE" if handshake.compatible else "BLOCKED"
            if handshake.compatible:
                snapshot["provider_contract_version"] = handshake.adapter_version
                if handshake.migration_required:
                    snapshot["provider_contract_migrated_from"] = handshake.expected_version
            else:
                snapshot["provider_contract_reason"] = handshake.reason

    def decide(self, employee_id: str, work_item: WorkItem, attempt: int) -> AgentDecision:
        if self._cancelled.is_set():
            return AgentDecision(message="provider run cancelled", failure_kind="PROVIDER_CANCELLED")
        primary_provider_id = self.employee_provider_ids.get(employee_id, "")
        if not primary_provider_id or work_item.work_item_id in self.provider_work_item_ids:
            return self.fallback.decide(employee_id, work_item, attempt)

        provider_ids = [primary_provider_id, *self.fallback_provider_ids.get(employee_id, [])]
        required_capabilities = {"filesystem.write", "structured_output"}
        correlation_id = f"corr-{work_item.goal_id}-{work_item.work_item_id}"
        runs: list[ProviderRun] = []
        for provider_id in dict.fromkeys(provider_ids):
            if self._cancelled.is_set():
                return AgentDecision(message="provider run cancelled", failure_kind="PROVIDER_CANCELLED", provider_runs=runs)
            provider = self.providers.get(provider_id)
            if provider is None:
                continue
            if not self.circuit_breaker.allow(provider_id):
                runs.append(ProviderRun(
                    new_id("provider-run"), employee_id, provider_id, work_item.work_item_id,
                    "SKIPPED", utc_now(), utc_now(),
                    error="provider circuit is open", correlation_id=correlation_id,
                ))
                continue
            profile = getattr(provider, "capability_profile", None)
            handshake = provider_adapter_handshake(
                self.provider_contract_versions.get(provider_id, PROVIDER_ADAPTER_CONTRACT_VERSION),
                str(getattr(profile, "contract_version", PROVIDER_ADAPTER_CONTRACT_VERSION)),
            )
            if not handshake.compatible:
                runs.append(ProviderRun(
                    new_id("provider-run"), employee_id, provider_id, work_item.work_item_id,
                    "BLOCKED", utc_now(), utc_now(),
                    error=handshake.reason, correlation_id=correlation_id,
                ))
                continue
            if profile is not None and not profile.supports(required_capabilities):
                continue
            context = self.context_policy.apply(self._prompt_for(work_item))
            request = ProviderExecutionRequest(
                new_id("provider-run"), employee_id, provider_id, work_item.work_item_id,
                context.prompt, utc_now(), frozenset(required_capabilities), self._action_schema(),
                context_metadata={
                    "original_characters": context.original_characters,
                    "condensed_characters": context.condensed_characters,
                    "condensed": context.condensed,
                },
                correlation_id=correlation_id,
            )
            try:
                result = self._execute_provider(provider, request)
            except Exception as exc:
                result = ProviderExecutionResult(
                    request.run_id,
                    employee_id,
                    provider_id,
                    work_item.work_item_id,
                    "FAILED",
                    request.started_at,
                    utc_now(),
                    error=redact_provider_text(f"{type(exc).__name__}: {exc}"),
                )
            provider_run = ProviderRun(
                result.run_id,
                result.employee_id,
                result.provider_id,
                result.work_item_id,
                result.status,
                result.started_at,
                result.finished_at,
                error=redact_provider_text(result.error),
                correlation_id=correlation_id,
            )
            runs.append(provider_run)
            if result.status == "SUCCEEDED":
                self.circuit_breaker.record_success(provider_id)
                self.provider_work_item_ids.add(work_item.work_item_id)
                decision = self._parse_action(work_item, employee_id, result.content, provider_run)
                decision.provider_runs = runs
                return decision
            self.circuit_breaker.record_failure(provider_id)
        detail = runs[-1].error if runs else "no provider adapter is available"
        return AgentDecision(message=detail or "provider failure", failure_kind="PROVIDER_FAILURE", provider_run=runs[-1] if runs else None, provider_runs=runs)

    def _execute_provider(self, provider, request: ProviderExecutionRequest) -> ProviderExecutionResult:
        """Bound a provider call even when an external CLI ignores its own timeout."""
        future = self._provider_executor.submit(provider.execute, request)
        try:
            return future.result(timeout=self.provider_timeout_seconds)
        except TimeoutError:
            cancel = getattr(provider, "cancel", None)
            if callable(cancel):
                cancel()
            return ProviderExecutionResult(
                request.run_id, request.employee_id, request.provider_id, request.work_item_id,
                "FAILED", request.started_at, utc_now(),
                error=f"provider execution timed out after {self.provider_timeout_seconds:g} seconds",
            )

    def provider_health(self, provider_id: str) -> dict[str, object]:
        snapshot = self.circuit_breaker.snapshot(provider_id)
        return {
            "provider_id": snapshot.provider_id,
            "circuit": snapshot.state,
            "consecutive_failures": snapshot.consecutive_failures,
            "retry_after_seconds": snapshot.retry_after_seconds,
        }

    @staticmethod
    def _prompt_for(work_item: WorkItem) -> str:
        output_path = f"v3_provider_output/{work_item.work_item_id}.md"
        return "\n".join(
            [
                "You are an execution adapter inside Team2050 Runtime V3.",
                "Return exactly one JSON object. No Markdown or prose.",
                "Return either one action or an actions list of up to 32 declared tools.",
                f"Write only to this relative path: {output_path}",
                "Write a concise factual work product satisfying the objective.",
                "For research work, include a 'Source evidence' section with an authoritative source URL.",
                f'{{"actions":[{{"action":"filesystem.write","path":"{output_path}","content":"..."}}]}}',
                f"Objective: {work_item.objective}",
                f"Acceptance criteria: {', '.join(work_item.acceptance_criteria) or 'artifact created'}",
            ]
        )

    @staticmethod
    def _action_schema() -> dict[str, object]:
        return {
            "type": "object",
            "anyOf": [{"required": ["action"]}, {"required": ["actions"]}],
            "properties": {
                "action": {"type": "string", "enum": [item.value for item in ActionType]},
                "actions": {"type": "array", "maxItems": 32, "items": {"type": "object"}},
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
        }

    @staticmethod
    def _parse_action(work_item: WorkItem, employee_id: str, content: str, provider_run: ProviderRun) -> AgentDecision:
        try:
            payload = json.loads(content.strip())
        except json.JSONDecodeError:
            return AgentDecision(message="provider response is not valid JSON", failure_kind="PROVIDER_INVALID_ACTION", provider_run=provider_run)
        if not isinstance(payload, dict):
            return AgentDecision(message="provider proposed an unsupported action", failure_kind="PROVIDER_INVALID_ACTION", provider_run=provider_run)
        entries = payload.get("actions") if isinstance(payload.get("actions"), list) else [payload]
        if not entries or len(entries) > 32 or not all(isinstance(entry, dict) for entry in entries):
            return AgentDecision(message="provider action list failed validation", failure_kind="PROVIDER_INVALID_ACTION", provider_run=provider_run)
        actions: list[Action] = []
        for entry in entries:
            try:
                action_type = ActionType(str(entry.get("action") or ""))
            except ValueError:
                return AgentDecision(message="provider proposed an unsupported action", failure_kind="PROVIDER_INVALID_ACTION", provider_run=provider_run)
            action_payload = {key: value for key, value in entry.items() if key != "action"}
            if action_type == ActionType.FILESYSTEM_WRITE:
                path = str(action_payload.get("path") or "").replace("\\", "/").strip()
                content = str(action_payload.get("content") or "").strip()
                if not path.startswith("v3_provider_output/") or not path.endswith(".md") or not content:
                    return AgentDecision(message="provider write action failed validation", failure_kind="PROVIDER_INVALID_ACTION", provider_run=provider_run)
                action_payload["path"] = path
                action_payload["content"] = content
            action_payload["correlation_id"] = provider_run.correlation_id
            actions.append(Action(new_id("action"), work_item.work_item_id, employee_id, action_type, action_payload))
        provider_run.action_count = len(actions)
        return AgentDecision(
            message="provider action accepted",
            actions=actions,
            provider_run=provider_run,
        )
