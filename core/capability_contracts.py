"""Product-owned contracts for capability and tool execution.

Capabilities describe what Iris or an employee needs. Tool implementations
are replaceable executors behind that contract and may be backed by any
runtime, provider, local process, or first-party service.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable, Mapping

from .runtime_contracts import RuntimeError, RuntimeEvent, RuntimeUsage


CAPABILITY_IDS = (
    "text.reason", "code", "web.research", "image.generate", "image.edit",
    "vision.analyze", "audio.transcribe", "speech.synthesize", "video.generate",
    "document.read", "document.write", "file.read", "file.write", "local.execute",
)


class ToolAvailability(StrEnum):
    AVAILABLE = "AVAILABLE"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class PrivacyMode(StrEnum):
    ANY = "ANY"
    CLOUD = "CLOUD"
    LOCAL = "LOCAL"


@dataclass(frozen=True)
class CapabilityRequest:
    organization_id: str
    capability_id: str
    input: Mapping[str, Any] = field(default_factory=dict)
    employee_id: str = ""
    permissions: tuple[str, ...] = ()
    correlation_id: str = ""
    constraints: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.organization_id.strip():
            raise ValueError("organization_id is required")
        if not self.capability_id.strip():
            raise ValueError("capability_id is required")


@dataclass(frozen=True)
class CapabilityToolContract:
    capability_id: str
    tool_id: str
    availability: ToolAvailability = ToolAvailability.AVAILABLE
    health: str = "READY"
    permissions: tuple[str, ...] = ()
    input_schema: Mapping[str, Any] = field(default_factory=dict)
    output_schema: Mapping[str, Any] = field(default_factory=dict)
    cost_hint: float = 0.0
    latency_hint_ms: int = 0
    privacy_mode: PrivacyMode = PrivacyMode.ANY
    provider_metadata: Mapping[str, Any] = field(default_factory=dict)
    historical_reliability: float = 1.0

    def __post_init__(self) -> None:
        if not self.capability_id.strip() or not self.tool_id.strip():
            raise ValueError("capability_id and tool_id are required")
        if self.cost_hint < 0 or self.latency_hint_ms < 0:
            raise ValueError("cost and latency hints cannot be negative")
        if not 0 <= self.historical_reliability <= 1:
            raise ValueError("historical_reliability must be between 0 and 1")


@dataclass(frozen=True)
class ToolExecutionResult:
    ok: bool
    output: Any = None
    error: RuntimeError | None = None
    usage: RuntimeUsage = field(default_factory=RuntimeUsage)
    artifact_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    events: tuple[RuntimeEvent, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


ToolExecutor = Callable[[CapabilityRequest], ToolExecutionResult]


@dataclass(frozen=True)
class CapabilityExecutionResult:
    ok: bool
    organization_id: str
    capability_id: str
    tool_id: str
    output: Any = None
    error: RuntimeError | None = None
    usage: RuntimeUsage = field(default_factory=RuntimeUsage)
    artifact_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    events: tuple[RuntimeEvent, ...] = ()
    fallback_used: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)
