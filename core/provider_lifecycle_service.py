from __future__ import annotations

import os
import subprocess

from .provider_models import ProviderProfile


class ProviderLifecycleService:
    """Runs only commands shipped in the verified provider catalog."""

    ACTION_FIELDS = {
        "install": "install_command",
        "authenticate": "auth_command",
        "update": "update_command",
        "uninstall": "uninstall_command",
    }

    @classmethod
    def command_for(cls, profile: ProviderProfile, action: str) -> list[str]:
        field = cls.ACTION_FIELDS.get(action)
        if field is None:
            raise ValueError("unknown provider action")
        command = list(getattr(profile, field))
        if not command:
            raise ValueError("action is not available for this integration")
        return command

    @classmethod
    def start(cls, profile: ProviderProfile, action: str) -> subprocess.Popen:
        command = cls.command_for(profile, action)
        creationflags = subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0
        return subprocess.Popen(command, creationflags=creationflags)
