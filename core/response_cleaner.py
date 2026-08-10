from __future__ import annotations

import re


class ResponseCleaner:
    @staticmethod
    def clean(text: str) -> str:
        text = text.strip()
        if not text:
            return ""
        text = ResponseCleaner._remove_repeated_paragraphs(text)
        text = ResponseCleaner._remove_repeated_sentences(text)
        return text.strip()

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
