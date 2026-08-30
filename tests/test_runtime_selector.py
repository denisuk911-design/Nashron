from dataclasses import dataclass

from core.runtime_contracts import ExecutionPolicy, ExecutionRequest, ExecutionResult
from core.runtime_selector import RuntimeSelector


@dataclass
class Adapter:
    runtime_id: str
    calls: int = 0
    fail: bool = False

    def execute(self, request):
        self.calls += 1
        if self.fail:
            raise RuntimeError("candidate failed")
        return ExecutionResult(True, request.organization_id, self.runtime_id, "ok")


def request(policy, **metadata):
    return ExecutionRequest("org-a", "task", policy, metadata=metadata)


def test_selector_keeps_deterministic_workflow_on_native():
    selector = RuntimeSelector({"native": Adapter("native"), "langgraph": Adapter("langgraph")})
    assert selector.select(request(ExecutionPolicy.DETERMINISTIC_WORKFLOW)).runtime_id == "native"


def test_selector_uses_semantic_policy_for_candidates():
    selector = RuntimeSelector({"native": Adapter("native"), "langgraph": Adapter("langgraph")})
    assert selector.select(request(ExecutionPolicy.DYNAMIC_MULTI_AGENT)).runtime_id == "langgraph"


def test_selector_falls_back_without_duplicate_native_call():
    native = Adapter("native")
    candidate = Adapter("langgraph", fail=True)
    selector = RuntimeSelector({"native": native, "langgraph": candidate})
    result = selector.execute(request(ExecutionPolicy.DYNAMIC_MULTI_AGENT))
    assert result.runtime_id == "native"
    assert result.data["fallback_from"] == "langgraph"
    assert native.calls == 1
    assert candidate.calls == 1
