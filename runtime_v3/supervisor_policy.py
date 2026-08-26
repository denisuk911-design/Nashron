from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class SupervisorPlanningAdapter(Protocol):
    def decide(self, objective: str) -> str: ...


@dataclass(frozen=True)
class SupervisorPolicyDecision:
    level: str
    shape: str
    reason: str


class HybridSupervisorPolicy:
    """Provider-neutral escalation policy for planning, not execution tools."""

    def __init__(self, local_adapter: SupervisorPlanningAdapter | None = None, strong_adapter: SupervisorPlanningAdapter | None = None) -> None:
        self.local_adapter = local_adapter
        self.strong_adapter = strong_adapter

    def decide(self, objective: str, deterministic_shape: str) -> SupervisorPolicyDecision:
        if deterministic_shape in {"SOCIAL", "SIMPLE"}:
            return SupervisorPolicyDecision("DETERMINISTIC", deterministic_shape, "rules_are_sufficient")
        local = self._try_adapter(self.local_adapter, objective)
        if local in {"SIMPLE", "COMPLEX"}:
            return SupervisorPolicyDecision("LOCAL", local, "local_model_decision")
        strong = self._try_adapter(self.strong_adapter, objective)
        if strong in {"SIMPLE", "COMPLEX"}:
            return SupervisorPolicyDecision("STRONG", strong, "strong_provider_decision")
        return SupervisorPolicyDecision("DETERMINISTIC", deterministic_shape, "adapter_unavailable_fallback")

    @staticmethod
    def _try_adapter(adapter: SupervisorPlanningAdapter | None, objective: str) -> str:
        if adapter is None:
            return ""
        try:
            return str(adapter.decide(objective)).upper().strip()
        except Exception:
            return ""
