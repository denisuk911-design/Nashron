"""Reset one local staging profile so owner bootstrap can be exercised again.

This command is deliberately unavailable unless the caller opts into the
staging environment and explicitly confirms the profile reset. It never
touches the production API and keeps the old profile as a timestamped backup.
"""
from __future__ import annotations

import argparse
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


def recover_profile(profile: Path) -> Path:
    if os.environ.get("LUMINIFERA_STAGING", "").lower() != "true":
        raise RuntimeError("LUMINIFERA_STAGING=true is required")
    profile = profile.expanduser().resolve()
    if not profile.name or profile == profile.parent:
        raise RuntimeError("refusing an unsafe profile path")
    if not profile.exists():
        profile.mkdir(parents=True)
        return profile
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = profile.with_name(f"{profile.name}.recovery-{stamp}")
    shutil.move(str(profile), str(backup))
    profile.mkdir(parents=True)
    return backup


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset an explicitly selected Luminifera staging profile.")
    parser.add_argument("--profile", type=Path, required=True, help="staging profile directory")
    parser.add_argument("--confirm-reset", action="store_true", help="confirm moving the current profile to a backup")
    args = parser.parse_args()
    if not args.confirm_reset:
        parser.error("--confirm-reset is required; no files were changed")
    try:
        backup = recover_profile(args.profile)
    except (OSError, RuntimeError) as error:
        parser.error(str(error))
    print(f"staging profile reset: {args.profile.resolve()}")
    print(f"backup preserved: {backup}")
    print("next: start the staging app, then bootstrap the first owner through the normal UI/API")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
