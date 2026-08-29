from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from core.beta_release_integrity import sign_manifest, verify_release_dir


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build(source: Path, target: Path, version: str) -> tuple[Path, Path]:
    if not (source / "Team2050.exe").is_file():
        raise FileNotFoundError(source / "Team2050.exe")
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    (target / "CHANGELOG.md").write_text(
        f"# Team2050 Beta {version}\n\n"
        "- External user profile is preserved across update, restart and uninstall.\n"
        "- Interrupted updates recover from a rollback snapshot.\n"
        "- Support bundles contain diagnostics only and exclude secrets and chat contents.\n",
        encoding="utf-8",
    )
    (target / "INSTALL.txt").write_text(
        "Team2050 Beta\n\nЗапустите Team2050.exe. Папка профиля хранится отдельно.\n"
        "Для обновления замените содержимое папки установки новым пакетом.\n",
        encoding="utf-8",
    )
    files = {
        str(path.relative_to(target)).replace("\\", "/"): _sha256(path)
        for path in sorted(target.rglob("*"))
        if path.is_file()
    }
    manifest = {
        "product": "Team2050",
        "channel": "beta",
        "version": version,
        "executable": "Team2050.exe",
        "profile_policy": "external_localappdata",
        "legacy_profile_policy": "never_import_Roman2050",
        "files": files,
    }
    manifest["signature"] = sign_manifest(manifest)
    manifest_path = target / "team2050-release.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    archive = target.parent / f"Team2050-Beta-{version}.zip"
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(target.rglob("*")):
            if path.is_file():
                bundle.write(path, Path(target.name) / path.relative_to(target))
    return target, archive


def verify(target: Path) -> bool:
    return verify_release_dir(target)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and verify the final Team2050 Beta release package.")
    parser.add_argument("--source", default=str(ROOT / "dist" / "Team2050"))
    parser.add_argument("--target", default=str(ROOT / "release" / "Team2050-Beta-final"))
    parser.add_argument("--version", default="2.6.0-beta.2")
    args = parser.parse_args()
    target, archive = build(Path(args.source).resolve(), Path(args.target).resolve(), args.version)
    ok = verify(target) and archive.is_file()
    print(json.dumps({"verified": ok, "target": str(target), "archive": str(archive), "version": args.version}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
