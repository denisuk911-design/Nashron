from __future__ import annotations

from dataclasses import dataclass, field
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
class ContextWindowResult:
    prompt: str
    original_characters: int
    condensed_characters: int
    condensed: bool


@dataclass(frozen=True)
class ContextWindowPolicy:
    """Deterministic prompt budget policy for provider execution.

    It preserves the instruction header and the latest task material while
    recording an explicit condensation boundary instead of silently truncating.
    """

    max_characters: int = 12000
    head_characters: int = 4000

    def apply(self, prompt: str) -> ContextWindowResult:
        original = str(prompt or "")
        if len(original) <= self.max_characters:
            return ContextWindowResult(original, len(original), len(original), False)
        marker = "\n\n[CONTEXT CONDENSED: middle content omitted by policy]\n\n"
        available = max(0, self.max_characters - len(marker))
        head_size = min(self.head_characters, available // 2)
        tail_size = available - head_size
        condensed = f"{original[:head_size].rstrip()}{marker}{original[-tail_size:].lstrip()}"
        return ContextWindowResult(condensed, len(original), len(condensed), True)


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
    context_metadata: dict[str, Any] = field(default_factory=dict)


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
