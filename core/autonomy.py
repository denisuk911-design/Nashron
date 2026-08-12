from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AutonomyRequest:
    enabled: bool
    goal: str
    complete_on_goal: bool


STOP_WORDS = {
    "стоп",
    "stop",
    "хватит",
    "остановись",
    "остановитесь",
    "прекратите",
    "молчать",
}

DISCUSSION_TRIGGERS = (
    "говорите между собой",
    "говорити между собой",
    "говори между собой",
    "общайтесь между собой",
    "поговорите между собой",
    "обсудите между собой",
    "совещайтесь",
    "обсуждайте",
)

GOAL_TRIGGERS = (
    "цель:",
    "цель -",
    "цель —",
    "пока не выполните",
    "пока не решите",
    "работайте пока",
    "обсуждайте пока",
    "решайте пока",
)

WORK_GOAL_TRIGGERS = (
    "задача",
    "сделай",
    "сделайте",
    "создай",
    "создайте",
    "напиши",
    "подготовь",
    "разработай",
    "собери",
    "проверь",
    "исправь",
    "улучши",
    "обучи",
    "обучайся",
    "обучаться",
    "развивай",
    "развиваться",
    "модернизируй",
    "скилл",
    "skill",
)

HANDOFF_CUES = (
    "review",
    "check",
    "take a look",
    "your turn",
    "continue",
    "проверь",
    "посмотри",
    "оцени",
    "ревью",
    "на просмотр",
    "на проверку",
    "твой ход",
    "подхвати",
    "продолжай",
    "скажи",
    "что скажешь",
    "реагируй",
    "ответь",
    "начинай",
)

UNFINISHED_CUES = (
    "сначала",
    "потом",
    "дальше",
    "следующий ход",
    "следующим ходом",
    "после этого",
    "пока не",
    "не закончил",
    "не закончено",
    "продолжим",
)


def is_stop_command(text: str) -> bool:
    lowered = _compact(text)
    return lowered in STOP_WORDS


def parse_autonomy_request(text: str) -> AutonomyRequest:
    lowered = text.lower()
    discussion = any(trigger in lowered for trigger in DISCUSSION_TRIGGERS)
    goal_mode = (
        any(trigger in lowered for trigger in GOAL_TRIGGERS)
        or lowered.strip().startswith("цель ")
    )
    if not discussion and not goal_mode:
        return AutonomyRequest(False, text.strip(), False)

    goal = _extract_goal(text).strip() or text.strip()
    return AutonomyRequest(True, goal, goal_mode)


def looks_like_work_goal(text: str) -> bool:
    lowered = text.lower()
    return any(trigger in lowered for trigger in WORK_GOAL_TRIGGERS)


def detect_peer_handoff(text: str, current_agent: str) -> str | None:
    return None


def has_handoff_intent(text: str) -> bool:
    lowered = text.lower()
    return any(cue in lowered for cue in HANDOFF_CUES)


def looks_unfinished(text: str) -> bool:
    lowered = text.lower()
    if "auto_done" in lowered:
        return False
    return any(cue in lowered for cue in UNFINISHED_CUES)


def _extract_goal(text: str) -> str:
    lowered = text.lower()
    for marker in ("цель:", "цель -", "цель —"):
        index = lowered.find(marker)
        if index >= 0:
            return text[index + len(marker) :].strip()
    return text


def _compact(text: str) -> str:
    return " ".join(text.lower().strip().split())
