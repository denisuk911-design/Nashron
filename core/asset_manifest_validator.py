from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass
class AssetValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_product_assets(root: Path) -> AssetValidationResult:
    result = AssetValidationResult()
    _validate_theme_manifest(root, result)
    _validate_avatars(root, result)
    _validate_audio(root, result)
    _validate_localization(result)
    _validate_package_spec(root, result)
    return result


def _validate_theme_manifest(root: Path, result: AssetValidationResult) -> None:
    manifest_path = root / "data" / "theme_backgrounds" / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result.errors.append(f"theme_manifest:{exc}")
        return
    collections = manifest.get("collections")
    if not isinstance(collections, dict):
        result.errors.append("theme_manifest:collections_missing")
        return
    required = {"city", "forest", "ocean", "mountains", "night_city", "space"}
    for collection in sorted(required):
        entries = collections.get(collection, [])
        if not isinstance(entries, list) or len(entries) < 3:
            result.errors.append(f"theme_collection:{collection}:needs_at_least_three_images")
            continue
        for relative in entries:
            path = manifest_path.parent / str(relative)
            if not path.is_file() or path.stat().st_size < 100_000:
                result.errors.append(f"theme_asset:{relative}:missing_or_invalid")


def _validate_avatars(root: Path, result: AssetValidationResult) -> None:
    from .avatar_catalog import list_avatar_files

    avatars = list_avatar_files(root / "data" / "avatars")
    if len(avatars) < 75:
        result.errors.append(f"avatars:expected_at_least_75:found_{len(avatars)}")
    for path in avatars:
        if path.stat().st_size < 100:
            result.errors.append(f"avatar:{path.name}:invalid")


def _validate_audio(root: Path, result: AssetValidationResult) -> None:
    sound_dir = root / "data" / "sounds"
    sounds = list(sound_dir.glob("*.wav")) if sound_dir.exists() else []
    if not sounds:
        result.warnings.append("audio:no_bundled_wav_assets_runtime_fallback_used")
    for path in sounds:
        try:
            if path.read_bytes()[:4] != b"RIFF":
                result.errors.append(f"audio:{path.name}:invalid_wav")
        except OSError as exc:
            result.errors.append(f"audio:{path.name}:{exc}")


def _validate_localization(result: AssetValidationResult) -> None:
    from gui.localization import TEXT

    baseline = set(TEXT.get("ru", {}))
    for language in ("uk", "en"):
        missing = baseline - set(TEXT.get(language, {}))
        if missing:
            result.warnings.append(f"localization:{language}:fallback_keys:{len(missing)}")


def _validate_package_spec(root: Path, result: AssetValidationResult) -> None:
    try:
        spec = (root / "Team2050.spec").read_text(encoding="utf-8")
    except OSError as exc:
        result.errors.append(f"package_spec:{exc}")
        return
    for asset in ("data/avatars", "data/theme_backgrounds"):
        if asset not in spec:
            result.errors.append(f"package_spec:missing:{asset}")
