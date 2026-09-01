"""Run the guarded one-shot owner recovery against a local staging profile."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from core.staging_recovery_service import recover_profile_auth


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset only auth/admin state in a Luminifera staging profile.")
    parser.add_argument("--profile", type=Path, required=True, help="staging profile directory")
    parser.add_argument("--confirm-reset", action="store_true", help="confirm the one-shot reset")
    args = parser.parse_args()
    if os.environ.get("LUMINIFERA_STAGING", "").lower() != "true":
        parser.error("LUMINIFERA_STAGING=true is required; no files were changed")
    if not os.environ.get("LUMINIFERA_STAGING_RESET_ON_BOOT"):
        parser.error("LUMINIFERA_STAGING_RESET_ON_BOOT is required; no files were changed")
    if not args.confirm_reset:
        parser.error("--confirm-reset is required; no files were changed")
    changed = recover_profile_auth(args.profile)
    print("staging auth recovery applied once" if changed else "staging nonce was already used; no changes made")
    print(f"profile: {args.profile.resolve()}")
    print("next: remove LUMINIFERA_STAGING_RESET_ON_BOOT after normal UI/API bootstrap")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
