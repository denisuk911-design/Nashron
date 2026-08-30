"""Common normalization boundary for externally hosted runtime executions."""

from __future__ import annotations

from dataclasses import dataclass
import json
import subprocess
import sys
from typing import Any, Callable, Mapping, Sequence

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
    organization_id: str = ""

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ExternalExecutionPayload":
        return cls(
            ok=bool(value.get("ok")),
            summary=str(value.get("summary") or ""),
            organization_id=str(value.get("organization_id") or ""),
            artifact_refs=tupled(value.get("artifact_refs")),
            evidence_refs=tupled(value.get("evidence_refs")),
            observations=tupled(value.get("observations")),
            tool_calls=tupled(value.get("tool_calls")),
            data=value.get("data") if isinstance(value.get("data"), Mapping) else {},
        )


class SubprocessRuntimeBridge:
    """Bounded JSON IPC bridge for an SDK running outside Product/Core."""

    def __init__(self, command: Sequence[str], timeout_seconds: float = 45.0) -> None:
        if not command or timeout_seconds <= 0:
            raise ValueError("command and positive timeout are required")
        self.command = tuple(str(part) for part in command)
        self.timeout_seconds = timeout_seconds

    def __call__(self, request: ExecutionRequest) -> ExternalExecutionPayload:
        completed = subprocess.run(
            self.command,
            input=json.dumps({
                "organization_id": request.organization_id,
                "objective": request.objective,
                "policy": request.policy.value,
                "correlation_id": request.correlation_id,
                "employees": [employee.employee_id for employee in request.employees],
            }),
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            error = RuntimeError(f"external runtime exited with code {completed.returncode}")
            setattr(error, "side_effects_committed", False)
            raise error
        try:
            value = json.loads(completed.stdout)
        except (json.JSONDecodeError, TypeError) as error:
            raise ValueError("external runtime returned invalid JSON payload") from error
        if not isinstance(value, Mapping):
            raise ValueError("external runtime payload must be a JSON object")
        return ExternalExecutionPayload.from_mapping(value)


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
        if payload.organization_id and payload.organization_id != request.organization_id:
            raise ValueError("external runtime organization scope mismatch")
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
