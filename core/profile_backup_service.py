from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


class ProfileBackupError(ValueError):
    pass


class ProfileBackupService:
    """Export and restore the portable profile without secure credentials or logs."""

    SCHEMA_VERSION = 1
    ALLOWED_FILES = {
        "team2050.sqlite3",
        "data/app_settings.json",
        "data/roman_identity.json",
        "data/agent_skills.json",
    }

    def backup(self, profile_dir: Path, output_path: Path) -> Path:
        profile = Path(profile_dir)
        files = {name: (profile / name) for name in self.ALLOWED_FILES if (profile / name).is_file()}
        manifest = {
            "product": "Team2050",
            "schema_version": self.SCHEMA_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "files": {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in sorted(files.items())},
            "excluded": ["credentials", "api keys", "tokens", "logs", "chat export outside database"],
        }
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("backup-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            for name, path in sorted(files.items()):
                archive.write(path, name)
        return output

    def restore(self, backup_path: Path, profile_dir: Path) -> None:
        profile = Path(profile_dir)
        with tempfile.TemporaryDirectory(prefix="team2050-restore-") as directory:
            staging = Path(directory)
            try:
                with zipfile.ZipFile(backup_path) as archive:
                    archive.extractall(staging)
                manifest = json.loads((staging / "backup-manifest.json").read_text(encoding="utf-8"))
            except (OSError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
                raise ProfileBackupError("backup_invalid") from exc
            if manifest.get("product") != "Team2050" or manifest.get("schema_version") != self.SCHEMA_VERSION:
                raise ProfileBackupError("backup_schema_unsupported")
            for name, expected in manifest.get("files", {}).items():
                if name not in self.ALLOWED_FILES or not (staging / name).is_file():
                    raise ProfileBackupError("backup_file_not_allowed")
                if hashlib.sha256((staging / name).read_bytes()).hexdigest() != expected:
                    raise ProfileBackupError("backup_integrity_failed")
            database = staging / "team2050.sqlite3"
            if database.is_file():
                connection = sqlite3.connect(database)
                try:
                    if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise ProfileBackupError("backup_database_invalid")
                    if connection.execute("PRAGMA foreign_key_check").fetchall():
                        raise ProfileBackupError("backup_database_foreign_keys_invalid")
                finally:
                    connection.close()
            profile.mkdir(parents=True, exist_ok=True)
            for name in manifest.get("files", {}):
                destination = profile / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(staging / name, destination)
