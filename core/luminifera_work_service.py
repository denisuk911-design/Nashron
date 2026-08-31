"""Read-only product view model for Luminifera Work and Goals."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.agent_directory import list_chat_agents
from core.database import Database
from runtime_v3.models import GoalStatus, WorkItemStatus, load_state


@dataclass(frozen=True)
class WorkArtifact:
    title: str
    status: str


@dataclass(frozen=True)
class WorkStep:
    title: str
    status: str
    is_review: bool = False


@dataclass(frozen=True)
class WorkSnapshot:
    organization_name: str = ""
    team_size: int = 0
    goal_title: str = ""
    goal_state: str = ""
    goal_progress: int = 0
    artifacts: tuple[WorkArtifact, ...] = ()
    findings: int = 0
    evidence_count: int = 0
    receipt_ready: bool = False
    steps: tuple[WorkStep, ...] = ()


@dataclass(frozen=True)
class WorkReceiptView:
    goal_title: str = ""
    completed: bool = False
    artifacts: tuple[str, ...] = ()
    evidence_count: int = 0
    findings_count: int = 0
    review_status: str = ""


@dataclass(frozen=True)
class WorkItemView:
    title: str
    status: str
    assignee: str
    attempt: int
    artifacts: int
    findings: int


@dataclass(frozen=True)
class ReviewFindingView:
    title: str
    severity: str
    status: str
    reviewer: str


@dataclass(frozen=True)
class WorkTimelineEvent:
    message: str
    status: str
    occurred_at: str
    artifact_created: bool = False


class LuminiferaWorkService:
    _PROGRESS = {
        "PENDING": 10,
        "PLANNED": 15,
        "IN_PROGRESS": 50,
        "RUNNING": 50,
        "REVIEW": 75,
        "REWORK": 60,
        "COMPLETED": 100,
        "DONE": 100,
        "FAILED": 0,
        "BLOCKED": 25,
        "CANCELLED": 0,
    }

    def __init__(self, database: Database, runtime_root: Path | None = None) -> None:
        self._database = database
        self._runtime_root = Path(runtime_root) if runtime_root else None

    def snapshot(self, organization_id: str | None) -> WorkSnapshot:
        if not organization_id:
            return WorkSnapshot()
        organization = next((row for row in self._database.list_organizations() if str(row["id"]) == organization_id), None)
        if organization is None:
            return WorkSnapshot()
        runtime_snapshot = self._runtime_snapshot(organization_id, str(organization["name"]))
        if runtime_snapshot is not None:
            return runtime_snapshot
        tasks = self._database.list_tasks(limit=1, organization_id=organization_id)
        artifacts = self._database.list_artifacts(limit=6, organization_id=organization_id)
        findings = self._database.list_findings(limit=100, organization_id=organization_id)
        plans = self._database.list_project_plans(organization_id)
        steps: tuple[WorkStep, ...] = ()
        if plans:
            assignments = self._database.list_work_assignments(str(plans[0]["id"]))
            steps = tuple(
                WorkStep(
                    title=str(row["position"] or row["role_id"] or "Участок работы"),
                    status=str(row["status"] or "ASSIGNED"),
                    is_review=str(row["assignment_type"] or "") == "REVIEW",
                )
                for row in assignments[:8]
            )
        task = tasks[0] if tasks else None
        state = str(task["state"] or "") if task is not None else ""
        return WorkSnapshot(
            organization_name=str(organization["name"]),
            team_size=len(list_chat_agents(self._database, organization_id=organization_id)),
            goal_title=str(task["title"]) if task is not None else "",
            goal_state=state,
            goal_progress=self._PROGRESS.get(state.upper(), 0),
            artifacts=tuple(WorkArtifact(str(row["relative_path"] or row["kind"] or "Результат"), str(row["status"] or "")) for row in artifacts),
            findings=len(findings),
            evidence_count=0,
            receipt_ready=False,
            steps=steps,
        )

    def receipt(self, organization_id: str | None) -> WorkReceiptView:
        if not organization_id or self._runtime_root is None:
            return WorkReceiptView()
        state_path = self._runtime_root / organization_id / "checkpoints" / "state.json"
        if not state_path.is_file():
            return WorkReceiptView()
        try:
            state = load_state(state_path)
        except (OSError, ValueError, KeyError, TypeError):
            return WorkReceiptView()
        goals = sorted(state.goals.values(), key=lambda item: (item.updated_at, item.created_at), reverse=True)
        if not goals:
            return WorkReceiptView()
        goal = goals[0]
        artifacts = tuple(
            Path(item.path).name or item.artifact_type
            for item in state.artifacts.values()
            if item.goal_id == goal.goal_id
        )
        evidence_count = sum(1 for item in state.evidence.values() if item.goal_id == goal.goal_id and item.passed)
        findings_count = sum(1 for item in state.findings.values() if item.goal_id == goal.goal_id)
        receipt = state.work_receipts.get(goal.work_receipt_id) if goal.work_receipt_id else None
        return WorkReceiptView(
            goal_title=goal.objective,
            completed=goal.status == GoalStatus.COMPLETED,
            artifacts=artifacts,
            evidence_count=evidence_count,
            findings_count=findings_count,
            review_status="PASSED" if receipt is not None and goal.status == GoalStatus.COMPLETED else "IN_PROGRESS" if goal.status != GoalStatus.COMPLETED else "NEEDS_ATTENTION",
        )

    def items(self, organization_id: str | None) -> tuple[WorkItemView, ...]:
        if not organization_id or self._runtime_root is None:
            return ()
        state_path = self._runtime_root / organization_id / "checkpoints" / "state.json"
        if not state_path.is_file():
            return ()
        try:
            state = load_state(state_path)
        except (OSError, ValueError, KeyError, TypeError):
            return ()
        goals = sorted(state.goals.values(), key=lambda item: (item.updated_at, item.created_at), reverse=True)
        if not goals:
            return ()
        goal_id = goals[0].goal_id
        names = {
            str(item.get("employee_id", key)): str(item.get("display_name", ""))
            for key, item in state.employee_snapshots.items()
        }
        artifacts = tuple(state.artifacts.values())
        findings = tuple(state.findings.values())
        return tuple(
            WorkItemView(
                title=item.objective,
                status=item.status.value,
                assignee=names.get(item.assigned_employee_id, "Assigned team member"),
                attempt=item.attempt,
                artifacts=sum(artifact.work_item_id == item.work_item_id for artifact in artifacts),
                findings=sum(finding.work_item_id == item.work_item_id for finding in findings),
            )
            for item in state.work_items.values()
            if item.goal_id == goal_id
        )

    def review_findings(self, organization_id: str | None) -> tuple[ReviewFindingView, ...]:
        if not organization_id or self._runtime_root is None:
            return ()
        state_path = self._runtime_root / organization_id / "checkpoints" / "state.json"
        if not state_path.is_file():
            return ()
        try:
            state = load_state(state_path)
        except (OSError, ValueError, KeyError, TypeError):
            return ()
        goals = sorted(state.goals.values(), key=lambda item: (item.updated_at, item.created_at), reverse=True)
        if not goals:
            return ()
        names = {
            str(item.get("employee_id", key)): str(item.get("display_name", ""))
            for key, item in state.employee_snapshots.items()
        }
        return tuple(
            ReviewFindingView(
                title=finding.description,
                severity=finding.severity,
                status=finding.status,
                reviewer=names.get(finding.reviewer_employee_id, "Review team member"),
            )
            for finding in state.findings.values()
            if finding.goal_id == goals[0].goal_id
        )

    def timeline(self, organization_id: str | None) -> tuple[WorkTimelineEvent, ...]:
        """Return a human-facing replay of durable Runtime V3 progress."""
        state = self._load_runtime_state(organization_id)
        if state is None:
            return ()
        goals = sorted(state.goals.values(), key=lambda item: (item.updated_at, item.created_at), reverse=True)
        if not goals:
            return ()
        goal_id = goals[0].goal_id
        messages = {
            "goal_created": ("Цель создана", "planned", False),
            "plan_created": ("План подготовлен", "planned", False),
            "goal_started": ("Работа начата", "working", False),
            "work_item_running": ("Рабочий шаг начат", "working", False),
            "tool_observed": ("Инструмент выполнил действие", "working", False),
            "artifact_created": ("Артефакт сохранён", "working", True),
            "review_requested": ("Результат передан на проверку", "review", False),
            "review_rework_requested": ("Проверка запросила доработку", "rework", False),
            "review_passed": ("Проверка пройдена", "complete", False),
            "work_item_finished": ("Рабочий шаг завершён", "complete", False),
        }
        events = []
        for item in sorted(state.trace_events.values(), key=lambda value: value.created_at):
            if item.goal_id != goal_id:
                continue
            key = next((candidate for candidate in messages if item.stage.startswith(candidate)), None)
            if key is None:
                continue
            message, status, artifact_created = messages[key]
            events.append(WorkTimelineEvent(message, status, item.created_at, artifact_created))
        return tuple(events)

    def _load_runtime_state(self, organization_id: str | None):
        if not organization_id or self._runtime_root is None:
            return None
        state_path = self._runtime_root / organization_id / "checkpoints" / "state.json"
        if not state_path.is_file():
            return None
        try:
            return load_state(state_path)
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def _runtime_snapshot(self, organization_id: str, organization_name: str) -> WorkSnapshot | None:
        """Project the durable V3 checkpoint into the product Work view."""
        if self._runtime_root is None:
            return None
        state_path = self._runtime_root / organization_id / "checkpoints" / "state.json"
        if not state_path.is_file():
            return None
        try:
            state = load_state(state_path)
        except (OSError, ValueError, KeyError, TypeError):
            return None
        goals = sorted(state.goals.values(), key=lambda item: (item.updated_at, item.created_at), reverse=True)
        if not goals:
            return None
        goal = goals[0]
        items = [item for item in state.work_items.values() if item.goal_id == goal.goal_id]
        completed = sum(item.status == WorkItemStatus.COMPLETED for item in items)
        base_progress = self._PROGRESS.get(goal.status.value.upper(), 0)
        progress = 100 if goal.status == GoalStatus.COMPLETED else max(
            base_progress,
            round((completed / len(items)) * 100) if items else 0,
        )
        artifacts = [item for item in state.artifacts.values() if item.goal_id == goal.goal_id]
        findings = [item for item in state.findings.values() if item.goal_id == goal.goal_id]
        receipt = state.work_receipts.get(goal.work_receipt_id) if goal.work_receipt_id else None
        evidence_count = sum(1 for item in state.evidence.values() if item.goal_id == goal.goal_id and item.passed)
        receipt_ready = bool(
            goal.status == GoalStatus.COMPLETED
            and receipt is not None
            and receipt.artifact_ids
            and receipt.evidence_ids
        )
        steps = tuple(
            WorkStep(
                title=item.objective,
                status=item.status.value,
                is_review=any(token in " ".join(item.required_capabilities).lower() for token in ("review", "audit", "evidence", "qa")),
            )
            for item in items[:8]
        )
        team_size = len(state.employee_snapshots)
        if not team_size:
            try:
                team_size = len(list_chat_agents(self._database, organization_id=organization_id))
            except (AttributeError, KeyError, TypeError):
                team_size = 0
        return WorkSnapshot(
            organization_name=organization_name,
            team_size=team_size,
            goal_title=goal.objective,
            goal_state=goal.status.value,
            goal_progress=max(0, min(100, progress)),
            artifacts=tuple(WorkArtifact(Path(item.path).name or item.artifact_type, "verified") for item in artifacts[:6]),
            findings=len(findings),
            evidence_count=evidence_count,
            receipt_ready=receipt_ready,
            steps=steps,
        )
