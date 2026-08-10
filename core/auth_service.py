from __future__ import annotations

import subprocess

from .codex_client import CodexClient
from .models import AuthStatus


class AuthService:
    def __init__(self, client: CodexClient) -> None:
        self.client = client

    def status(self) -> AuthStatus:
        return self.client.login_status()

    def start_login(self) -> subprocess.Popen[str]:
        return self.client.start_login()

    def logout(self) -> AuthStatus:
        return self.client.logout()

