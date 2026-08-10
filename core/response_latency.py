from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResponseLatencyPolicy:
    soft_warning_seconds: int
    extended_warning_seconds: int
    timeout_seconds: int

    @classmethod
    def from_settings(cls, settings: dict[str, Any]) -> "ResponseLatencyPolicy":
        soft = _setting_int(settings, "response_soft_warning_seconds", 20)
        extended = _setting_int(settings, "response_extended_warning_seconds", 90)
        timeout = _setting_int(settings, "response_timeout_seconds", 0)

        soft = max(5, min(soft, 3600))
        extended = max(soft + 1, min(extended, 7200))
        if timeout > 0:
            timeout = max(extended + 1, min(timeout, 10800))
        else:
            timeout = 0
        return cls(soft, extended, timeout)

    @property
    def timeout_enabled(self) -> bool:
        return self.timeout_seconds > 0


def _setting_int(settings: dict[str, Any], key: str, default: int) -> int:
    try:
        return int(settings.get(key, default))
    except (TypeError, ValueError):
        return default
