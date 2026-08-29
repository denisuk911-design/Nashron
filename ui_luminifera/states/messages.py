from __future__ import annotations


STATE_COPY = {
    "ru": {
        "provider_unavailable": ("Провайдер временно недоступен", "Данные в безопасности. Проверьте подключение сотрудника и повторите попытку.", "Повторить"),
        "worker_timeout": ("Ответ занимает больше времени", "Работа не потеряна. Можно подождать, уточнить задачу или остановить ответ.", "Продолжить"),
        "goal_blocked": ("Работа приостановлена", "Команда ждёт решения или дополнительного материала. Проверьте блокер и выберите следующий шаг.", "Проверить работу"),
        "login_required": ("Нужен вход", "Чтобы продолжить, подключите рабочий AI-провайдер в настройках.", "Открыть настройки"),
        "goal_failed": ("Не удалось завершить работу", "Данные и уже созданные материалы сохранены. Проверьте замечания и запустите повторную попытку.", "Открыть работу"),
        "recovery": ("Работа восстановлена", "Состояние проекта сохранено. Можно продолжить с последнего подтверждённого шага.", "Продолжить"),
        "no_organization": ("Рабочее пространство ещё не создано", "Iris поможет собрать команду и начать работу.", "Поговорить с Iris"),
        "no_team": ("Команда ещё не собрана", "Опишите результат, который хотите получить, и Iris предложит специалистов.", "Собрать команду"),
        "no_files": ("Материалов пока нет", "Созданные командой результаты появятся здесь после начала работы.", "Открыть работу"),
        "confirmation": ("Подтвердите действие", "Это действие изменит рабочее пространство. Данные будут затронуты только после вашего подтверждения.", "Подтвердить"),
    },
    "uk": {
        "provider_unavailable": ("Провайдер тимчасово недоступний", "Дані в безпеці. Перевірте підключення працівника та повторіть спробу.", "Повторити"),
        "worker_timeout": ("Відповідь триває довше", "Роботу не втрачено. Можна зачекати, уточнити завдання або зупинити відповідь.", "Продовжити"),
        "goal_blocked": ("Роботу призупинено", "Команда чекає на рішення або додаткові матеріали. Перевірте блокер і виберіть наступний крок.", "Перевірити роботу"),
        "login_required": ("Потрібен вхід", "Щоб продовжити, підключіть робочого AI-провайдера в налаштуваннях.", "Відкрити налаштування"),
        "goal_failed": ("Не вдалося завершити роботу", "Дані та вже створені матеріали збережено. Перевірте зауваження і повторіть спробу.", "Відкрити роботу"),
        "recovery": ("Роботу відновлено", "Стан проєкту збережено. Можна продовжити з останнього підтвердженого кроку.", "Продовжити"),
        "no_organization": ("Робочий простір ще не створено", "Iris допоможе зібрати команду та почати роботу.", "Поговорити з Iris"),
        "no_team": ("Команду ще не зібрано", "Опишіть бажаний результат, і Iris запропонує спеціалістів.", "Зібрати команду"),
        "no_files": ("Матеріалів ще немає", "Результати команди з'являться тут після початку роботи.", "Відкрити роботу"),
        "confirmation": ("Підтвердьте дію", "Ця дія змінить робочий простір. Дані буде змінено лише після вашого підтвердження.", "Підтвердити"),
    },
    "en": {
        "provider_unavailable": ("Provider temporarily unavailable", "Your data is safe. Check the employee connection and try again.", "Retry"),
        "worker_timeout": ("The response is taking longer", "Your work is safe. You can wait, clarify the task, or stop the response.", "Continue"),
        "goal_blocked": ("Work is paused", "The team is waiting for a decision or more input. Review the blocker and choose the next step.", "Review work"),
        "login_required": ("Sign-in required", "Connect a working AI provider in Settings to continue.", "Open settings"),
        "goal_failed": ("Work could not be completed", "Your data and existing materials are safe. Review the findings and try again.", "Open work"),
        "recovery": ("Work restored", "The project state is saved. You can continue from the last confirmed step.", "Continue"),
        "no_organization": ("No workspace yet", "Iris will help you assemble a team and get started.", "Talk to Iris"),
        "no_team": ("No team yet", "Describe the result you want and Iris will suggest specialists.", "Build a team"),
        "no_files": ("No materials yet", "Team results will appear here after work begins.", "Open work"),
        "confirmation": ("Confirm this action", "This action changes the workspace. Nothing is changed until you confirm.", "Confirm"),
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
