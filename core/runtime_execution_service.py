"""Product-facing execution facade independent of a runtime SDK."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Callable, Iterable

from .agent_directory import ChatAgent
from .native_runtime_adapter import NativeRuntimeAdapter
from .runtime_contracts import EmployeeRef, ExecutionPolicy, ExecutionRequest, ExecutionResult, tupled
from .runtime_selector import RuntimeSelector
from .runtime_journal import RuntimeExecutionJournal


class RuntimeExecutionService:
    """Translate Product identities into a selected runtime request."""

    def __init__(
        self,
        native_service,
        external_adapters=None,
        journal: RuntimeExecutionJournal | None = None,
        promoted_runtime_ids: set[str] | None = None,
        permission_resolver: Callable[[str], Iterable[str]] | None = None,
    ) -> None:
        self._employee_scope: ContextVar[dict[str, ChatAgent]] = ContextVar("runtime_employee_scope", default={})
        self._permission_resolver = permission_resolver or (lambda _agent_id: ())
        self.journal = journal
        native = NativeRuntimeAdapter(native_service, lambda employee: self._employee_scope.get().get(employee.employee_id))
        self.selector = RuntimeSelector(
            {"native": native, **dict(external_adapters or {})},
            promoted_runtime_ids=promoted_runtime_ids,
        )

    def execute(
        self,
        organization_id: str,
        objective: str,
        employees: Iterable[ChatAgent],
        policy: ExecutionPolicy = ExecutionPolicy.DETERMINISTIC_WORKFLOW,
        *,
        correlation_id: str = "",
        preferred_runtime: str = "",
    ) -> ExecutionResult:
        agents = list(employees)
        scope_token = self._employee_scope.set({agent.agent_id: agent for agent in agents})
        request = ExecutionRequest(
            organization_id=organization_id,
            objective=objective,
            policy=policy,
            employees=tuple(
                EmployeeRef(
                    employee_id=agent.agent_id,
                    display_name=agent.display_name,
                    role=agent.primary_role,
                    provider_binding_id=agent.provider_id,
                    competencies=tupled([agent.primary_role, *agent.roles, agent.engine_name]),
                    permissions=tupled(self._permission_resolver(agent.agent_id)),
                )
                for agent in agents
            ),
            correlation_id=correlation_id,
            metadata={"preferred_runtime": preferred_runtime} if preferred_runtime else {},
        )
        try:
            if self.journal is not None:
                self.journal.begin(request)
            try:
                result = self.selector.execute(request)
            except Exception as error:
                if self.journal is not None:
                    self.journal.fail(request, error)
                raise
            if self.journal is not None:
                self.journal.complete(request, result)
            return result
        finally:
            self._employee_scope.reset(scope_token)
