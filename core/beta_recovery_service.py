from __future__ import annotations

import json
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from .beta_release_integrity import verify_release_dir


class SimulatedUpdateCrash(RuntimeError):
    """Testable equivalent of a process crash during an update."""


class BetaRecoveryService:
    """Crash-safe update transaction and secret-free support bundle builder."""

    def __init__(self, install_dir: Path) -> None:
        self.install_dir = Path(install_dir)
        self.state_path = self.install_dir.parent / "update-state.json"
        self.rollback_root = self.install_dir.parent / ".rollback"

    def update(self, source_dir: Path, version: str, *, simulate_crash: bool = False) -> None:
        source = Path(source_dir)
        if not (source / "Team2050.exe").is_file():
            raise FileNotFoundError(source / "Team2050.exe")
        if not verify_release_dir(source):
            raise ValueError("release_integrity_check_failed")
        backup = self.rollback_root / f"{version}-{uuid.uuid4().hex[:8]}"
        self.rollback_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.install_dir, backup)
        self._write_state("APPLYING", version, backup)
        try:
            shutil.copytree(source, self.install_dir, dirs_exist_ok=True)
            if not verify_release_dir(self.install_dir):
                raise ValueError("release_integrity_check_failed_after_copy")
            if simulate_crash:
                raise SimulatedUpdateCrash("simulated crash after update copy")
            self._write_state("COMPLETED", version, backup)
        except SimulatedUpdateCrash:
            raise
        except Exception:
            self.rollback()
            raise

    def recover(self) -> bool:
        if not self.state_path.is_file():
            return False
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        if state.get("phase") != "APPLYING":
            return False
        self.rollback()
        return True

    def rollback(self) -> None:
        if not self.state_path.is_file():
            return
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        backup = Path(str(state.get("backup", "")))
        if not backup.is_dir():
            raise FileNotFoundError(f"rollback_snapshot_missing:{backup}")
        shutil.rmtree(self.install_dir)
        shutil.copytree(backup, self.install_dir)
        self._write_state("ROLLED_BACK", str(state.get("version", "")), backup)

    def create_support_bundle(self, profile_dir: Path, output_path: Path) -> Path:
        profile = Path(profile_dir)
        database = profile / "team2050.sqlite3"
        foreign_keys: list[tuple] = []
        if database.is_file():
            import sqlite3

            connection = sqlite3.connect(database)
            try:
                foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
            finally:
                connection.close()
        report = {
            "product": "Team2050",
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "database": {"name": database.name, "exists": database.is_file(), "foreign_key_errors": len(foreign_keys)},
            "profile": {"directory_name": profile.name, "settings_exists": (profile / "data" / "app_settings.json").is_file()},
            "installation": {"directory_name": self.install_dir.name, "exists": self.install_dir.is_dir()},
            "secrets_included": False,
            "excluded": ["credentials", "api keys", "cookies", "tokens", "database contents", "chat history"],
        }
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr("support-report.json", json.dumps(report, ensure_ascii=False, indent=2))
        return output

    def _write_state(self, phase: str, version: str, backup: Path) -> None:
        self.state_path.write_text(
            json.dumps({"phase": phase, "version": version, "backup": str(backup)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
