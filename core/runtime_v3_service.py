from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from core.agent_directory import ChatAgent
from runtime_v3 import GoalStatus, HybridWorkflowEngine
from runtime_v3.agent_runtime import ProviderAgentRuntime
from runtime_v3.models import EmployeeBinding, RuntimeState, WorkItemStatus


@dataclass(frozen=True)
class RuntimeV3GoalResult:
    ok: bool
    summary: str
    state: RuntimeState
    workspace_root: Path


class RuntimeV3GoalService:
    """Application boundary for experimental V3 Goal mode."""

    def __init__(self, workspace_root: Path, provider_adapters: dict[str, object] | None = None, permission_resolver=None) -> None:
        self.workspace_root = Path(workspace_root)
        self.provider_adapters = dict(provider_adapters or {})
        self.permission_resolver = permission_resolver

    def run_goal(self, organization_id: str, objective: str, agents: Iterable[ChatAgent]) -> RuntimeV3GoalResult:
        employees = self._employee_bindings(list(agents))
        if not employees:
            employees = [
                EmployeeBinding("employee-engineer", "Инженер", "engineering", ["engineering", "specification"]),
                EmployeeBinding("employee-reviewer", "Проверяющий", "qa", ["review", "qa", "evidence"]),
            ]
        # Production work uses the configured provider. Review stays local and
        # independent so it can actually read the artifacts produced by peers.
        provider_bindings = {
            employee.employee_id: employee.provider_binding_id
            for employee in employees
            if self._is_provider_execution_role(employee)
            and employee.provider_binding_id in self.provider_adapters
        }
        fallback_bindings = {
            employee_id: [provider_id for provider_id in self.provider_adapters if provider_id != primary]
            for employee_id, primary in provider_bindings.items()
        }
        engine = HybridWorkflowEngine(
            organization_id,
            employees,
            self.workspace_root / organization_id,
            agent_runtime=ProviderAgentRuntime(self.provider_adapters, provider_bindings, fallback_bindings) if provider_bindings else None,
        )
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
    def is_explicit_work_intent(text: str) -> bool:
        normalized = " ".join(str(text or "").lower().split())
        social = ("привет", "куку", "как дела", "hello", "hi ", "how are you")
        work = ("сделай", "создай", "проверь", "подготов", "исследуй", "разработ", "create", "build", "review", "prepare", "research")
        return bool(normalized) and not any(token in normalized for token in social) and any(token in normalized for token in work)

    def _employee_bindings(self, agents: list[ChatAgent]) -> list[EmployeeBinding]:
        values: list[EmployeeBinding] = []
        for agent in agents:
            permissions = self.permission_resolver(agent.agent_id) if self.permission_resolver else None
            binding_kwargs = {"permissions": sorted(permissions)} if permissions is not None else {}
            adapter = self.provider_adapters.get(agent.provider_id)
            profile = getattr(adapter, "capability_profile", None)
            provider_capabilities = sorted(getattr(profile, "capabilities", [])) if profile is not None else []
            provider_contract_version = str(getattr(profile, "contract_version", "1.0")) if profile is not None else "1.0"
            values.append(
                EmployeeBinding(
                    agent.agent_id,
                    agent.display_name,
                    agent.primary_role,
                    [agent.primary_role, *agent.roles, agent.engine_name],
                    provider_binding_id=agent.provider_id,
                    provider_capabilities=provider_capabilities,
                    provider_contract_version=provider_contract_version,
                    **binding_kwargs,
                )
            )
        return values

    @staticmethod
    def _is_provider_execution_role(employee: EmployeeBinding) -> bool:
        capabilities = " ".join([employee.role, *employee.competencies]).lower()
        return not any(token in capabilities for token in ("qa", "review", "audit", "evidence"))

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
