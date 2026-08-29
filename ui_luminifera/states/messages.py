from __future__ import annotations


STATE_COPY = {
    "ru": {
        "provider_unavailable": ("Провайдер временно недоступен", "Данные в безопасности. Проверьте подключение сотрудника и повторите попытку.", "Повторить"),
        "worker_timeout": ("Ответ занимает больше времени", "Работа не потеряна. Можно подождать, уточнить задачу или остановить ответ.", "Продолжить"),
        "goal_blocked": ("Работа приостановлена", "Команда ждёт решения или дополнительного материала. Проверьте блокер и выберите следующий шаг.", "Проверить работу"),
    },
    "uk": {
        "provider_unavailable": ("Провайдер тимчасово недоступний", "Дані в безпеці. Перевірте підключення працівника та повторіть спробу.", "Повторити"),
        "worker_timeout": ("Відповідь триває довше", "Роботу не втрачено. Можна зачекати, уточнити завдання або зупинити відповідь.", "Продовжити"),
        "goal_blocked": ("Роботу призупинено", "Команда чекає на рішення або додаткові матеріали. Перевірте блокер і виберіть наступний крок.", "Перевірити роботу"),
    },
    "en": {
        "provider_unavailable": ("Provider temporarily unavailable", "Your data is safe. Check the employee connection and try again.", "Retry"),
        "worker_timeout": ("The response is taking longer", "Your work is safe. You can wait, clarify the task, or stop the response.", "Continue"),
        "goal_blocked": ("Work is paused", "The team is waiting for a decision or more input. Review the blocker and choose the next step.", "Review work"),
    },
}


def product_state(language: str, state: str) -> dict[str, str]:
    """Return actionable Product Mode copy without exposing runtime details."""
    language = language if language in STATE_COPY else "en"
    title, body, action = STATE_COPY[language].get(state, STATE_COPY[language]["provider_unavailable"])
    return {"title": title, "body": body, "action": action}


def product_failure_message(language: str, *, operation: str = "ответ команды") -> str:
    """Explain a recoverable failure without exposing runtime internals."""
    return {
        "ru": f"Не удалось запустить {operation}. Данные в безопасности. Проверьте подключение провайдера и повторите попытку.",
        "uk": f"Не вдалося запустити {operation}. Дані в безпеці. Перевірте підключення провайдера та повторіть спробу.",
        "en": f"Could not start the {operation}. Your data is safe. Check the provider connection and try again.",
    }.get(language, f"Could not start the {operation}. Your data is safe. Check the provider connection and try again.")
