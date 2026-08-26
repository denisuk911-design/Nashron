from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol


@dataclass(frozen=True)
class ProviderCapabilityProfile:
    """Versioned execution contract used for provider selection, not UI labels."""

    provider_id: str
    model_id: str = ""
    capabilities: frozenset[str] = frozenset({"chat"})
    supports_native_tools: bool = False
    supports_native_structured_output: bool = False
    supports_streaming: bool = False
    supports_cancellation: bool = True

    def supports(self, required: set[str]) -> bool:
        return required <= self.capabilities


@dataclass(frozen=True)
class ProviderExecutionRequest:
    run_id: str
    employee_id: str
    provider_id: str
    work_item_id: str
    prompt: str
    started_at: str
    required_capabilities: frozenset[str] = frozenset()
    output_schema: dict[str, Any] | None = None
    on_delta: Callable[[str], None] | None = None


@dataclass(frozen=True)
class ProviderExecutionResult:
    run_id: str
    employee_id: str
    provider_id: str
    work_item_id: str
    status: str
    started_at: str
    finished_at: str
    content: str = ""
    error: str = ""


class ProviderExecutionAdapter(Protocol):
    provider_id: str
    capability_profile: ProviderCapabilityProfile

    def execute(self, request: ProviderExecutionRequest) -> ProviderExecutionResult:
        ...

    def cancel(self) -> None:
        ...
