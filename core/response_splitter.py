from __future__ import annotations

import re
from dataclasses import dataclass


_SPEAKER_RE = re.compile(r"(?<![\wА-Яа-яЁё])(Роман|Петр|Пётр)\s*:", re.IGNORECASE)


@dataclass(frozen=True)
class ResponsePart:
    role: str
    content: str


class ResponseSplitter:
    @staticmethod
    def split(text: str, default_role: str, speaker_aliases: dict[str, str] | None = None) -> list[ResponsePart]:
        text = text.strip()
        if not text:
            return []
        aliases = {str(label).strip().lower().replace("ё", "е"): role for label, role in (speaker_aliases or {}).items() if str(label).strip()}
        if aliases:
            labels = sorted(aliases, key=len, reverse=True)
            speaker_re = re.compile(
                rf"(?<![\wА-Яа-яЁё])(?P<label>{'|'.join(re.escape(label) for label in labels)})\s*:",
                re.IGNORECASE,
            )
            matches = list(speaker_re.finditer(text))
        else:
            matches = list(_SPEAKER_RE.finditer(text))
        if not matches:
            return [ResponsePart(default_role, text)]

        parts: list[ResponsePart] = []
        prefix = text[: matches[0].start()].strip()
        if prefix:
            parts.append(ResponsePart(default_role, prefix))

        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            content = text[start:end].strip(" \n\r\t-—")
            if not content:
                continue
            label = match.groupdict().get("label") or match.group(1)
            parts.append(ResponsePart(ResponseSplitter._role_for(label, aliases), content))
        return ResponseSplitter._merge_neighbors(parts)

    @staticmethod
    def has_multiple_speakers(text: str) -> bool:
        return len({_role.group(1).lower().replace("ё", "е") for _role in _SPEAKER_RE.finditer(text)}) > 1

    @staticmethod
    def _role_for(label: str, aliases: dict[str, str] | None = None) -> str:
        normalized = label.lower().replace("ё", "е")
        if aliases and normalized in aliases:
            return aliases[normalized]
        return aliases.get(normalized, normalized.replace(" ", "-")) if aliases else normalized.replace(" ", "-")

    @staticmethod
    def _merge_neighbors(parts: list[ResponsePart]) -> list[ResponsePart]:
        merged: list[ResponsePart] = []
        for part in parts:
            if merged and merged[-1].role == part.role:
                previous = merged[-1]
                merged[-1] = ResponsePart(previous.role, f"{previous.content}\n\n{part.content}")
            else:
                merged.append(part)
        return merged
