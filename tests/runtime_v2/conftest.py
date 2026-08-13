import pytest

from runtime_v2.checkpoint_store import JsonCheckpointStore
from runtime_v2.engine import PrototypeWorkflowEngine
from runtime_v2.provider import LocalAgentRuntime, ScriptedProviderAdapter
from runtime_v2.trace import LocalTraceService


@pytest.fixture
def engine_factory(tmp_path):
    def create(*, outcomes=None, disabled_employees=None, result_factory=None):
        providers = {
            "provider-a": ScriptedProviderAdapter("provider-a", outcomes=outcomes, result_factory=result_factory),
            "provider-b": ScriptedProviderAdapter("provider-b", result_factory=result_factory),
        }
        traces = LocalTraceService()
        engine = PrototypeWorkflowEngine(
            JsonCheckpointStore(tmp_path / "checkpoints"),
            LocalAgentRuntime(providers),
            traces,
            disabled_employees=disabled_employees,
        )
        return engine, providers, traces

    return create
