from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable

from .models import AgentAction, AgentResult, FailureReason


class ScriptedProviderAdapter:
    """Deterministic provider used by the isolated benchmark and chaos tests."""

    def __init__(
        self,
        provider_id: str,
        outcomes: dict[str, list[AgentResult | FailureReason]] | None = None,
        result_factory: Callable[[AgentAction, str], AgentResult] | None = None,
    ) -> None:
        self.provider_id = provider_id
        self._outcomes = defaultdict(deque)
        for step_id, values in (outcomes or {}).items():
            self._outcomes[step_id].extend(values)
        self._result_factory = result_factory or self._default_result
        self.calls: list[AgentAction] = []

    def capabilities(self) -> set[str]:
        return {"chat", "tools", "files", "structured_output", "session_resume", "streaming"}

    def execute(self, action: AgentAction) -> AgentResult:
        self.calls.append(action)
        if self._outcomes[action.step_id]:
            outcome = self._outcomes[action.step_id].popleft()
            if isinstance(outcome, FailureReason):
                return AgentResult(False, self.provider_id, failure_reason=outcome, duration_ms=2)
            outcome.provider_id = self.provider_id
            return outcome
        return self._result_factory(action, self.provider_id)

    @staticmethod
    def _default_result(action: AgentAction, provider_id: str) -> AgentResult:
        return AgentResult(
            True,
            provider_id,
            summary=f"Completed {action.operation}",
            artifacts=[
                {
                    "artifact_id": f"artifact-{action.step_id}",
                    "artifact_type": action.expected_output,
                    "content": {"step": action.step_id, "requirements": action.requirements},
                    "evidence": {"provider_run": True, "operation": action.operation},
                }
            ],
            duration_ms=3,
            input_tokens=20,
            output_tokens=10,
        )


class LocalAgentRuntime:
    def __init__(self, providers: dict[str, ScriptedProviderAdapter]) -> None:
        self.providers = providers

    def execute(self, action: AgentAction, provider_id: str) -> AgentResult:
        provider = self.providers.get(provider_id)
        if provider is None:
            return AgentResult(False, provider_id, failure_reason=FailureReason.PROVIDER_UNAVAILABLE)
        return provider.execute(action)
