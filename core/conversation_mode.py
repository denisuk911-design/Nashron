from __future__ import annotations

from enum import StrEnum


class ConversationMode(StrEnum):
    SOCIAL = "SOCIAL"
    WORK = "WORK"
    MANAGEMENT = "MANAGEMENT"
    REVIEW = "REVIEW"
    TEAM_DISCUSSION = "TEAM_DISCUSSION"


_PAUSE_PHRASES = (
    "стоп работа",
    "пока не работаем",
    "отложи работу",
    "закончим на сегодня",
    "вернемся потом",
    "вернёмся потом",
)
_RESUME_PHRASES = (
    "продолжай работу",
    "продолжай проект",
    "начинай работу",
    "возобнови работу",
    "можно работать",
)
_WORK_MARKERS = (
    "проверь",
    "проверить",
    "создай",
    "создать",
    "сделай",
    "сделать",
    "исправь",
    "исправить",
    "спроектируй",
    "спроектировать",
    "проанализируй",
    "проанализировать",
    "файл",
    "документ",
    "папк",
    "таблиц",
    "проект",
)


def contains_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    lowered = " ".join(str(text or "").lower().split())
    return any(phrase in lowered for phrase in phrases)


def infer_mode(text: str, current: ConversationMode = ConversationMode.SOCIAL) -> ConversationMode:
    if contains_phrase(text, _PAUSE_PHRASES):
        return ConversationMode.SOCIAL
    if contains_phrase(text, _RESUME_PHRASES):
        return ConversationMode.WORK
    lowered = " ".join(str(text or "").lower().split())
    if any(marker in lowered for marker in _WORK_MARKERS):
        return ConversationMode.WORK
    # Work mode is entered by an explicit work request, not inherited by
    # ordinary chat. This prevents a completed task from hijacking greetings
    # and casual questions with stale task context.
    return ConversationMode.SOCIAL
