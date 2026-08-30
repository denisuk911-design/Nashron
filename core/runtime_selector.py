"""Policy-driven runtime selection and bounded fallback."""

from __future__ import annotations

from dataclasses import dataclass

from .runtime_contracts import ExecutionRequest, ExecutionResult, RuntimeAdapter


@dataclass(frozen=True)
class RuntimeSelection:
    runtime_id: str
    reason: str
    fallback: bool = False


class RuntimeSelector:
    """Select registered adapters without exposing runtime mechanics to UI."""

    def __init__(
        self,
        adapters: dict[str, RuntimeAdapter],
        native_id: str = "native",
        promoted_runtime_ids: set[str] | None = None,
    ) -> None:
        if native_id not in adapters:
            raise ValueError("Native baseline adapter is required")
        self.adapters = dict(adapters)
        self.native_id = native_id
        self.promoted_runtime_ids = set(promoted_runtime_ids or ()) | {native_id}

    def select(self, request: ExecutionRequest) -> RuntimeSelection:
        preferred = str(request.metadata.get("preferred_runtime") or "").strip()
        if preferred in self.adapters and preferred in self.promoted_runtime_ids:
            return RuntimeSelection(preferred, "explicit runtime preference")
        if request.policy.value == "deterministic_workflow":
            return RuntimeSelection(self.native_id, "deterministic workflow remains Native baseline")
        if request.policy.value in {"conversational", "direct_action"}:
            if "openai-agents" in self.adapters and "openai-agents" in self.promoted_runtime_ids:
                return RuntimeSelection("openai-agents", "short policy selected the registered candidate")
            external_ids = [
                runtime_id for runtime_id in self.adapters
                if runtime_id != self.native_id and runtime_id in self.promoted_runtime_ids
            ]
            if external_ids:
                return RuntimeSelection(external_ids[0], "short policy selected the available candidate")
        if (
            request.policy.value in {"dynamic_multi_agent", "long_running_project"}
            and "langgraph" in self.adapters
            and "langgraph" in self.promoted_runtime_ids
        ):
            return RuntimeSelection("langgraph", "durable policy selected the registered candidate")
        return RuntimeSelection(self.native_id, "no promoted candidate is registered")

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        selection = self.select(request)
        try:
            return self.adapters[selection.runtime_id].execute(request)
        except Exception as error:
            if selection.runtime_id == self.native_id:
                raise
            # A failed adapter may have committed an external side effect.
            # Never replay the request through Native when that is explicit.
            if bool(getattr(error, "side_effects_committed", False)):
                raise
            fallback = self.adapters[self.native_id].execute(request)
            return ExecutionResult(
                ok=fallback.ok,
                organization_id=fallback.organization_id,
                runtime_id=fallback.runtime_id,
                summary=fallback.summary,
                correlation_id=fallback.correlation_id,
                goal_id=fallback.goal_id,
                artifact_refs=fallback.artifact_refs,
                evidence_refs=fallback.evidence_refs,
                events=fallback.events,
                data={**fallback.data, "fallback_from": selection.runtime_id, "fallback_reason": str(error)},
            )
