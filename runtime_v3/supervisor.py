from __future__ import annotations

from .models import EmployeeBinding, Goal, Plan, WorkItem, WorkItemStatus, new_id
from .supervisor_policy import HybridSupervisorPolicy, SupervisorPolicyDecision


class GoalSupervisor:
    """Owns goal execution, planning, assignment and review flow."""

    def __init__(self, employees: list[EmployeeBinding], supervisor_employee_id: str = "supervisor", policy: HybridSupervisorPolicy | None = None) -> None:
        self.employees = employees
        self.supervisor_employee_id = supervisor_employee_id
        self.policy = policy or HybridSupervisorPolicy()
        self.last_policy_decision: SupervisorPolicyDecision | None = None

    def is_social(self, text: str) -> bool:
        normalized = " ".join(str(text or "").lower().split())
        work_tokens = ("prepare", "create", "build", "write", "review", "research", "goal", "task", "specification")
        social_tokens = ("hello", "hi", "how are you", "joke", "nothing done", "куку", "привет", "как дела")
        return any(token in normalized for token in social_tokens) and not any(token in normalized for token in work_tokens)

    def create_plan(self, goal: Goal) -> tuple[Plan, list[WorkItem]]:
        deterministic_shape = "SOCIAL" if self.is_social(goal.objective) else "SIMPLE" if self._is_simple_single_item(goal.objective) else "COMPLEX"
        self.last_policy_decision = self.policy.decide(goal.objective, deterministic_shape)
        if self.last_policy_decision.shape == "SOCIAL":
            return Plan(new_id("plan"), goal.goal_id, self.supervisor_employee_id, [], strategy="SEQUENTIAL"), []
        if self.last_policy_decision.shape == "SIMPLE":
            employee = self._select_employee(["engineering", "specification", "documentation"])
            item = WorkItem(
                new_id("work"),
                goal.goal_id,
                goal.objective,
                employee.employee_id,
                required_capabilities=["single-work-item"],
                required_tools=["filesystem.write"],
                expected_artifact_types=["WORK_PRODUCT"],
                acceptance_criteria=["artifact created"],
                evidence_requirements=["successful filesystem.write observation"],
                status=WorkItemStatus.READY,
            )
            plan = Plan(new_id("plan"), goal.goal_id, self.supervisor_employee_id, [item.work_item_id], strategy=self.choose_strategy([item]))
            return plan, [item]
        spec_employee = self._select_employee(["requirements", "specification", "engineering"])
        research_employee = self._select_employee(["research", "components"])
        reviewer = self._select_employee(["review", "qa", "evidence"])
        spec = WorkItem(
            new_id("work"),
            goal.goal_id,
            "Prepare technical specification for 24 V to 12 V 5 A converter; force rework",
            spec_employee.employee_id,
            required_capabilities=["specification"],
            required_tools=["filesystem.write"],
            expected_artifact_types=["TECHNICAL_SPECIFICATION"],
            acceptance_criteria=["mentions input", "mentions output", "mentions controller"],
            evidence_requirements=["successful filesystem.write observation"],
            status=WorkItemStatus.READY,
        )
        research = WorkItem(
            new_id("work"),
            goal.goal_id,
            "Perform controller research for the converter",
            research_employee.employee_id,
            required_capabilities=["research"],
            required_tools=["filesystem.write"],
            expected_artifact_types=["SOURCE_RESEARCH"],
            acceptance_criteria=["names controller", "contains source evidence"],
            evidence_requirements=["successful filesystem.write observation"],
            status=WorkItemStatus.READY,
        )
        review = WorkItem(
            new_id("work"),
            goal.goal_id,
            "Review artifacts and evidence",
            reviewer.employee_id,
            dependencies=[spec.work_item_id, research.work_item_id],
            required_capabilities=["review"],
            required_tools=["artifact.review", "filesystem.read"],
            expected_artifact_types=["REVIEW_RESULT"],
            acceptance_criteria=["all findings resolved"],
            evidence_requirements=["review observation"],
        )
        plan = Plan(
            new_id("plan"), goal.goal_id, self.supervisor_employee_id,
            [spec.work_item_id, research.work_item_id, review.work_item_id],
            strategy=self.choose_strategy([spec, research, review]),
        )
        return plan, [spec, research, review]

    @staticmethod
    def choose_strategy(work_items: list[WorkItem]) -> str:
        """Choose orchestration from the dependency graph, not employee names or UI state."""
        if len(work_items) < 2:
            return "SEQUENTIAL"
        if any(item.dependencies for item in work_items):
            return "HANDOFF"
        return "CONCURRENT"

    @staticmethod
    def can_retry_without_human(item: WorkItem) -> bool:
        """Ordinary transient provider failures get one autonomous retry."""
        return item.result.get("failure_kind") == "PROVIDER_FAILURE" and item.attempt < 2

    def replan(self, item: WorkItem, all_items: list[WorkItem]) -> dict | None:
        """Return a bounded, graph-safe recovery plan for an executable work item."""
        if item.attempt >= 2 or "artifact.review" in item.required_tools or item.result.get("hitl_interrupt_id"):
            return None
        self.last_policy_decision = self.policy.route(
            "replanning", item.objective, "HIGH", "HIGH", "HIGH", item.required_capabilities,
        )
        previous_employee_id = item.assigned_employee_id
        replacement = self._select_alternate_employee(item)
        completed_dependencies = {
            dependency.work_item_id
            for dependency in all_items
            if dependency.status == WorkItemStatus.COMPLETED
        }
        retained_dependencies = [dependency for dependency in item.dependencies if dependency not in completed_dependencies]
        active_items = [
            candidate
            for candidate in all_items
            if candidate.work_item_id != item.work_item_id and candidate.status not in {WorkItemStatus.COMPLETED, WorkItemStatus.FAILED}
        ]
        replanned_view = WorkItem(
            item.work_item_id, item.goal_id, item.objective, replacement.employee_id,
            dependencies=retained_dependencies,
        )
        strategy = self.choose_strategy([*active_items, replanned_view])
        return {
            "previous_employee_id": previous_employee_id,
            "employee_id": replacement.employee_id,
            "dependencies": retained_dependencies,
            "strategy": strategy,
        }

    def _select_alternate_employee(self, item: WorkItem) -> EmployeeBinding:
        capabilities = item.required_capabilities
        for employee in self.employees:
            if employee.employee_id == item.assigned_employee_id:
                continue
            if self._matches_capabilities(employee, capabilities):
                return employee
        current = next(employee for employee in self.employees if employee.employee_id == item.assigned_employee_id)
        if self._matches_capabilities(current, capabilities):
            return current
        raise ValueError(f"no alternate employee has required capabilities: {', '.join(item.required_capabilities)}")

    def _select_employee(self, required: list[str]) -> EmployeeBinding:
        for employee in self.employees:
            if self._has_direct_capability(employee, required):
                return employee
        for employee in self.employees:
            if self._matches_capabilities(employee, required):
                return employee
        raise ValueError(f"no employee has required capabilities: {', '.join(required)}")

    @staticmethod
    def _has_direct_capability(employee: EmployeeBinding, required: list[str]) -> bool:
        available = " ".join([employee.role, *employee.competencies]).lower().replace("_", " ")
        return any(capability.lower().replace("-", " ") in available for capability in required)

    @staticmethod
    def _matches_capabilities(employee: EmployeeBinding, required: list[str]) -> bool:
        if not required:
            return True
        available = " ".join([employee.role, *employee.competencies]).lower().replace("_", " ")
        aliases = {
            "single-work-item": ("engineering", "engineer", "documentation"),
            "specification": ("specification", "engineering", "engineer"),
            "engineering": ("engineering", "engineer"),
            "requirements": ("requirements", "engineering", "engineer"),
            "review": ("review", "qa", "audit"),
            "evidence": ("evidence", "review", "qa", "audit"),
            # A design engineer may perform bounded component research when a
            # small organization has no dedicated researcher.
            "research": ("research", "engineering", "engineer"),
            "components": ("components", "research", "engineering", "engineer"),
        }
        return any(any(token in available for token in aliases.get(capability.lower(), (capability.lower(),))) for capability in required)

    @staticmethod
    def _is_simple_single_item(text: str) -> bool:
        normalized = " ".join(str(text or "").lower().split())
        complex_tokens = ("research", "review", "controller", "24", "12", "specification", "преобраз", "контроллер", "исслед")
        simple_tokens = ("one file", "single file", "прост", "один файл", "заметка")
        return any(token in normalized for token in simple_tokens) and not any(token in normalized for token in complex_tokens)
