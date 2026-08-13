from __future__ import annotations

from enum import StrEnum
from typing import Any


class RuntimeEngine(StrEnum):
    LEGACY = "LEGACY"
    V2_EXPERIMENTAL = "V2_EXPERIMENTAL"


def selected_runtime(settings: dict[str, Any]) -> RuntimeEngine:
    if not bool(settings.get("developer_mode", False)):
        return RuntimeEngine.LEGACY
    try:
        return RuntimeEngine(str(settings.get("runtime_engine", RuntimeEngine.LEGACY)))
    except ValueError:
        return RuntimeEngine.LEGACY
