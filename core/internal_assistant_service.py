from __future__ import annotations


class Team2050InternalAssistant:
    """System-only diagnostic assistant; it is not an employee or organization member."""

    def __init__(self, provider_health_service) -> None:
        self._provider_health_service = provider_health_service

    def explain_employee_unavailable(self, provider_id: str) -> str:
        health = self._provider_health_service.latest_health(provider_id)
        if health is None:
            health = self._provider_health_service.check_provider(provider_id)
        if health.health_status in {"READY", "AVAILABLE"}:
            return f"Провайдер {provider_id} доступен. Проверьте назначение сотрудника и маршрут сообщения."
        detail = health.diagnostic or "нет подтверждённого состояния провайдера"
        return f"Сотрудник недоступен: провайдер {provider_id} имеет состояние {health.health_status}. Причина: {detail}"
