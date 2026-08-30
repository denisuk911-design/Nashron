"""Application service boundary for capability requests."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from .capability_contracts import CapabilityExecutionResult, CapabilityRequest
from .capability_router import CapabilityRouter


class CapabilityExecutionService:
    """Expose capabilities to Product services without provider/runtime names."""

    def __init__(self, router: CapabilityRouter, permission_resolver=None) -> None:
        self.router = router
        self.permission_resolver = permission_resolver or (lambda _organization_id, _employee_id: ())

    def request(
        self,
        organization_id: str,
        capability_id: str,
        input: Mapping[str, Any] | None = None,
        *,
        employee_id: str = "",
        permissions: Iterable[str] | None = None,
        correlation_id: str = "",
        constraints: Mapping[str, Any] | None = None,
    ) -> CapabilityExecutionResult:
        resolved_permissions = (
            tuple(str(value) for value in permissions if str(value))
            if permissions is not None
            else tuple(str(value) for value in self.permission_resolver(organization_id, employee_id) if str(value))
        )
        request = CapabilityRequest(
            organization_id=organization_id,
            capability_id=capability_id,
            input=dict(input or {}),
            employee_id=employee_id,
            permissions=resolved_permissions,
            correlation_id=correlation_id,
            constraints=dict(constraints or {}),
        )
        return self.router.execute(request)
