from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from core.agent_directory import ChatAgent
from runtime_v3 import GoalStatus, HybridWorkflowEngine
from runtime_v3.models import EmployeeBinding, RuntimeState, WorkItemStatus


@dataclass(frozen=True)
class RuntimeV3GoalResult:
    ok: bool
    summary: str
    state: RuntimeState
    workspace_root: Path


class RuntimeV3GoalService:
    """Application boundary for experimental V3 Goal mode."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = Path(workspace_root)

    def run_goal(self, organization_id: str, objective: str, agents: Iterable[ChatAgent]) -> RuntimeV3GoalResult:
        employees = self._employee_bindings(list(agents))
        if not employees:
            employees = [
                EmployeeBinding("employee-engineer", "Инженер", "engineering", ["engineering", "specification"]),
                EmployeeBinding("employee-reviewer", "Проверяющий", "qa", ["review", "qa", "evidence"]),
            ]
        engine = HybridWorkflowEngine(organization_id, employees, self.workspace_root / organization_id)
        goal = engine.create_goal(objective)
        engine.create_plan(goal.goal_id)
        state = engine.start(goal.goal_id)
        return RuntimeV3GoalResult(
            ok=state.goals[goal.goal_id].status == GoalStatus.COMPLETED,
            summary=self.project_for_chat(state, goal.goal_id),
            state=state,
            workspace_root=self.workspace_root / organization_id,
        )

    @staticmethod
    def _employee_bindings(agents: list[ChatAgent]) -> list[EmployeeBinding]:
        values: list[EmployeeBinding] = []
        for agent in agents:
            values.append(
                EmployeeBinding(
                    agent.agent_id,
                    agent.display_name,
                    agent.primary_role,
                    [agent.primary_role, *agent.roles, agent.engine_name],
                    provider_binding_id=agent.provider_id,
                )
            )
        return values

    @staticmethod
    def project_for_chat(state: RuntimeState, goal_id: str) -> str:
        goal = state.goals[goal_id]
        work_items = [item for item in state.work_items.values() if item.goal_id == goal_id]
        artifacts = [artifact for artifact in state.artifacts.values() if artifact.goal_id == goal_id]
        source_count = sum(1 for item in state.evidence.values() if item.goal_id == goal_id and item.evidence_type == "SOURCE_RECORD" and item.passed)
        findings = [finding for finding in state.findings.values() if finding.goal_id == goal_id]
        rework_done = any(item.attempt > 1 for item in work_items)
        completed = goal.status == GoalStatus.COMPLETED
        lines = [
            "Цель выполнена." if completed else "Цель пока не завершена.",
            f"План: {len(work_items)} рабочих пункта.",
            f"Артефакты: {len(artifacts)}.",
            f"Источники/доказательства: {source_count}.",
            f"Проверка: {'найдены замечания, исправлены' if findings and rework_done else 'замечаний нет' if not findings else 'есть открытые замечания'}.",
        ]
        if artifacts:
            lines.append("Результаты:")
            for artifact in artifacts:
                path = Path(artifact.path)
                lines.append(f"- {path.name}, ревизия {artifact.revision}")
        blocked = [item for item in work_items if item.status == WorkItemStatus.BLOCKED]
        if blocked:
            lines.append("Есть неподтверждённые заявления, работа не закрыта без действий инструментов.")
        return "\n".join(lines)
