from __future__ import annotations


class Team2050InternalAssistant:
    """System-only diagnostic assistant; it is not an employee or organization member."""

    def __init__(self, provider_health_service) -> None:
        self._provider_health_service = provider_health_service

    def runtime_health(self, runtime_state, provider_ids: list[str]) -> dict[str, object]:
        """Return an operator-safe control-plane projection through services."""
        providers = {}
        for provider_id in provider_ids:
            health = self._provider_health_service.latest_health(provider_id)
            if health is None:
                health = self._provider_health_service.check_provider(provider_id)
            providers[provider_id] = health.health_status
        return {
            "providers": providers,
            "tool_permissions": {
                employee_id: sorted(snapshot.get("permissions", []))
                for employee_id, snapshot in runtime_state.employee_snapshots.items()
            },
            "trace_events": len(runtime_state.trace_events),
            "checkpoint_count": len(runtime_state.checkpoints),
        }

    def explain_employee_unavailable(self, provider_id: str) -> str:
        health = self._provider_health_service.latest_health(provider_id)
        if health is None:
            health = self._provider_health_service.check_provider(provider_id)
        if health.health_status in {"READY", "AVAILABLE"}:
            return f"Провайдер {provider_id} доступен. Проверьте назначение сотрудника и маршрут сообщения."
        detail = health.diagnostic or "нет подтверждённого состояния провайдера"
        return f"Сотрудник недоступен: провайдер {provider_id} имеет состояние {health.health_status}. Причина: {detail}"
