"""Capability-aware tool selection, fallback, normalized events and telemetry."""

from __future__ import annotations

from dataclasses import replace
from time import monotonic
from typing import Any

from .capability_contracts import (
    CapabilityExecutionResult,
    CapabilityRequest,
    CapabilityToolContract,
    PrivacyMode,
    ToolAvailability,
    ToolExecutionResult,
)
from .capability_registry import CapabilityRegistry, RegisteredTool
from .runtime_contracts import RuntimeError, RuntimeEvent, RuntimeEventType, RuntimeUsage


class CapabilityUnavailableError(Exception):
    pass


class CapabilityPermissionError(Exception):
    pass


class CapabilityRouter:
    """Choose a permitted, healthy implementation without provider knowledge."""

    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry

    @staticmethod
    def _matches_constraints(contract: CapabilityToolContract, request: CapabilityRequest) -> bool:
        constraints = request.constraints
        required_privacy = str(constraints.get("privacy_mode") or PrivacyMode.ANY)
        if required_privacy == PrivacyMode.LOCAL and contract.privacy_mode not in {PrivacyMode.LOCAL, PrivacyMode.ANY}:
            return False
        if constraints.get("local_only") and contract.privacy_mode not in {PrivacyMode.LOCAL, PrivacyMode.ANY}:
            return False
        max_cost = constraints.get("max_cost")
        if max_cost is not None and contract.cost_hint > float(max_cost):
            return False
        max_latency = constraints.get("max_latency_ms")
        if max_latency is not None and contract.latency_hint_ms > int(max_latency):
            return False
        return True

    @staticmethod
    def _permitted(tool: RegisteredTool, request: CapabilityRequest) -> bool:
        return set(tool.contract.permissions).issubset(set(request.permissions))

    def _candidates(self, request: CapabilityRequest, excluded: set[str] | None = None) -> list[RegisteredTool]:
        excluded = excluded or set()
        tools = [
            tool for tool in self.registry.for_capability(request.capability_id)
            if tool.contract.tool_id not in excluded
            and tool.contract.availability is ToolAvailability.AVAILABLE
            and tool.contract.health.upper() in {"READY", "AVAILABLE", "OK"}
            and self._permitted(tool, request)
            and self._matches_constraints(tool.contract, request)
        ]
        preferred = str(request.constraints.get("preferred_tool_id") or "")
        return sorted(
            tools,
            key=lambda tool: (
                0 if tool.contract.tool_id == preferred else 1,
                -tool.contract.historical_reliability,
                tool.contract.cost_hint,
                tool.contract.latency_hint_ms,
                tool.contract.tool_id,
            ),
        )

    def select(self, request: CapabilityRequest, excluded: set[str] | None = None) -> RegisteredTool:
        candidates = self._candidates(request, excluded)
        if candidates:
            return candidates[0]
        known = self.registry.for_capability(request.capability_id)
        if known and any(not self._permitted(tool, request) for tool in known):
            raise CapabilityPermissionError(
                "no registered tool satisfies the requested permissions"
            )
        raise CapabilityUnavailableError(
            f"capability is not available: {request.capability_id}"
        )

    @staticmethod
    def _event(event_type: RuntimeEventType, request: CapabilityRequest, detail: str = "", data: dict[str, Any] | None = None) -> RuntimeEvent:
        return RuntimeEvent(
            event_type=event_type,
            organization_id=request.organization_id,
            correlation_id=request.correlation_id,
            employee_id=request.employee_id,
            detail=detail,
            data=data or {},
        )

    def execute(self, request: CapabilityRequest) -> CapabilityExecutionResult:
        events = [self._event(RuntimeEventType.CAPABILITY_REQUESTED, request, request.capability_id)]
        excluded: set[str] = set()
        preferred_tool_id = str(request.constraints.get("preferred_tool_id") or "")
        preferred = self.registry.get(preferred_tool_id) if preferred_tool_id else None
        preferred_unavailable = bool(
            preferred is not None
            and (
                preferred.contract.availability is not ToolAvailability.AVAILABLE
                or preferred.contract.health.upper() not in {"READY", "AVAILABLE", "OK"}
                or not self._permitted(preferred, request)
                or not self._matches_constraints(preferred.contract, request)
            )
        )
        fallback_used = preferred_unavailable
        started = monotonic()
        while True:
            try:
                selected = self.select(request, excluded)
            except CapabilityUnavailableError as error:
                runtime_error = RuntimeError("capability_unavailable", str(error), retryable=True)
                events.append(self._event(RuntimeEventType.TOOL_FAILED, request, str(error)))
                return CapabilityExecutionResult(
                    False, request.organization_id, request.capability_id, "",
                    error=runtime_error, events=tuple(events), fallback_used=fallback_used,
                )
            except CapabilityPermissionError as error:
                runtime_error = RuntimeError("permission_denied", str(error), retryable=False)
                events.append(self._event(RuntimeEventType.TOOL_FAILED, request, str(error)))
                return CapabilityExecutionResult(
                    False, request.organization_id, request.capability_id, "",
                    error=runtime_error, events=tuple(events), fallback_used=fallback_used,
                )

            if fallback_used:
                fallback_from = next(iter(excluded), preferred_tool_id)
                events.append(self._event(
                    RuntimeEventType.CAPABILITY_FALLBACK, request,
                    f"fallback selected: {selected.contract.tool_id}",
                    {"from": fallback_from, "to": selected.contract.tool_id},
                ))
            events.append(self._event(RuntimeEventType.TOOL_SELECTED, request, selected.contract.tool_id))
            events.append(self._event(RuntimeEventType.TOOL_STARTED, request, selected.contract.tool_id))
            try:
                result = selected.executor(request)
                if not isinstance(result, ToolExecutionResult):
                    raise TypeError("tool executor must return ToolExecutionResult")
            except Exception as error:
                result = ToolExecutionResult(
                    False,
                    error=RuntimeError("tool_exception", str(error), retryable=True),
                )
            duration_ms = int((monotonic() - started) * 1000)
            usage = replace(result.usage, duration_ms=max(result.usage.duration_ms, duration_ms))
            events.extend(result.events)
            terminal = RuntimeEventType.TOOL_COMPLETED if result.ok else RuntimeEventType.TOOL_FAILED
            events.append(self._event(terminal, request, selected.contract.tool_id))
            if result.ok:
                return CapabilityExecutionResult(
                    True, request.organization_id, request.capability_id,
                    selected.contract.tool_id, result.output, usage=usage,
                    artifact_refs=result.artifact_refs, evidence_refs=result.evidence_refs,
                    events=tuple(events), fallback_used=fallback_used,
                    metadata={**dict(result.metadata), "provider_metadata": dict(selected.contract.provider_metadata)},
                )
            excluded.add(selected.contract.tool_id)
            next_candidates = self._candidates(request, excluded)
            if not next_candidates:
                return CapabilityExecutionResult(
                    False, request.organization_id, request.capability_id,
                    selected.contract.tool_id,
                    error=result.error, usage=usage, events=tuple(events),
                    fallback_used=fallback_used,
                )
            fallback_used = True
