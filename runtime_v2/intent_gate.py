from __future__ import annotations

import re

from .models import WorkIntent


class WorkIntentGate:
    """Conservative deterministic gate: chat does not become work by default."""

    _stop = re.compile(r"\b(стоп|останов|отмени|прекрати|stop|cancel)\w*", re.I)
    _review = re.compile(r"\b(проверь|ревью|аудит|review|inspect)\w*", re.I)
    _modify = re.compile(r"\b(измени|исправь|добавь|убери|переделай|change|modify|fix)\w*", re.I)
    _continue = re.compile(r"\b(продолжай|приступай|начинай|выполняй|continue|proceed|start)\w*", re.I)
    _work = re.compile(
        r"\b(создай|разработай|реализуй|подготовь|сделай|выполни|построй|напиши|"
        r"create|build|implement|prepare|execute)\w*",
        re.I,
    )
    _social = re.compile(r"\b(привет|здравств|как дела|анекдот|шутк|hello|hi|joke)\w*", re.I)

    def classify(self, text: str, *, active_workflow: bool = False) -> WorkIntent:
        normalized = " ".join(text.strip().split())
        if not normalized:
            return WorkIntent.SOCIAL
        if self._stop.search(normalized):
            return WorkIntent.WORK_STOP if active_workflow else WorkIntent.DISCUSSION
        if active_workflow and self._modify.search(normalized):
            return WorkIntent.WORK_MODIFICATION
        if active_workflow and self._review.search(normalized):
            return WorkIntent.WORK_REVIEW
        if active_workflow and self._continue.search(normalized):
            return WorkIntent.WORK_CONTINUATION
        if self._work.search(normalized):
            return WorkIntent.WORK_REQUEST
        if self._social.search(normalized):
            return WorkIntent.SOCIAL
        if normalized.endswith("?"):
            return WorkIntent.QUESTION
        return WorkIntent.DISCUSSION
