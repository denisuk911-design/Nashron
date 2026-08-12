from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from .models import AppPaths


DEFAULT_SETTINGS: dict[str, Any] = {
    "history_message_limit": 20,
    "theme": "dark",
    "codex_timeout_seconds": 180,
    "response_soft_warning_seconds": 20,
    "response_extended_warning_seconds": 90,
    "response_timeout_seconds": 0,
    "allow_local_tools": False,
    "goal_turn_limit": 80,
    "general_chat_response": "SINGLE",
    "workspace_root": str(Path.home() / "Documents" / "Roman2050 Workspace"),
    "reduce_motion": False,
    "interface_language": "ru",
    "user_avatar_path": "",
    "chat_background_path": "",
    "chat_background_opacity": 18,
    "chat_background_mode": "cover",
    "onboarding_skipped": False,
    "developer_mode": False,
}

DEFAULT_RESOURCE_TEXTS: dict[str, str] = {
    "data/roman_identity.json": json.dumps(
        {
            "full_name": "Team2050",
            "current_year": 2050,
            "identity_locked": True,
            "birth_date": None,
            "birth_place": None,
            "current_city": None,
            "profession": None,
            "education": None,
            "family": None,
            "communication_origin": None,
        },
        ensure_ascii=False,
        indent=2,
    ),
    "data/roman_timeline.json": json.dumps(
        {
            "version": 1,
            "events": [],
            "style_notes": [
                "Это нейтральная стартовая конфигурация Team2050 без заранее созданных сотрудников.",
            ],
        },
        ensure_ascii=False,
        indent=2,
    ),
    "data/app_settings.json": json.dumps(DEFAULT_SETTINGS, ensure_ascii=False, indent=2),
    "data/agent_skills.json": json.dumps({}, ensure_ascii=False, indent=2),
    "prompts/roman_system.md": (
        "# Team2050\n\n"
        "Ты отвечаешь как назначенный сотрудник универсальной команды Team2050. "
        "Твоя роль, полномочия, провайдер и область ответственности определяются профилем сотрудника. "
        "Отвечай коротко, по делу и объективно. Не выдумывай выполненную работу и не говори за коллег."
    ),
}


class SettingsService:
    def __init__(self, project_root: Path | None = None, user_dir: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[1]
        self.user_dir = user_dir or self.default_user_dir()
        self.paths = self._build_paths()

    @staticmethod
    def default_user_dir() -> Path:
        override = os.environ.get("ROMAN2050_HOME")
        if override:
            return Path(override)
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "Roman2050"
        return Path.home() / ".roman2050"

    def _build_paths(self) -> AppPaths:
        data_dir = self.user_dir / "data"
        prompts_dir = self.user_dir / "prompts"
        return AppPaths(
            project_root=self.project_root,
            user_dir=self.user_dir,
            data_dir=data_dir,
            prompts_dir=prompts_dir,
            logs_dir=self.user_dir / "logs",
            codex_workspace=self.user_dir / "codex_workspace",
            database_path=self.user_dir / "roman2050.sqlite3",
            identity_path=data_dir / "roman_identity.json",
            identity_backup_path=data_dir / "roman_identity.initial.bak.json",
            timeline_path=data_dir / "roman_timeline.json",
            skills_path=data_dir / "agent_skills.json",
            settings_path=data_dir / "app_settings.json",
            system_prompt_path=prompts_dir / "roman_system.md",
            workspace_root=Path(DEFAULT_SETTINGS["workspace_root"]),
            management_config_dir=self.user_dir / "management",
            avatar_dir=data_dir / "avatars",
        )

    def ensure_user_files(self) -> AppPaths:
        for path in (
            self.paths.data_dir,
            self.paths.prompts_dir,
            self.paths.logs_dir,
            self.paths.codex_workspace,
            self.paths.management_config_dir,
            self.paths.avatar_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
        self._copy_template("data/roman_identity.json", self.paths.identity_path)
        self._copy_template("data/roman_timeline.json", self.paths.timeline_path, overwrite=True)
        self._copy_template("data/agent_skills.json", self.paths.skills_path)
        self._copy_template("data/app_settings.json", self.paths.settings_path)
        self._copy_template("prompts/roman_system.md", self.paths.system_prompt_path, overwrite=True)
        self._copy_avatar_templates()
        return self.paths

    def _copy_template(self, relative_source: str, destination: Path, overwrite: bool = False) -> None:
        source = self.resource_path(relative_source)
        if not source.exists():
            if destination.exists():
                return
            fallback = DEFAULT_RESOURCE_TEXTS.get(relative_source)
            if fallback is None:
                raise FileNotFoundError(source)
            destination.write_text(fallback, encoding="utf-8")
            return
        if overwrite or not destination.exists():
            shutil.copyfile(source, destination)

    def resource_path(self, relative_path: str) -> Path:
        base = Path(getattr(sys, "_MEIPASS", self.project_root))
        return base / relative_path

    def _copy_avatar_templates(self) -> None:
        source_dir = self.resource_path("data/avatars")
        if not source_dir.exists():
            return
        for source in source_dir.glob("*.png"):
            destination = self.paths.avatar_dir / source.name
            if not destination.exists():
                shutil.copyfile(source, destination)

    def load(self) -> dict[str, Any]:
        self.ensure_user_files()
        try:
            data = json.loads(self.paths.settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        settings = DEFAULT_SETTINGS.copy()
        settings.update({k: v for k, v in data.items() if k in DEFAULT_SETTINGS})
        if not settings.get("workspace_root"):
            settings["workspace_root"] = DEFAULT_SETTINGS["workspace_root"]
        return settings

    def save(self, settings: dict[str, Any]) -> None:
        self.ensure_user_files()
        clean = DEFAULT_SETTINGS.copy()
        clean.update({k: settings[k] for k in DEFAULT_SETTINGS.keys() & settings.keys()})
        self.paths.settings_path.write_text(
            json.dumps(clean, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
