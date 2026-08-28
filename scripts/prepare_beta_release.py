from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a versioned Team2050 Beta installation bundle.")
    parser.add_argument("--source", default=str(ROOT / "dist" / "Team2050"))
    parser.add_argument("--target", default=str(ROOT / "release" / "Team2050-Beta"))
    parser.add_argument("--version", default="2.6.0-beta.1")
    args = parser.parse_args()
    source = Path(args.source).resolve()
    target = Path(args.target).resolve()
    if not (source / "Team2050.exe").is_file():
        raise SystemExit(f"packaged_exe_not_found:{source / 'Team2050.exe'}")
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    manifest = {
        "product": "Team2050",
        "channel": "beta",
        "version": args.version,
        "executable": "Team2050.exe",
        "profile_policy": "external_localappdata",
        "update_policy": "replace_install_files_preserve_profile",
        "legacy_profile_policy": "never_import_Roman2050",
    }
    (target / "team2050-release.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (target / "README.txt").write_text(
        "Team2050 Beta\n\n"
        "Запустите Team2050.exe. Профиль пользователя хранится отдельно от папки установки.\n"
        "Обновление заменяет только файлы приложения и сохраняет профиль.\n",
        encoding="utf-8",
    )
    print(target / "Team2050.exe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
