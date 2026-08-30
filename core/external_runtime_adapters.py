"""Common normalization boundary for externally hosted runtime executions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .runtime_contracts import ExecutionRequest, ExecutionResult, RuntimeAdapter, RuntimeEvent, RuntimeEventType, tupled


@dataclass(frozen=True)
class ExternalExecutionPayload:
    """Data returned by an SDK bridge after it has completed its run."""

    ok: bool
    summary: str
    artifact_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    observations: tuple[str, ...] = ()
    tool_calls: tuple[str, ...] = ()
    data: Mapping[str, Any] | None = None


class CallbackRuntimeAdapter(RuntimeAdapter):
    """Normalize a real SDK bridge while keeping the SDK out of Product code.

    The callback is deliberately injected: importing an SDK or creating a
    provider client belongs to the isolated runtime process/environment.
    """

    def __init__(self, runtime_id: str, executor: Callable[[ExecutionRequest], ExternalExecutionPayload]) -> None:
        self.runtime_id = runtime_id
        self._executor = executor

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        payload = self._executor(request)
        events = [RuntimeEvent(RuntimeEventType.RUN_STARTED, request.organization_id, request.correlation_id)]
        events.extend(
            RuntimeEvent(
                RuntimeEventType.TOOL_CALLED,
                request.organization_id,
                request.correlation_id,
                detail=tool_call,
            )
            for tool_call in payload.tool_calls
        )
        events.extend(
            RuntimeEvent(
                RuntimeEventType.OBSERVATION_RECORDED,
                request.organization_id,
                request.correlation_id,
                detail=observation,
            )
            for observation in payload.observations
        )
        events.extend(
            RuntimeEvent(
                RuntimeEventType.ARTIFACT_CREATED,
                request.organization_id,
                request.correlation_id,
                artifact_id=artifact_id,
            )
            for artifact_id in payload.artifact_refs
        )
        events.append(RuntimeEvent(
            RuntimeEventType.RUN_COMPLETED if payload.ok else RuntimeEventType.RUN_FAILED,
            request.organization_id,
            request.correlation_id,
            detail=payload.summary,
        ))
        return ExecutionResult(
            ok=payload.ok,
            organization_id=request.organization_id,
            runtime_id=self.runtime_id,
            summary=payload.summary,
            correlation_id=request.correlation_id,
            artifact_refs=tupled(payload.artifact_refs),
            evidence_refs=tupled(payload.evidence_refs),
            events=tuple(events),
            data=dict(payload.data or {}),
        )


class OpenAIAgentsRuntimeAdapter(CallbackRuntimeAdapter):
    def __init__(self, executor):
        super().__init__("openai-agents", executor)


class LangGraphRuntimeAdapter(CallbackRuntimeAdapter):
    def __init__(self, executor):
        super().__init__("langgraph", executor)


class GoogleAdkRuntimeAdapter(CallbackRuntimeAdapter):
    def __init__(self, executor):
        super().__init__("google-adk", executor)


class AutoGenRuntimeAdapter(CallbackRuntimeAdapter):
    def __init__(self, executor):
        super().__init__("autogen", executor)
