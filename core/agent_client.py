from __future__ import annotations

from typing import Callable, Protocol

from .models import CodexResult


class AgentClient(Protocol):
    """Common generation interface for CLI-backed agents."""

    def is_available(self) -> bool:
        ...

    def version(self) -> str:
        ...

    def generate(
        self,
        prompt: str,
        allow_full_access: bool = False,
        on_delta: Callable[[str], None] | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> CodexResult:
        ...

    def cancel(self) -> None:
        ...
