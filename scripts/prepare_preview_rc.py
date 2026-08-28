from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a standalone Team2050 Preview RC folder for manual testing.")
    parser.add_argument("--source", default=str(ROOT / "dist" / "Team2050"))
    parser.add_argument("--target", default=str(ROOT / "release" / "Team2050-Preview-RC"))
    args = parser.parse_args()
    source = Path(args.source).resolve()
    target = Path(args.target).resolve()
    if not (source / "Team2050.exe").is_file():
        raise SystemExit(f"packaged_exe_not_found:{source / 'Team2050.exe'}")
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    (target / "README.txt").write_text(
        "Team2050 Preview RC\n\nRun Team2050.exe. This folder is self-contained; user data is stored outside it.\n",
        encoding="utf-8",
    )
    print(target / "Team2050.exe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
