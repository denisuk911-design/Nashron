from __future__ import annotations

import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
import traceback

from PySide6.QtCore import QLockFile, QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QMessageBox

from core.management_models import AgentProfile
from core.settings_service import SettingsService
from core.unicode_pipeline import validate_unicode_catalog
from gui.main_window import MainWindow
from gui.startup_splash import StartupSplash


def setup_logging(settings_service: SettingsService) -> logging.Logger:
    paths = settings_service.ensure_user_files()
    logger = logging.getLogger("roman2050")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = RotatingFileHandler(
            paths.logs_dir / "roman2050.log",
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)
    return logger


GOLDEN_GOAL = (
    "Подготовьте техническую спецификацию преобразователя 24 В -> 12 В, 5 А "
    "и подберите подходящий контроллер."
)


def _runtime_v3_smoke_enabled() -> bool:
    return os.environ.get("TEAM2050_RUNTIME_V3_GUI_SMOKE") == "1"


def _prepare_runtime_v3_smoke_settings(settings_service: SettingsService) -> None:
    if not _runtime_v3_smoke_enabled():
        return
    settings = settings_service.load()
    smoke_workspace = os.environ.get("TEAM2050_RUNTIME_V3_GUI_SMOKE_WORKSPACE")
    if not smoke_workspace:
        smoke_workspace = str(settings_service.paths.user_dir / "workspace")
    settings.update(
        {
            "developer_mode": True,
            "runtime_engine": "HYBRID_V3_EXPERIMENTAL",
            "workspace_root": smoke_workspace,
            "interface_language": "ru",
            "onboarding_skipped": True,
        }
    )
    settings_service.save(settings)


def _ensure_runtime_v3_smoke_team(window: MainWindow) -> str:
    organization = window.universal_platform_service.create_organization(
        "Hybrid Runtime V3 Golden",
        purpose="Packaged GUI golden scenario for execution-oriented Runtime V3.",
    )
    organization_id = organization.organization_id
    employees = [
        ("agent-v3-golden-engineer", "Инженер", "DESIGN_ENGINEER", "CODEX_CLI"),
        ("agent-v3-golden-researcher", "Исследователь", "RESEARCH_ASSISTANT", "CODEX_CLI"),
        ("agent-v3-golden-reviewer", "Ревьюер", "QA_ENGINEER", "GEMINI_CLI"),
    ]
    for agent_id, name, role_id, provider_id in employees:
        if window.database.get_agent_profile(agent_id) is None:
            profile = AgentProfile(
                agent_id=agent_id,
                display_name=name,
                description="Runtime V3 packaged golden scenario employee.",
                lifecycle_state="ACTIVE",
                provider_id=provider_id,
                persona_id=f"{agent_id}-persona",
            )
            window.management_service.create_agent(profile, [role_id], ["CHAT"], reason="Runtime V3 packaged GUI smoke")
        window.database.create_organization_member(
            {
                "organization_id": organization_id,
                "agent_id": agent_id,
                "role_id": role_id,
                "position": name,
                "responsibilities": ["Runtime V3 packaged golden scenario"],
                "provider_id": provider_id,
                "assignment_mode": "AUTO_CREATE",
                "provisioning_status": "READY",
                "permissions": ["CHAT"],
            }
        )
    window.database.set_active_organization(organization_id)
    window._activate_organization_live(organization_id)
    return organization_id


class _RecordingRuntimeV3GoalService:
    def __init__(self, wrapped) -> None:
        self.wrapped = wrapped
        self.last_result = None

    def run_goal(self, organization_id, objective, agents):
        self.last_result = self.wrapped.run_goal(organization_id, objective, agents)
        return self.last_result


