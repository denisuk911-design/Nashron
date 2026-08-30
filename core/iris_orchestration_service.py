"""Product Iris orchestration boundary.

Iris is one Product identity. Runtime adapters are implementation details
selected below this service and never become separate Iris personas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .agent_directory import ChatAgent
from .runtime_contracts import ExecutionPolicy, ExecutionResult
from .runtime_execution_service import RuntimeExecutionService


@dataclass(frozen=True)
class IrisExecutionContext:
    organization_id: str
    owner_id: str = "owner"
    conversation_id: str = ""


class IrisOrchestrationService:
    """Route Iris requests while preserving Product-owned identity and scope."""

    product_name = "Iris"

    def __init__(self, execution_service: RuntimeExecutionService) -> None:
        self.execution_service = execution_service

    def execute(
        self,
        context: IrisExecutionContext,
        objective: str,
        employees: Iterable[ChatAgent],
        policy: ExecutionPolicy,
        *,
        preferred_runtime: str = "",
    ) -> ExecutionResult:
        if not context.organization_id.strip():
            raise ValueError("Iris execution requires an organization scope")
        return self.execution_service.execute(
            context.organization_id,
            objective,
            employees,
            policy,
            correlation_id=context.conversation_id,
            preferred_runtime=preferred_runtime,
        )
