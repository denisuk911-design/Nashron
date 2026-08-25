from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProviderExecutionRequest:
    run_id: str
    employee_id: str
    provider_id: str
    work_item_id: str
    prompt: str
    started_at: str


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

    def execute(self, request: ProviderExecutionRequest) -> ProviderExecutionResult:
        ...
