from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class ConfigurationRepository:
    """Safe JSON configuration store for future Director Console files."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve(strict=False)
        root = self.root.resolve(strict=False)
        if candidate != root and root not in candidate.parents:
            raise ValueError("Configuration path escapes repository root")
        return candidate

    def read_json(self, relative_path: str, default: Any = None) -> Any:
        path = self.resolve(relative_path)
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def write_json_atomic(self, relative_path: str, payload: Any, dry_run: bool = False) -> Path:
        path = self.resolve(relative_path)
        if dry_run:
            return path
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
            os.replace(temp_name, path)
        finally:
            temp_path = Path(temp_name)
            if temp_path.exists():
                temp_path.unlink()
        return path
