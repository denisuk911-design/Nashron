"""Registry of tool implementations independent of Iris and the Web UI."""

from __future__ import annotations

from dataclasses import dataclass

from .capability_contracts import CapabilityToolContract, ToolExecutor


@dataclass(frozen=True)
class RegisteredTool:
    contract: CapabilityToolContract
    executor: ToolExecutor


class CapabilityRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, contract: CapabilityToolContract, executor: ToolExecutor) -> None:
        if contract.tool_id in self._tools:
            raise ValueError(f"tool already registered: {contract.tool_id}")
        if not callable(executor):
            raise TypeError("tool executor must be callable")
        self._tools[contract.tool_id] = RegisteredTool(contract, executor)

    def replace(self, contract: CapabilityToolContract, executor: ToolExecutor) -> None:
        if not callable(executor):
            raise TypeError("tool executor must be callable")
        self._tools[contract.tool_id] = RegisteredTool(contract, executor)

    def get(self, tool_id: str) -> RegisteredTool | None:
        return self._tools.get(tool_id)

    def for_capability(self, capability_id: str) -> tuple[RegisteredTool, ...]:
        return tuple(
            tool for tool in self._tools.values()
            if tool.contract.capability_id == capability_id
        )

    def contracts(self) -> tuple[CapabilityToolContract, ...]:
        return tuple(tool.contract for tool in self._tools.values())

    def capabilities(self) -> tuple[str, ...]:
        return tuple(sorted({tool.contract.capability_id for tool in self._tools.values()}))
