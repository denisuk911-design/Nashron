from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_manifest(manifest: dict[str, Any]) -> bytes:
    payload = {key: value for key, value in manifest.items() if key != "signature"}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_manifest(manifest: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_manifest(manifest)).hexdigest()


def verify_release_dir(root: Path) -> bool:
    path = Path(root) / "team2050-release.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(manifest, dict) or manifest.get("signature") != sign_manifest(manifest):
        return False
    for relative, digest in manifest.get("files", {}).items():
        file_path = Path(root) / str(relative)
        if not file_path.is_file():
            return False
        actual = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual != digest:
            return False
    return True
