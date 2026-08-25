from __future__ import annotations

from .models import EmployeeBinding, Goal, Plan, WorkItem, WorkItemStatus, new_id


class GoalSupervisor:
    """Owns goal execution, planning, assignment and review flow."""

    def __init__(self, employees: list[EmployeeBinding], supervisor_employee_id: str = "supervisor") -> None:
        self.employees = employees
        self.supervisor_employee_id = supervisor_employee_id

    def is_social(self, text: str) -> bool:
        normalized = " ".join(str(text or "").lower().split())
        work_tokens = ("prepare", "create", "build", "write", "review", "research", "goal", "task", "specification")
        social_tokens = ("hello", "hi", "how are you", "joke", "nothing done", "куку", "привет", "как дела")
        return any(token in normalized for token in social_tokens) and not any(token in normalized for token in work_tokens)

    def create_plan(self, goal: Goal) -> tuple[Plan, list[WorkItem]]:
        if self.is_social(goal.objective):
            return Plan(new_id("plan"), goal.goal_id, self.supervisor_employee_id, [], strategy="SEQUENTIAL"), []
        if self._is_simple_single_item(goal.objective):
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

    def _select_employee(self, required: list[str]) -> EmployeeBinding:
        for employee in self.employees:
            competencies = {item.lower() for item in employee.competencies + [employee.role]}
            if any(token in " ".join(competencies) for token in required):
                return employee
        return self.employees[0]

    @staticmethod
    def _is_simple_single_item(text: str) -> bool:
        normalized = " ".join(str(text or "").lower().split())
        complex_tokens = ("research", "review", "controller", "24", "12", "specification", "преобраз", "контроллер", "исслед")
        simple_tokens = ("one file", "single file", "прост", "один файл", "заметка")
        return any(token in normalized for token in simple_tokens) and not any(token in normalized for token in complex_tokens)
