from __future__ import annotations

from enum import StrEnum
from typing import Any


class RuntimeEngine(StrEnum):
    LEGACY = "LEGACY"
    V2_SHADOW = "V2_SHADOW"
    V2_EXPERIMENTAL = "V2_EXPERIMENTAL"
    HYBRID_V3_EXPERIMENTAL = "HYBRID_V3_EXPERIMENTAL"


def selected_runtime(settings: dict[str, Any]) -> RuntimeEngine:
    try:
        selected = RuntimeEngine(str(settings.get("runtime_engine", RuntimeEngine.LEGACY)))
        # Existing profiles use this persisted identifier. V3 Goals are now a
        # packaged product capability, not a hidden developer-only feature.
        if selected is RuntimeEngine.HYBRID_V3_EXPERIMENTAL:
            return selected
        if not bool(settings.get("developer_mode", False)):
            return RuntimeEngine.LEGACY
        return selected if selected in {
            RuntimeEngine.V2_SHADOW,
            RuntimeEngine.V2_EXPERIMENTAL,
        } else RuntimeEngine.LEGACY
    except ValueError:
        return RuntimeEngine.LEGACY
