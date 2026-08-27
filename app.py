from __future__ import annotations

import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
import traceback

from PySide6.QtCore import QLockFile, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QMessageBox

from core.management_models import AgentProfile
from core.branding import BRAND_NAME, brand_mark_path
from core.settings_service import SettingsService
from core.unicode_pipeline import validate_unicode_catalog
from gui.main_window import MainWindow
from gui.startup_splash import StartupSplash
from runtime_v3.agent_runtime import AgentDecision
from runtime_v3.engine import HybridWorkflowEngine
from runtime_v3.models import Action, ActionType, EmployeeBinding, Goal, Plan, WorkItem, WorkItemStatus, new_id


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


def _runtime_v3_hitl_smoke_enabled() -> bool:
    return os.environ.get("TEAM2050_RUNTIME_V3_HITL_SMOKE") == "1"


def _admin_smoke_enabled() -> bool:
    return os.environ.get("TEAM2050_ADMIN_SMOKE") == "1"


def _prepare_runtime_v3_smoke_settings(settings_service: SettingsService) -> None:
    if not (_runtime_v3_smoke_enabled() or _runtime_v3_hitl_smoke_enabled()):
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
            artifacts = list(result.state.artifacts.values()) if result is not None else []
            evidence = list(result.state.evidence.values()) if result is not None else []
            review_actions = [
                action
                for action in (result.state.actions.values() if result is not None else [])
                if action.action_type.value == "artifact.review"
            ]
            rework_artifacts = [
                artifact
                for artifact in artifacts
                if artifact.artifact_type == "TECHNICAL_SPECIFICATION" and artifact.revision >= 2
            ]
            passed_source_evidence = [
                item for item in evidence if item.evidence_type == "SOURCE_RECORD" and item.passed
            ]
            completed_work_items = [
                item for item in (result.state.work_items.values() if result is not None else [])
                if item.status.value == "COMPLETED"
            ]
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
                "review_actions": len(review_actions),
                "rework_artifacts": len(rework_artifacts),
                "passed_source_evidence": len(passed_source_evidence),
                "completed_work_items": len(completed_work_items),
                "trace_events": len(result.state.trace_events) if result is not None else 0,
                "permission_snapshots": len(result.state.employee_snapshots) if result is not None else 0,
                "message_rows": window.chat.messages.count(),
                "screenshot": str(screenshot_path),
            }
            checks = [
                payload["ok"],
                payload["work_items"] >= 3,
                payload["actions"] >= 5,
                payload["observations"] >= 5,
                payload["artifacts"] >= 3,
                payload["evidence"] >= 4,
                payload["findings"] >= 1,
                payload["handoffs"] >= 1,
                payload["provider_actions"] >= 2,
                payload["provider_observations_ok"] >= 2,
                payload["provider_runs"] >= 2,
                payload["provider_run_action_count"] >= 2,
                payload["review_actions"] >= 2,
                payload["rework_artifacts"] >= 1,
                payload["passed_source_evidence"] >= 1,
                payload["completed_work_items"] == payload["work_items"],
                payload["trace_events"] >= payload["observations"],
                payload["permission_snapshots"] >= 3,
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


def _run_admin_smoke(app: QApplication, window: MainWindow) -> None:
    report_path = Path(os.environ["TEAM2050_ADMIN_SMOKE_REPORT"])

    def run() -> None:
        before_goals = len(window.runtime_v3_goal_service.workspace_root.glob("**/state.json"))
        answer = window.internal_assistant.explain_employee_unavailable("CODEX_CLI")
        finish(before_goals, answer)

    def finish(before_goals: int, answer: str) -> None:
        payload = {"provider_health_service_used": True, "goals_before": before_goals, "goals_after": len(window.runtime_v3_goal_service.workspace_root.glob("**/state.json")), "work_items": 0, "supervisor_runs": 0, "answer": answer}
        payload["checks_passed"] = payload["goals_before"] == payload["goals_after"] and "провайдер" in payload["answer"].lower()
        report_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        app.exit(0 if payload["checks_passed"] else 1)

    QTimer.singleShot(0, run)


def _run_runtime_v3_hitl_smoke(app: QApplication, window: MainWindow, logger: logging.Logger) -> None:
    report_path = Path(os.environ.get("TEAM2050_RUNTIME_V3_HITL_SMOKE_REPORT") or window.paths.user_dir / "runtime_v3_hitl_smoke.json")
    workspace = Path(os.environ.get("TEAM2050_RUNTIME_V3_GUI_SMOKE_WORKSPACE") or window.paths.user_dir / "workspace") / "hitl"

    class HitlRuntime:
        def decide(self, employee_id, work_item, attempt):
            if work_item.work_item_id == "owner-choice" and not work_item.result.get("owner_decision"):
                return AgentDecision(hitl_request={
                    "question": "Select the validated output option.",
                    "options": ["12 V", "15 V"],
                    "context": "Requirements contain two compatible output variants.",
                })
            return AgentDecision(actions=[Action(
                new_id("action"), work_item.work_item_id, employee_id, ActionType.FILESYSTEM_WRITE,
                {"path": f"artifacts/{work_item.work_item_id}.md", "content": work_item.result.get("owner_decision", "validated")},
            )])

    def finish(code: int, payload: dict) -> None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        app.exit(code)

    def run() -> None:
        try:
            team = [
                EmployeeBinding("hitl-engineer", "Engineer", "engineering", ["engineering"]),
                EmployeeBinding("hitl-researcher", "Researcher", "research", ["research"]),
            ]
            engine = HybridWorkflowEngine("packaged-hitl", team, workspace, agent_runtime=HitlRuntime())
            goal = Goal("goal-hitl", "Resolve an ambiguous validated output choice")
            first = WorkItem("completed-effect", goal.goal_id, "prepare evidence", "hitl-engineer", status=WorkItemStatus.READY)
            choice = WorkItem("owner-choice", goal.goal_id, "choose output", "hitl-researcher", status=WorkItemStatus.READY)
            plan = Plan("plan-hitl", goal.goal_id, "supervisor", [first.work_item_id, choice.work_item_id], strategy="CONCURRENT")
            goal.plan_id = plan.plan_id
            engine.state.goals[goal.goal_id] = goal
            engine.state.plans[plan.plan_id] = plan
            engine.state.work_items = {first.work_item_id: first, choice.work_item_id: choice}
            engine.start(goal.goal_id)
            interrupt = engine.pending_interrupts(goal.goal_id)[0]
            resumed = HybridWorkflowEngine("packaged-hitl", team, workspace, agent_runtime=HitlRuntime())
            resumed.repository = engine.repository
            resumed.resume()
            state = resumed.answer_interrupt(interrupt.interrupt_id, "12 V")
            screenshot_path = report_path.with_suffix(".png")
            window.grab().save(str(screenshot_path))
            payload = {
                "goal_id": goal.goal_id,
                "interrupt_id": interrupt.interrupt_id,
                "question": interrupt.question,
                "options": interrupt.options,
                "owner_decision": state.interrupts[interrupt.interrupt_id].owner_decision,
                "completed_work_items": sum(item.status == WorkItemStatus.COMPLETED for item in state.work_items.values()),
                "actions": len(state.actions),
                "artifacts": len(state.artifacts),
                "pending_interrupts": len(resumed.pending_interrupts(goal.goal_id)),
                "screenshot": str(screenshot_path),
            }
            payload["checks_passed"] = (
                payload["owner_decision"] == "12 V"
                and payload["completed_work_items"] == 2
                and payload["actions"] == 2
                and payload["artifacts"] == 2
                and payload["pending_interrupts"] == 0
            )
            finish(0 if payload["checks_passed"] else 1, payload)
        except Exception as exc:
            logger.exception("runtime_v3_hitl_smoke_failed")
            finish(1, {"checks_passed": False, "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()})

    QTimer.singleShot(0, run)


def main() -> int:
    settings_service = SettingsService()
    _prepare_runtime_v3_smoke_settings(settings_service)
    logger = setup_logging(settings_service)
    unicode_errors = validate_unicode_catalog()
    if unicode_errors:
        logger.error("unicode_catalog_invalid errors=%s", ";".join(unicode_errors))
    app = QApplication(sys.argv)
    app.setApplicationName(BRAND_NAME)
    app.setOrganizationName("Roman2050")
    app.setWindowIcon(QIcon(str(brand_mark_path(settings_service.resource_path(".")))))

    lock = QLockFile(str(settings_service.paths.user_dir / "roman2050.lock"))
    lock.setStaleLockTime(30000)
    if not lock.tryLock(100):
        QMessageBox.information(None, BRAND_NAME, "Программа уже запущена")
        return 0

    splash = StartupSplash(brand_mark_path(settings_service.resource_path(".")))
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
    elif _runtime_v3_hitl_smoke_enabled():
        _run_runtime_v3_hitl_smoke(app, window, logger)
    elif _admin_smoke_enabled():
        _run_admin_smoke(app, window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
