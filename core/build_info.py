from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


APP_VERSION = "2.3.1"


def _resource_path() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1])) / "data" / "build_info.json"


def _load_packaged_info() -> dict[str, str]:
    path = _resource_path()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _source_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip() or "source"
    except (OSError, subprocess.SubprocessError):
        return "source"


def build_info() -> dict[str, str]:
    packaged = _load_packaged_info()
    return {
        "version": str(packaged.get("version") or APP_VERSION),
        "commit": str(packaged.get("commit") or _source_commit()),
        "timestamp": str(packaged.get("timestamp") or datetime.now(timezone.utc).isoformat(timespec="seconds")),
    }


def build_label() -> str:
    info = build_info()
    return f"v{info['version']} · сборка {info['commit']} · {info['timestamp']}"
