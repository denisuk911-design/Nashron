from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from runtime_v3.agent_runtime import AgentDecision, DeterministicAgentRuntime
from runtime_v3.engine import HybridWorkflowEngine
from runtime_v3.models import Action, ActionType, EmployeeBinding, GoalStatus, WorkItem, new_id


@dataclass(frozen=True)
class DemoSandboxResult:
    goal_id: str
    status: str
    workspace: Path
    work_items: int
    artifacts: int
    observations: int
    reviews: int

    @property
    def completed(self) -> bool:
        return self.status == GoalStatus.COMPLETED.value


class _DemoRuntime(DeterministicAgentRuntime):
    """Deterministic demo execution that preserves distinct physical outputs."""

    def decide(self, employee_id: str, work_item: WorkItem, attempt: int) -> AgentDecision:
        if "artifact.review" in work_item.required_tools:
            return super().decide(employee_id, work_item, attempt)
        filename = "artifacts/research.md" if "SOURCE_RESEARCH" in work_item.expected_artifact_types else "artifacts/work_product.md"
        return AgentDecision(
            f"Write {filename}",
            [Action(new_id("action"), work_item.work_item_id, employee_id, ActionType.FILESYSTEM_WRITE, {
                "path": filename,
                "content": self._content_for(work_item, attempt),
            })],
        )


class DemoSandboxService:
    """Runs a real, disposable V3 workflow without touching an organization."""

    def __init__(self, profile_dir: Path) -> None:
        self.workspace = Path(profile_dir) / "demo_sandbox"

    def run(self) -> DemoSandboxResult:
        employees = [
            EmployeeBinding(
                "demo-engineer", "Engineer", "engineering", ["engineering", "specification"],
                provider_capabilities=["filesystem.write", "filesystem.read", "structured_output"],
            ),
            EmployeeBinding(
                "demo-researcher", "Researcher", "research", ["research", "components"],
                provider_capabilities=["filesystem.write", "filesystem.read", "structured_output"],
            ),
            EmployeeBinding(
                "demo-reviewer", "Reviewer", "quality", ["review", "qa", "evidence"],
                provider_capabilities=["filesystem.write", "filesystem.read", "structured_output"],
            ),
        ]
        engine = HybridWorkflowEngine(
            "DEMO_SANDBOX",
            employees,
            self.workspace,
            agent_runtime=_DemoRuntime(),
        )
        goal = engine.create_goal("Create a small technical specification with research and quality check")
        engine.create_plan(goal.goal_id)
        state = engine.start(goal.goal_id)
        reviews = sum(action.action_type.value == "artifact.review" for action in state.actions.values())
        return DemoSandboxResult(
            goal_id=goal.goal_id,
            status=state.goals[goal.goal_id].status.value,
            workspace=self.workspace,
            work_items=len(state.work_items),
            artifacts=len(state.artifacts),
            observations=len(state.observations),
            reviews=reviews,
        )
