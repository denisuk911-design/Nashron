from core.agent_directory import ChatAgent
from core.iris_orchestration_service import IrisExecutionContext, IrisOrchestrationService
from core.runtime_contracts import ExecutionPolicy, ExecutionResult


def test_iris_is_one_product_boundary_and_passes_explicit_policy():
    seen = {}

    class ExecutionService:
        def execute(self, organization_id, objective, employees, policy, **kwargs):
            seen.update(organization_id=organization_id, objective=objective, policy=policy, kwargs=kwargs)
            return ExecutionResult(True, organization_id, "native", "done", correlation_id=kwargs["correlation_id"])

    employee = ChatAgent("worker", "employee-1", "Worker", "CODEX_CLI", ["CUSTOM_ROLE"], None, "", None)
    service = IrisOrchestrationService(ExecutionService())
    result = service.execute(
        IrisExecutionContext("org-a", conversation_id="conversation-1"),
        "prepare specification",
        [employee],
        ExecutionPolicy.DIRECT_ACTION,
    )
    assert service.product_name == "Iris"
    assert seen["organization_id"] == "org-a"
    assert seen["policy"] is ExecutionPolicy.DIRECT_ACTION
    assert result.correlation_id == "conversation-1"


def test_iris_requires_organization_scope():
    try:
        IrisOrchestrationService(object()).execute(
            IrisExecutionContext(""), "task", [], ExecutionPolicy.CONVERSATIONAL,
        )
    except ValueError as error:
        assert "organization" in str(error)
    else:
        raise AssertionError("organization scope must be required")
