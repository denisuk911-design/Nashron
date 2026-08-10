from __future__ import annotations

import re


class ResponseCleaner:
    @staticmethod
    def clean(text: str) -> str:
        text = text.strip()
        if not text:
            return ""
        text = ResponseCleaner._remove_repeated_blocks(text)
        text = ResponseCleaner._remove_repeated_paragraphs(text)
        text = ResponseCleaner._remove_repeated_sentences(text)
        return text.strip()

    @staticmethod
    def _remove_repeated_blocks(text: str) -> str:
        """Collapse a provider that emitted the same complete reply twice."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) >= 2 and len(lines) % 2 == 0:
            half = len(lines) // 2
            if all(ResponseCleaner._same(left, right) for left, right in zip(lines[:half], lines[half:])):
                return "\n".join(lines[:half])

        normalized = ResponseCleaner._norm(text)
        if len(normalized) >= 120 and len(normalized) % 2 == 0:
            midpoint = len(normalized) // 2
            if normalized[:midpoint] == normalized[midpoint:]:
                return text[: len(text) // 2].rstrip()
        return text

    @staticmethod
    def _remove_repeated_paragraphs(text: str) -> str:
        parts = re.split(r"\n\s*\n", text)
        result: list[str] = []
        for part in parts:
            clean = part.strip()
            if not clean:
                continue
            if any(ResponseCleaner._same(previous, clean) for previous in result):
                continue
            result.append(clean)
        return "\n\n".join(result)

    @staticmethod
    def _remove_repeated_sentences(text: str) -> str:
        sentences = re.split(r"(?<=[.!?。])\s+", text)
        result: list[str] = []
        for sentence in sentences:
            clean = sentence.strip()
            if not clean:
                continue
            if any(ResponseCleaner._same(previous, clean) for previous in result):
                continue
            result.append(clean)
        return " ".join(result)

    @staticmethod
    def _same(left: str, right: str) -> bool:
        return ResponseCleaner._norm(left) == ResponseCleaner._norm(right)

    @staticmethod
    def _norm(value: str) -> str:
        return re.sub(r"\W+", "", value, flags=re.UNICODE).lower()
