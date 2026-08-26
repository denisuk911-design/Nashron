from core.internal_assistant_service import Team2050InternalAssistant


class Health:
    health_status = "NOT_READY"
    diagnostic = "authentication required"


class HealthService:
    def latest_health(self, provider_id): return Health()
    def check_provider(self, provider_id): raise AssertionError("unexpected")


def test_internal_assistant_explains_provider_failure_without_database_access():
    answer = Team2050InternalAssistant(HealthService()).explain_employee_unavailable("CODEX_CLI")
    assert "CODEX_CLI" in answer and "NOT_READY" in answer and "authentication required" in answer


def test_internal_assistant_projects_runtime_health_from_service_state():
    class RuntimeState:
        employee_snapshots = {"engineer": {"permissions": ["READ_WORKSPACE"]}}
        trace_events = {"trace-1": object()}
        checkpoints = ["checkpoint-1"]

    health = Team2050InternalAssistant(HealthService()).runtime_health(RuntimeState(), ["CODEX_CLI"])

    assert health["providers"] == {"CODEX_CLI": "NOT_READY"}
    assert health["tool_permissions"] == {"engineer": ["READ_WORKSPACE"]}
    assert health["trace_events"] == 1
