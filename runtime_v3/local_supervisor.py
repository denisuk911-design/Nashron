from __future__ import annotations

import os
import subprocess


class LocalSupervisorRuntime:
    """Level-1 local classifier backed by an optional configured executable."""

    def __init__(self, command: str | None = None, timeout_seconds: float = 8.0) -> None:
        self.command = command or os.environ.get("TEAM2050_LOCAL_SUPERVISOR_CMD", "").strip()
        self.timeout_seconds = timeout_seconds

    def decide(self, objective: str) -> str:
        if not self.command:
            return ""
        try:
            result = subprocess.run(
                [self.command, objective], capture_output=True, text=True,
                timeout=self.timeout_seconds, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return ""
        return result.stdout.strip().splitlines()[0].upper() if result.returncode == 0 and result.stdout.strip() else ""
