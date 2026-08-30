"""Runtime-neutral adapter for the validated Native Runtime baseline."""

from __future__ import annotations

from typing import Callable

from .agent_directory import ChatAgent
from .runtime_contracts import (
    EmployeeRef,
    ExecutionRequest,
    ExecutionResult,
    RuntimeAdapter,
    RuntimeEvent,
    event_type_from_native_stage,
)


class NativeRuntimeAdapter(RuntimeAdapter):
    runtime_id = "native"

    def __init__(self, service, employee_resolver: Callable[[EmployeeRef], ChatAgent | None]) -> None:
        self.service = service
        self.employee_resolver = employee_resolver

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        agents = [
            agent
            for employee in request.employees
            if (agent := self.employee_resolver(employee)) is not None
        ]
        result = self.service.run_goal(request.organization_id, request.objective, agents)
        goal_id = next(iter(result.state.goals), "")
        events: list[RuntimeEvent] = []
        for trace in result.state.trace_events.values():
            event_type = event_type_from_native_stage(trace.stage)
            if event_type is None:
                continue
            events.append(RuntimeEvent(
                event_type=event_type,
                organization_id=request.organization_id,
                correlation_id=getattr(trace, "correlation_id", ""),
                run_id=getattr(trace, "run_id", ""),
                employee_id=getattr(trace, "employee_id", ""),
                work_item_id=getattr(trace, "work_item_id", ""),
                artifact_id=getattr(trace, "artifact_id", ""),
                evidence_id=getattr(trace, "evidence_id", ""),
                detail=getattr(trace, "detail", ""),
            ))
        return ExecutionResult(
            ok=result.ok,
            organization_id=request.organization_id,
            runtime_id=self.runtime_id,
            summary=result.summary,
            correlation_id=request.correlation_id,
            goal_id=goal_id,
            artifact_refs=tuple(result.state.artifacts),
            evidence_refs=tuple(result.state.evidence),
            events=tuple(events),
            data={"native_workspace_root": str(result.workspace_root)},
        )
