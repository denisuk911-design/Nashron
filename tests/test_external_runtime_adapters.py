from core.external_runtime_adapters import (
    AutoGenRuntimeAdapter,
    ExternalExecutionPayload,
    GoogleAdkRuntimeAdapter,
    LangGraphRuntimeAdapter,
    OpenAIAgentsRuntimeAdapter,
)
from core.runtime_contracts import ExecutionPolicy, ExecutionRequest, RuntimeEventType
from core.external_runtime_adapters import SubprocessRuntimeBridge
import json
import sys


def test_external_adapter_normalizes_observations_and_artifacts():
    request = ExecutionRequest("org-a", "task", ExecutionPolicy.MANAGED_AGENT, correlation_id="corr-1")
    adapter = OpenAIAgentsRuntimeAdapter(
        lambda value: ExternalExecutionPayload(
        True, "completed", artifact_refs=("artifact-1",), evidence_refs=("evidence-1",), observations=("tool ok",)
        , tool_calls=("write_artifact",)
        )
    )
    result = adapter.execute(request)
    assert result.runtime_id == "openai-agents"
    assert [event.event_type for event in result.events] == [
        RuntimeEventType.RUN_STARTED,
        RuntimeEventType.TOOL_CALLED,
        RuntimeEventType.OBSERVATION_RECORDED,
        RuntimeEventType.ARTIFACT_CREATED,
        RuntimeEventType.RUN_COMPLETED,
    ]
    assert result.artifact_refs == ("artifact-1",)
    assert result.evidence_refs == ("evidence-1",)


def test_each_external_adapter_has_distinct_runtime_identity():
    adapters = [
        LangGraphRuntimeAdapter(lambda _: ExternalExecutionPayload(True, "ok")),
        GoogleAdkRuntimeAdapter(lambda _: ExternalExecutionPayload(True, "ok")),
        AutoGenRuntimeAdapter(lambda _: ExternalExecutionPayload(True, "ok")),
    ]
    assert {adapter.runtime_id for adapter in adapters} == {"langgraph", "google-adk", "autogen"}


def test_subprocess_bridge_maps_json_ipc_to_normalized_payload():
    script = (
        "import json,sys; request=json.load(sys.stdin); "
        "print(json.dumps({'ok': True, 'summary': request['objective'], "
        "'tool_calls':['write'], 'observations':['verified'], "
        "'artifact_refs':['artifact-a']}))"
    )
    bridge = SubprocessRuntimeBridge([sys.executable, "-c", script], timeout_seconds=2)
    payload = bridge(ExecutionRequest("org-a", "task", ExecutionPolicy.DIRECT_ACTION))
    assert payload.ok is True
    assert payload.tool_calls == ("write",)
    assert payload.artifact_refs == ("artifact-a",)


def test_subprocess_bridge_rejects_invalid_json():
    bridge = SubprocessRuntimeBridge([sys.executable, "-c", "print('not-json')"], timeout_seconds=2)
    try:
        bridge(ExecutionRequest("org-a", "task", ExecutionPolicy.DIRECT_ACTION))
    except ValueError as error:
        assert "invalid JSON" in str(error)
    else:
        raise AssertionError("invalid subprocess payload must be rejected")


def test_subprocess_bridge_enforces_hard_timeout():
    script = "import time; time.sleep(5)"
    bridge = SubprocessRuntimeBridge([sys.executable, "-c", script], timeout_seconds=0.1)
    try:
        bridge(ExecutionRequest("org-a", "task", ExecutionPolicy.DIRECT_ACTION))
    except TimeoutError:
        raise AssertionError("subprocess timeout must be translated to a bounded failure")
    except __import__("subprocess").TimeoutExpired:
        pass
    else:
        raise AssertionError("hung external runtime must time out")
