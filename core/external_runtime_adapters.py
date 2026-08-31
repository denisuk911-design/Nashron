"""Common normalization boundary for externally hosted runtime executions."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import signal
import subprocess
import sys
from typing import Any, Callable, Mapping, Sequence

from .runtime_contracts import (
    ExecutionRequest,
    ExecutionResult,
    RuntimeAdapter,
    RuntimeCapabilities,
    RuntimeEvent,
    RuntimeEventType,
    tupled,
)


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

    def __init__(self, command: Sequence[str], timeout_seconds: float = 45.0, runtime_id: str = "") -> None:
        if not command or timeout_seconds <= 0:
            raise ValueError("command and positive timeout are required")
        self.command = tuple(str(part) for part in command)
        self.timeout_seconds = timeout_seconds
        self.runtime_id = runtime_id

    def __call__(self, request: ExecutionRequest) -> ExternalExecutionPayload:
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags,
            start_new_session=os.name != "nt",
        )
        request_payload = json.dumps({
            "organization_id": request.organization_id,
            "objective": request.objective,
            "policy": request.policy.value,
            "correlation_id": request.correlation_id,
            "employees": [employee.employee_id for employee in request.employees],
            "workspace_root": request.metadata.get("workspace_root", "."),
            "runtime_id": self.runtime_id or request.metadata.get("runtime_id", ""),
        })
        try:
            stdout, stderr = process.communicate(request_payload, timeout=self.timeout_seconds)
        except subprocess.TimeoutExpired as error:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                    capture_output=True,
                    check=False,
                )
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.kill()
            process.communicate()
            timeout_error = TimeoutError(f"external runtime timed out after {self.timeout_seconds}s")
            setattr(timeout_error, "side_effects_committed", False)
            raise timeout_error from error
        if process.returncode != 0:
            error = RuntimeError(f"external runtime exited with code {process.returncode}")
            setattr(error, "side_effects_committed", False)
            raise error
        try:
            value = json.loads(stdout)
        except (json.JSONDecodeError, TypeError):
            # SDKs may emit informational lines on stdout; the worker contract
            # is the final JSON object, while stderr remains diagnostic output.
            value = None
            for line in reversed(stdout.splitlines()):
                try:
                    candidate = json.loads(line)
                except (json.JSONDecodeError, TypeError):
                    continue
                if isinstance(candidate, Mapping):
                    value = candidate
                    break
            if value is None:
                raise ValueError("external runtime returned invalid JSON payload")
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
        self.capabilities = RuntimeCapabilities(tool_calls=True, multi_agent=True)

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
