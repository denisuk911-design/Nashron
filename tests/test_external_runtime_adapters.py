from core.external_runtime_adapters import (
    AutoGenRuntimeAdapter,
    ExternalExecutionPayload,
    GoogleAdkRuntimeAdapter,
    LangGraphRuntimeAdapter,
    OpenAIAgentsRuntimeAdapter,
)
from core.runtime_contracts import ExecutionPolicy, ExecutionRequest, RuntimeEventType


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
