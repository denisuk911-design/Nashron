from __future__ import annotations

from enum import StrEnum


class RunStatus(StrEnum):
    QUEUED = "QUEUED"
    PREPARING_CONTEXT = "PREPARING_CONTEXT"
    STARTING_PROVIDER = "STARTING_PROVIDER"
    WAITING_FOR_PROVIDER = "WAITING_FOR_PROVIDER"
    READING_FILES = "READING_FILES"
    RUNNING_TOOLS = "RUNNING_TOOLS"
    PREPARING_RESPONSE = "PREPARING_RESPONSE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


RUN_STATUS_LABELS = {
    RunStatus.QUEUED: "в очереди",
    RunStatus.PREPARING_CONTEXT: "готовлю контекст",
    RunStatus.STARTING_PROVIDER: "запускаю провайдера",
    RunStatus.WAITING_FOR_PROVIDER: "жду ответа провайдера",
    RunStatus.READING_FILES: "читаю файлы",
    RunStatus.RUNNING_TOOLS: "выполняю инструменты",
    RunStatus.PREPARING_RESPONSE: "готовлю ответ",
    RunStatus.COMPLETED: "завершено",
    RunStatus.FAILED: "ошибка",
    RunStatus.BLOCKED: "заблокировано",
    RunStatus.CANCELLED: "отменено",
    RunStatus.TIMED_OUT: "истёк лимит ожидания",
}


def status_label(status: RunStatus | str) -> str:
    try:
        return RUN_STATUS_LABELS[RunStatus(status)]
    except (KeyError, ValueError):
        return str(status)
