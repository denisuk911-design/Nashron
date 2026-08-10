from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    project_root: Path
    user_dir: Path
    data_dir: Path
    prompts_dir: Path
    logs_dir: Path
    codex_workspace: Path
    database_path: Path
    identity_path: Path
    identity_backup_path: Path
    timeline_path: Path
    skills_path: Path
    settings_path: Path
    system_prompt_path: Path
    workspace_root: Path
    management_config_dir: Path
    avatar_dir: Path


@dataclass(frozen=True)
class Conversation:
    id: int
    title: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Message:
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: str
    status: str


@dataclass(frozen=True)
class UserMemory:
    id: int
    content: str
    created_at: str


@dataclass(frozen=True)
class AuthStatus:
    codex_found: bool
    authorized: bool
    message: str
    returncode: int | None = None


@dataclass(frozen=True)
class CodexResult:
    ok: bool
    content: str
    returncode: int | None
    duration_seconds: float
    error: str | None = None
    cancelled: bool = False


@dataclass(frozen=True)
class AgentSpec:
    key: str
    display_name: str
    engine_name: str
    voice: str
