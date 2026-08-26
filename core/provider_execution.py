from __future__ import annotations

from dataclasses import dataclass, field
import os
import re
import threading
import time
from typing import Any, Callable, Protocol


_SECRET_ENVIRONMENT_NAME = re.compile(r"(?:api[_-]?key|token|secret|authorization|password)", re.IGNORECASE)
_INLINE_SECRET = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|authorization|password|gemini_api_key)\b\s*[:=]\s*[^\s,;]+"
)
PROVIDER_ADAPTER_CONTRACT_VERSION = "1.0"


@dataclass(frozen=True)
class ProviderCompatibilityHandshake:
    expected_version: str
    adapter_version: str
    compatible: bool
    migration_required: bool
    reason: str = ""


def provider_adapter_handshake(expected_version: str, adapter_version: str) -> ProviderCompatibilityHandshake:
    """Accept compatible minor upgrades while blocking incompatible major contracts."""
    expected = (expected_version or PROVIDER_ADAPTER_CONTRACT_VERSION).strip()
    offered = (adapter_version or PROVIDER_ADAPTER_CONTRACT_VERSION).strip()
    expected_major = expected.split(".", 1)[0]
    offered_major = offered.split(".", 1)[0]
    compatible = expected_major == offered_major
    return ProviderCompatibilityHandshake(
        expected,
        offered,
        compatible,
        compatible and expected != offered,
        "" if compatible else f"adapter contract {offered} is incompatible with runtime contract {expected}",
    )


def isolated_provider_environment(
    provider_values: dict[str, str] | None = None,
    base_environment: dict[str, str] | None = None,
) -> dict[str, str]:
    """Keep OS/runtime variables while withholding credentials of other providers."""
    allowed = {key.upper() for key in (provider_values or {})}
    environment = {
        key: value
        for key, value in (base_environment or os.environ).items()
        if not _SECRET_ENVIRONMENT_NAME.search(key) or key.upper() in allowed
    }
    environment.update({key: value for key, value in (provider_values or {}).items() if value})
    return environment


def redact_provider_text(value: str | None) -> str:
    return _INLINE_SECRET.sub(lambda match: f"{match.group(1)}=[REDACTED]", str(value or ""))


@dataclass(frozen=True)
class ProviderCircuitSnapshot:
    provider_id: str
    state: str
    consecutive_failures: int
    retry_after_seconds: float = 0.0


class ProviderCircuitBreaker:
    """Small process-local circuit breaker for provider execution failures."""

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 30.0, clock: Callable[[], float] = time.monotonic) -> None:
        self.failure_threshold = max(1, failure_threshold)
        self.cooldown_seconds = max(0.0, cooldown_seconds)
        self._clock = clock
        self._lock = threading.Lock()
        self._failures: dict[str, int] = {}
        self._opened_at: dict[str, float] = {}

    def allow(self, provider_id: str) -> bool:
        with self._lock:
            opened_at = self._opened_at.get(provider_id)
            if opened_at is None:
                return True
            if self._clock() - opened_at >= self.cooldown_seconds:
                self._opened_at.pop(provider_id, None)
                self._failures[provider_id] = 0
                return True
            return False

    def record_success(self, provider_id: str) -> None:
        with self._lock:
            self._failures[provider_id] = 0
            self._opened_at.pop(provider_id, None)

    def record_failure(self, provider_id: str) -> None:
        with self._lock:
            failures = self._failures.get(provider_id, 0) + 1
            self._failures[provider_id] = failures
            if failures >= self.failure_threshold:
                self._opened_at[provider_id] = self._clock()

    def snapshot(self, provider_id: str) -> ProviderCircuitSnapshot:
        with self._lock:
            opened_at = self._opened_at.get(provider_id)
            remaining = max(0.0, self.cooldown_seconds - (self._clock() - opened_at)) if opened_at is not None else 0.0
            return ProviderCircuitSnapshot(
                provider_id,
                "OPEN" if opened_at is not None and remaining > 0 else "CLOSED",
                self._failures.get(provider_id, 0),
                remaining,
            )


@dataclass(frozen=True)
class ProviderCapabilityProfile:
    """Versioned execution contract used for provider selection, not UI labels."""

    provider_id: str
    model_id: str = ""
    contract_version: str = PROVIDER_ADAPTER_CONTRACT_VERSION
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
    correlation_id: str = ""


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
