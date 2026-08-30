from core.capability_contracts import (
    CAPABILITY_IDS,
    CapabilityRequest,
    CapabilityToolContract,
    PrivacyMode,
    ToolAvailability,
    ToolExecutionResult,
)
from core.capability_registry import CapabilityRegistry
from core.capability_router import CapabilityRouter
from core.capability_service import CapabilityExecutionService
from core.iris_orchestration_service import IrisExecutionContext, IrisOrchestrationService
from core.runtime_contracts import RuntimeEventType, RuntimeUsage


def _tool(capability: str, tool_id: str, **kwargs):
    return CapabilityToolContract(capability, tool_id, **kwargs)


def test_registry_supports_two_implementations_of_one_capability_and_router_selects_best():
    registry = CapabilityRegistry()
    registry.register(
        _tool("text.reason", "local-reason", privacy_mode=PrivacyMode.LOCAL, historical_reliability=.8),
        lambda request: ToolExecutionResult(True, output={"source": "local"}),
    )
    registry.register(
        _tool("text.reason", "cloud-reason", privacy_mode=PrivacyMode.CLOUD, historical_reliability=.95),
        lambda request: ToolExecutionResult(True, output={"source": "cloud"}),
    )
    router = CapabilityRouter(registry)

    result = router.execute(CapabilityRequest("org-a", "text.reason", constraints={"local_only": True}))

    assert {tool.contract.tool_id for tool in registry.for_capability("text.reason")} == {"local-reason", "cloud-reason"}
    assert result.ok and result.tool_id == "local-reason"
    assert result.output == {"source": "local"}
    assert [event.event_type for event in result.events[:3]] == [
        RuntimeEventType.CAPABILITY_REQUESTED,
        RuntimeEventType.TOOL_SELECTED,
        RuntimeEventType.TOOL_STARTED,
    ]
    assert result.events[-1].event_type is RuntimeEventType.TOOL_COMPLETED


def test_unavailable_primary_uses_compatible_fallback_and_records_telemetry():
    registry = CapabilityRegistry()
    calls = []

    def primary(request):
        calls.append("primary")
        return ToolExecutionResult(False, error=None)

    def fallback(request):
        calls.append("fallback")
        return ToolExecutionResult(True, output="done", usage=RuntimeUsage(input_tokens=2, output_tokens=3))

    registry.register(_tool("code", "primary", historical_reliability=1.0), primary)
    registry.register(_tool("code", "fallback", historical_reliability=.5), fallback)
    result = CapabilityRouter(registry).execute(CapabilityRequest("org-a", "code"))

    assert result.ok and result.fallback_used
    assert calls == ["primary", "fallback"]
    assert result.tool_id == "fallback"
    assert result.usage.input_tokens == 2
    assert any(event.event_type is RuntimeEventType.CAPABILITY_FALLBACK for event in result.events)


def test_not_available_preferred_tool_uses_fallback_without_execution():
    registry = CapabilityRegistry()
    called = []
    registry.register(
        _tool("file.read", "primary", availability=ToolAvailability.NOT_AVAILABLE),
        lambda request: (called.append("primary") or ToolExecutionResult(True)),
    )
    registry.register(
        _tool("file.read", "fallback"),
        lambda request: (called.append("fallback") or ToolExecutionResult(True, output="read")),
    )
    result = CapabilityRouter(registry).execute(
        CapabilityRequest("org-a", "file.read", constraints={"preferred_tool_id": "primary"})
    )
    assert result.ok and result.fallback_used and result.tool_id == "fallback"
    assert called == ["fallback"]
    assert any(event.event_type is RuntimeEventType.CAPABILITY_FALLBACK for event in result.events)


def test_permissions_are_checked_before_executor_and_unavailable_is_not_fake_success():
    registry = CapabilityRegistry()
    called = []
    registry.register(
        _tool("file.write", "writer", permissions=("WRITE_WORKSPACE",)),
        lambda request: (called.append(True) or ToolExecutionResult(True, output="must not run")),
    )
    result = CapabilityRouter(registry).execute(
        CapabilityRequest("org-a", "file.write", permissions=("READ_WORKSPACE",))
    )
    assert not result.ok
    assert result.error and result.error.code == "permission_denied"
    assert not called

    unavailable = CapabilityRouter(CapabilityRegistry()).execute(
        CapabilityRequest("org-a", "video.generate")
    )
    assert not unavailable.ok
    assert unavailable.error and unavailable.error.code == "capability_unavailable"


def test_service_and_iris_request_capability_without_provider_or_runtime_name():
    registry = CapabilityRegistry()
    registry.register(
        _tool("document.read", "document-reader", permissions=("READ_WORKSPACE",)),
        lambda request: ToolExecutionResult(True, output={"text": "verified"}),
    )
    capability_service = CapabilityExecutionService(
        CapabilityRouter(registry),
        permission_resolver=lambda organization_id, employee_id: ("READ_WORKSPACE",),
    )
    iris = IrisOrchestrationService(object(), capability_service)

    result = iris.request_capability(
        IrisExecutionContext("org-a", conversation_id="conversation-7"),
        "document.read",
        {"path": "docs/spec.md"},
        employee_id="employee-1",
    )

    assert result.ok and result.output["text"] == "verified"
    assert result.organization_id == "org-a"
    assert result.events[0].correlation_id == "conversation-7"
    assert not hasattr(result, "provider_id")


def test_contract_lists_the_canonical_capabilities_and_not_available_is_explicit():
    assert "image.generate" in CAPABILITY_IDS
    assert CapabilityToolContract("image.generate", "missing", availability=ToolAvailability.NOT_AVAILABLE).availability is ToolAvailability.NOT_AVAILABLE
