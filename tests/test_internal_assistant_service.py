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
