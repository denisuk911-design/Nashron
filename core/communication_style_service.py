from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


_RANGES = {
    "directness": (1, 5), "warmth": (1, 5), "formality": (1, 5), "humor": (0, 5),
    "assertiveness": (1, 5), "verbosity": (1, 5), "initiative": (1, 5), "emotionality": (1, 5),
}
_EXPLANATION_STYLES = {"short", "detailed", "examples", "technical"}
_DISAGREEMENT_STYLES = {"evidence_first", "diplomatic", "direct"}


@dataclass(frozen=True)
class CommunicationStyle:
    directness: int = 3
    warmth: int = 3
    formality: int = 3
    humor: int = 1
    assertiveness: int = 3
    verbosity: int = 2
    initiative: int = 3
    emotionality: int = 3
    explanation_style: str = "short"
    disagreement_style: str = "evidence_first"

    @classmethod
    def from_profile(cls, profile: Mapping[str, object] | None) -> "CommunicationStyle":
        raw = profile or {}
        defaults = cls()
        values: dict[str, object] = {}
        for field, (minimum, maximum) in _RANGES.items():
            try:
                value = int(raw.get(field, getattr(defaults, field)))
            except (TypeError, ValueError):
                value = getattr(defaults, field)
            values[field] = max(minimum, min(maximum, value))
        explanation = str(raw.get("explanation_style", defaults.explanation_style))
        disagreement = str(raw.get("disagreement_style", defaults.disagreement_style))
        values["explanation_style"] = explanation if explanation in _EXPLANATION_STYLES else defaults.explanation_style
        values["disagreement_style"] = disagreement if disagreement in _DISAGREEMENT_STYLES else defaults.disagreement_style
        return cls(**values)

    def as_profile(self) -> dict[str, object]:
        return {field: getattr(self, field) for field in (*_RANGES, "explanation_style", "disagreement_style")}

    def prompt_directive(self, address_name: str) -> str:
        return (
            f"Communication profile for {address_name}: directness {self.directness}/5, warmth {self.warmth}/5, "
            f"formality {self.formality}/5, humor {self.humor}/5, assertiveness {self.assertiveness}/5, "
            f"verbosity {self.verbosity}/5, explanation style {self.explanation_style}, "
            f"disagreement style {self.disagreement_style}. Apply it naturally; do not list these values to the user."
        )

    def directive_for_mode(self, mode: str) -> str:
        """Keep employee tone human without letting a social ping become work chatter."""
        if str(mode).upper() == "SOCIAL":
            return (
                "Social mode: answer the current message naturally and briefly. "
                "Do not volunteer work plans, status reports, or unrelated professional advice."
            )
        return (
            "Work mode: keep the same personal manner, but lead with evidence, the action taken, "
            "and the next decision. Do not add social filler."
        )
