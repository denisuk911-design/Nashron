from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .beta_recovery_service import BetaRecoveryService
from .build_info import build_info


class FeedbackService:
    """Create local, consented feedback reports without exporting user data."""

    def __init__(self, install_dir: Path) -> None:
        self.install_dir = Path(install_dir)

    def create_report(
        self,
        profile_dir: Path,
        output_path: Path,
        description: str,
        *,
        attach_diagnostics: bool = False,
    ) -> Path:
        if not description.strip():
            raise ValueError("feedback_description_required")
        profile = Path(profile_dir)
        info = build_info()
        feedback: dict[str, Any] = {
            "product": "Team2050",
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "description": description.strip(),
            "build": info,
            "diagnostics_attached": bool(attach_diagnostics),
        }
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("feedback.json", json.dumps(feedback, ensure_ascii=False, indent=2))
            if attach_diagnostics:
                support_path = self.install_dir.parent / ".feedback-support.zip"
                BetaRecoveryService(self.install_dir).create_support_bundle(profile, support_path)
                with zipfile.ZipFile(support_path) as support:
                    archive.writestr("support-report.json", support.read("support-report.json"))
                support_path.unlink(missing_ok=True)
        return output