def _run_runtime_v3_gui_smoke(app: QApplication, window: MainWindow, logger: logging.Logger) -> None:
    report_path = Path(os.environ.get("TEAM2050_RUNTIME_V3_GUI_SMOKE_REPORT") or window.paths.user_dir / "runtime_v3_gui_smoke.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    def finish(code: int, payload: dict) -> None:
        report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        app.exit(code)

    def run() -> None:
        try:
            organization_id = _ensure_runtime_v3_smoke_team(window)
            mode_index = window.chat.mode_selector.findData("goal")
            if mode_index < 0:
                raise RuntimeError("goal_mode_not_available")
            window.chat.mode_selector.setCurrentIndex(mode_index)
            recorder = _RecordingRuntimeV3GoalService(window.runtime_v3_goal_service)
            window.runtime_v3_goal_service = recorder
            handled = window._try_start_runtime_v3_goal(GOLDEN_GOAL, None)
            QApplication.processEvents()
            result = recorder.last_result
            screenshot_path = report_path.with_suffix(".png")
            window.grab().save(str(screenshot_path))
            summary = result.summary if result is not None else ""
            provider_actions = [
                action
                for action in (result.state.actions.values() if result is not None else [])
                if str(action.payload.get("path", "")).replace("\\", "/").startswith("v3_provider_output/")
            ]
            provider_observation_ids = {
                action.action_id
                for action in provider_actions
                if any(
                    observation.action_id == action.action_id and observation.status.value == "OK"
                    for observation in result.state.observations.values()
                )
            } if result is not None else set()
            provider_runs = list(result.state.provider_runs.values()) if result is not None else []
            payload = {
                "ok": bool(handled and result is not None and result.ok),
                "handled_by_gui": handled,
                "organization_id": organization_id,
                "goal": GOLDEN_GOAL,
                "summary": summary,
                "goal_count": len(result.state.goals) if result is not None else 0,
                "work_items": len(result.state.work_items) if result is not None else 0,
                "actions": len(result.state.actions) if result is not None else 0,
                "observations": len(result.state.observations) if result is not None else 0,
                "artifacts": len(result.state.artifacts) if result is not None else 0,
                "evidence": len(result.state.evidence) if result is not None else 0,
                "findings": len(result.state.findings) if result is not None else 0,
                "handoffs": len(result.state.handoffs) if result is not None else 0,
                "provider_actions": len(provider_actions),
                "provider_observations_ok": len(provider_observation_ids),
                "provider_runs": len(provider_runs),
                "provider_run_statuses": sorted(run.status for run in provider_runs),
                "provider_run_action_count": sum(run.action_count for run in provider_runs),
                "message_rows": window.chat.messages.count(),
                "screenshot": str(screenshot_path),
            }
            checks = [
                payload["ok"],
                payload["work_items"] >= 3,
                payload["actions"] >= 3,
                payload["observations"] >= 3,
                payload["artifacts"] >= 2,
                payload["evidence"] >= 3,
                payload["handoffs"] >= 1,
                payload["provider_actions"] >= 1,
                payload["provider_observations_ok"] >= 1,
                payload["provider_runs"] >= 1,
                payload["provider_run_action_count"] >= 1,
                "Цель выполнена" in summary,
                "Артефакты" in summary,
                "Источники" in summary,
                "Проверка" in summary,
            ]
            payload["checks_passed"] = all(checks)
            finish(0 if payload["checks_passed"] else 1, payload)
        except Exception as exc:
            logger.exception("runtime_v3_gui_smoke_failed")
            finish(
                1,
                {
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "traceback": traceback.format_exc(),
                },
            )

    QTimer.singleShot(0, run)


def main() -> int:
    settings_service = SettingsService()
    _prepare_runtime_v3_smoke_settings(settings_service)
    logger = setup_logging(settings_service)
    unicode_errors = validate_unicode_catalog()
    if unicode_errors:
        logger.error("unicode_catalog_invalid errors=%s", ";".join(unicode_errors))
    app = QApplication(sys.argv)
    app.setApplicationName("Team2050")
    app.setOrganizationName("Roman2050")

    lock = QLockFile(str(settings_service.paths.user_dir / "roman2050.lock"))
    lock.setStaleLockTime(30000)
    if not lock.tryLock(100):
        QMessageBox.information(None, "Team2050", "Программа уже запущена")
        return 0

    splash = StartupSplash()
    splash.show()
    app.processEvents()
    splash.set_status("Загружаю настройки и базу данных")
    app.processEvents()
    window = MainWindow(settings_service, logger)
    splash.set_status("Открываю рабочий чат")
    app.processEvents()
    window.show()
    splash.close()
    if _runtime_v3_smoke_enabled():
        _run_runtime_v3_gui_smoke(app, window, logger)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
