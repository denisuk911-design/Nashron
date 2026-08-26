from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .models import Action, Observation, ObservationStatus, WorkItem, new_id
from .tools import ToolRuntime


@dataclass(frozen=True)
class WorkPackage:
    work_item_id: str
    employee_id: str
    objective: str
    input_artifact_ids: tuple[str, ...] = ()
    correlation_id: str = ""


@dataclass
class WorkerSessionResult:
    actions: list[Action] = field(default_factory=list)
    observations: list[Observation] = field(default_factory=list)
    completed: bool = False
    blocked_reason: str = ""


class WorkerSession:
    """Headless action/observation loop for one WorkItem.

    The session reports progress only through real tool observations. A planner can
    supply many actions; terminal and workspace effects remain inside ToolRuntime.
    """

    def __init__(self, package: WorkPackage, tools: ToolRuntime, max_actions: int = 128) -> None:
        self.package = package
        self.tools = tools
        self.max_actions = max(1, max_actions)

    def run(self, next_action: Callable[[list[Observation]], Action | None]) -> WorkerSessionResult:
        result = WorkerSessionResult()
        for _ in range(self.max_actions):
            action = next_action(list(result.observations))
            if action is None:
                result.completed = bool(result.observations) and all(item.status == ObservationStatus.OK for item in result.observations)
                if not result.completed:
                    result.blocked_reason = "worker finished without verified tool effects"
                return result
            if action.work_item_id != self.package.work_item_id or action.employee_id != self.package.employee_id:
                result.blocked_reason = "worker action does not match its work package"
                return result
            result.actions.append(action)
            observation = self.tools.execute(action)
            result.observations.append(observation)
            if observation.status != ObservationStatus.OK:
                result.blocked_reason = observation.summary
                return result
        result.blocked_reason = "worker action budget exhausted"
        return result

    def action(self, action_type, payload: dict[str, object]) -> Action:
        return Action(new_id("action"), self.package.work_item_id, self.package.employee_id, action_type, payload)
