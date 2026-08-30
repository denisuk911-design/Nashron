from dataclasses import dataclass

from core.native_runtime_adapter import NativeRuntimeAdapter
from core.runtime_contracts import (
    EmployeeRef,
    ExecutionPolicy,
    ExecutionRequest,
    RuntimeEventType,
    event_type_from_native_stage,
)


def test_execution_request_uses_semantic_policy_and_product_employee_ref():
    request = ExecutionRequest(
        organization_id="org-a",
        objective="Prepare a converter specification",
        policy=ExecutionPolicy.DYNAMIC_MULTI_AGENT,
        employees=(EmployeeRef("employee-1", "Engineer", "DESIGN_ENGINEER"),),
    )
    assert request.policy is ExecutionPolicy.DYNAMIC_MULTI_AGENT
    assert request.employees[0].employee_id == "employee-1"


def test_empty_execution_request_is_rejected():
    try:
        ExecutionRequest("", "task", ExecutionPolicy.DIRECT_ACTION)
    except ValueError as error:
        assert "organization_id" in str(error)
    else:
        raise AssertionError("empty organization must be rejected")


def test_native_stage_mapping_is_normalized():
    assert event_type_from_native_stage("tool_observed") is RuntimeEventType.OBSERVATION_RECORDED
    assert event_type_from_native_stage("internal_native_stage") is None


def test_native_adapter_preserves_employee_identity_and_returns_product_refs():
    @dataclass
    class Trace:
        stage: str
        employee_id: str = "employee-1"
        work_item_id: str = "work-1"
        detail: str = ""

    @dataclass
    class Goal:
        pass

    class State:
        goals = {"goal-1": Goal()}
        artifacts = {"artifact-1": object()}
        evidence = {"evidence-1": object()}
        trace_events = {"trace-1": Trace("tool_observed")}

    class Result:
        ok = True
        summary = "done"
        state = State()
        workspace_root = "/tmp/native"

    class Service:
        def run_goal(self, organization_id, objective, agents):
            assert organization_id == "org-a"
            assert objective == "task"
            assert [agent.agent_id for agent in agents] == ["agent-1"]
            return Result()

    class Agent:
        agent_id = "agent-1"

    adapter = NativeRuntimeAdapter(Service(), lambda employee: Agent() if employee.employee_id == "employee-1" else None)
    result = adapter.execute(ExecutionRequest(
        "org-a", "task", ExecutionPolicy.DETERMINISTIC_WORKFLOW,
        (EmployeeRef("employee-1", "Engineer", "DESIGN_ENGINEER"),),
    ))
    assert result.runtime_id == "native"
    assert result.artifact_refs == ("artifact-1",)
    assert result.evidence_refs == ("evidence-1",)
    assert result.events[0].event_type is RuntimeEventType.OBSERVATION_RECORDED
