from __future__ import annotations


def product_failure_message(language: str, *, operation: str = "ответ команды") -> str:
    """Explain a recoverable failure without exposing runtime internals."""
    return {
        "ru": f"Не удалось запустить {operation}. Данные в безопасности. Проверьте подключение провайдера и повторите попытку.",
        "uk": f"Не вдалося запустити {operation}. Дані в безпеці. Перевірте підключення провайдера та повторіть спробу.",
        "en": f"Could not start the {operation}. Your data is safe. Check the provider connection and try again.",
    }.get(language, f"Could not start the {operation}. Your data is safe. Check the provider connection and try again.")
