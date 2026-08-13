from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import os
from time import monotonic


@dataclass(frozen=True)
class ScheduledProviderRun:
    agent_key: str
    provider_id: str
    queued_at: float


class ProviderScheduler:
    """Small fair scheduler that prevents a team call from flooding CLI providers."""

    def __init__(self, provider_limits: dict[str, int] | None = None, total_limit: int | None = None) -> None:
        cpu_count = max(1, os.cpu_count() or 1)
        self.total_limit = max(1, total_limit or min(4, max(2, cpu_count // 2)))
        self.provider_limits = {
            "CODEX_CLI": 2,
            "GEMINI_CLI": 2,
            "CLAUDE_CLI": 1,
            "LOCAL_RUNTIME": 1,
            **(provider_limits or {}),
        }
        self._queue: deque[ScheduledProviderRun] = deque()
        self._active: dict[str, ScheduledProviderRun] = {}

    def enqueue(self, agent_key: str, provider_id: str) -> bool:
        if agent_key in self._active or any(run.agent_key == agent_key for run in self._queue):
            return False
        self._queue.append(ScheduledProviderRun(agent_key, provider_id, monotonic()))
        return True

    def startable(self) -> list[ScheduledProviderRun]:
        result: list[ScheduledProviderRun] = []
        while self._queue and len(self._active) < self._effective_total_limit():
            selected_index = self._first_startable_index()
            if selected_index is None:
                break
            run = self._queue[selected_index]
            del self._queue[selected_index]
            self._active[run.agent_key] = run
            result.append(run)
        return result

    def complete(self, agent_key: str) -> None:
        self._active.pop(agent_key, None)

    def clear(self) -> None:
        self._queue.clear()
        self._active.clear()

    @property
    def has_pending(self) -> bool:
        return bool(self._queue)

    @property
    def active_count(self) -> int:
        return len(self._active)

    def _first_startable_index(self) -> int | None:
        active_by_provider: dict[str, int] = {}
        for run in self._active.values():
            active_by_provider[run.provider_id] = active_by_provider.get(run.provider_id, 0) + 1
        for index, run in enumerate(self._queue):
            limit = max(1, self.provider_limits.get(run.provider_id, 1))
            if active_by_provider.get(run.provider_id, 0) < limit:
                return index
        return None

    def _effective_total_limit(self) -> int:
        try:
            import psutil  # type: ignore

            if psutil.cpu_percent(interval=None) >= 85 or psutil.virtual_memory().percent >= 90:
                return 1
        except (ImportError, OSError):
            pass
        return self.total_limit
