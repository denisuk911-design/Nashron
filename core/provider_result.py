from __future__ import annotations

from typing import Any

from .models import CodexResult


def normalize_provider_result(value: Any) -> CodexResult:
    """Convert every provider/adapter return value to the stable runtime type."""
    if isinstance(value, CodexResult):
        return value
    if value is None:
        return CodexResult(False, "", None, 0.0, "provider_returned_none")
    if isinstance(value, dict):
        return CodexResult(
            bool(value.get("ok", False)),
            str(value.get("content") or ""),
            value.get("returncode"),
            float(value.get("duration_seconds") or 0.0),
            str(value.get("error")) if value.get("error") else None,
            bool(value.get("cancelled", False)),
            bool(value.get("timed_out", False)),
        )
    return CodexResult(
        bool(getattr(value, "ok", False)),
        str(getattr(value, "content", "") or ""),
        getattr(value, "returncode", None),
        float(getattr(value, "duration_seconds", 0.0) or 0.0),
        str(getattr(value, "error", "")) or "unsupported_provider_result",
        bool(getattr(value, "cancelled", False)),
        bool(getattr(value, "timed_out", False)),
    )
