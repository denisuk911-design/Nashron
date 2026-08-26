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
        return self.route("planning", objective, deterministic_shape, "LOW", "LOW", [])

    def route(self, step: str, objective: str, complexity: str, risk: str, cost: str, required_capabilities: list[str]) -> SupervisorPolicyDecision:
        if complexity in {"SOCIAL", "SIMPLE", "LOW"} and risk == "LOW":
            return SupervisorPolicyDecision("DETERMINISTIC", complexity, "rules_are_sufficient")
        if complexity == "MEDIUM" and risk == "LOW":
            local = self._try_adapter(self.local_adapter, objective)
            if local:
                return SupervisorPolicyDecision("LOCAL", local if local in {"SIMPLE", "COMPLEX"} else complexity, "local_model_decision")
            return SupervisorPolicyDecision("DETERMINISTIC", complexity, "local_unavailable_fallback")
        strong = self._try_adapter(self.strong_adapter, objective)
        if strong in {"SIMPLE", "COMPLEX"}:
            return SupervisorPolicyDecision("STRONG", strong, "strong_provider_decision")
        local = self._try_adapter(self.local_adapter, objective)
        if local in {"SIMPLE", "COMPLEX"}:
            return SupervisorPolicyDecision("LOCAL", local, "strong_unavailable_local_fallback")
        return SupervisorPolicyDecision("DETERMINISTIC", complexity, "adapter_unavailable_fallback")

    @staticmethod
    def _try_adapter(adapter: SupervisorPlanningAdapter | None, objective: str) -> str:
        if adapter is None:
            return ""
        try:
            return str(adapter.decide(objective)).upper().strip()
        except Exception:
            return ""
