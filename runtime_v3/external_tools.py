from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ExternalToolDescriptor:
    name: str
    schema: dict[str, object]
    capabilities: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ExternalToolResult:
    ok: bool
    summary: str
    data: dict[str, object]
    task_handle: str = ""


class ExternalToolAdapter(Protocol):
    def discover(self) -> list[ExternalToolDescriptor]: ...
    def invoke(self, tool_name: str, arguments: dict[str, object], correlation_id: str = "") -> ExternalToolResult: ...
    def cancel(self, task_handle: str) -> None: ...


class ExternalToolRegistry:
    """Adapter registry for MCP, browser and other stateless external tools."""

    def __init__(self, adapters: dict[str, ExternalToolAdapter] | None = None) -> None:
        self.adapters = dict(adapters or {})

    def discover(self, adapter_id: str) -> list[ExternalToolDescriptor]:
        adapter = self.adapters.get(adapter_id)
        return adapter.discover() if adapter is not None else []

    def invoke(self, adapter_id: str, tool_name: str, arguments: dict[str, object], correlation_id: str = "") -> ExternalToolResult:
        adapter = self.adapters.get(adapter_id)
        if adapter is None:
            return ExternalToolResult(False, f"external tool adapter unavailable: {adapter_id}", {})
        known = {descriptor.name for descriptor in adapter.discover()}
        if tool_name not in known:
            return ExternalToolResult(False, f"external tool unavailable: {tool_name}", {})
        return adapter.invoke(tool_name, arguments, correlation_id)
