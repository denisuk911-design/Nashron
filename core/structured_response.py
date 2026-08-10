from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


RESPONSE_SCHEMA_VERSION = "1.0"
STRUCTURED_BLOCK_RE = re.compile(
    r"```(?:json)?\s*(\{.*?\})\s*```|(<structured_response>\s*(\{.*?\})\s*</structured_response>)",
    re.IGNORECASE | re.DOTALL,
)
STRUCTURED_START_RE = re.compile(
    r"```(?:json)?\s*\{|(?:^|\n)\s*\{\s*\"schema_version\"\s*:|<structured_response>",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class ParsedAgentResponse:
    human_text: str
    envelope: dict[str, Any] | None = None
    raw_structured: str | None = None
    malformed_structured: str | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def has_valid_envelope(self) -> bool:
        return self.envelope is not None and not self.errors


REQUIRED_FIELDS = {
    "schema_version",
    "agent_id",
    "role",
    "task_id",
    "run_id",
    "action",
    "summary",
}


def parse_agent_response(content: str) -> ParsedAgentResponse:
    """Split a human reply from an optional structured JSON envelope.

    Missing or malformed structured data never drives workflow changes. The raw
    block is returned so callers can preserve it for audit and request repair.
    """

    structured_block = _extract_structured_block(content)
    if structured_block is None:
        raw_object = _extract_leading_json_object(content)
        if raw_object is not None:
            raw, end_index = raw_object
            human = content[end_index:].strip()
            try:
                envelope = json.loads(raw)
            except json.JSONDecodeError as exc:
                return ParsedAgentResponse(
                    human_text="",
                    raw_structured=raw,
                    malformed_structured=raw,
                    errors=[f"malformed_json:{exc.msg}"],
                )
            if isinstance(envelope, dict) and envelope.get("schema_version") == RESPONSE_SCHEMA_VERSION:
                errors = validate_agent_envelope(envelope)
                return ParsedAgentResponse(human_text=human, envelope=envelope, raw_structured=raw, errors=errors)
        embedded_object = _extract_embedded_schema_json_object(content)
        if embedded_object is not None:
            raw, start_index, end_index = embedded_object
            human = (content[:start_index] + content[end_index:]).strip()
            human = _strip_orphan_json_fence(human)
            try:
                envelope = json.loads(raw)
            except json.JSONDecodeError as exc:
                return ParsedAgentResponse(
                    human_text=human,
                    raw_structured=raw,
                    malformed_structured=raw,
                    errors=[f"malformed_json:{exc.msg}"],
                )
            errors = validate_agent_envelope(envelope)
            return ParsedAgentResponse(human_text=human, envelope=envelope, raw_structured=raw, errors=errors)
        fallback = STRUCTURED_START_RE.search(content)
        if fallback is not None:
            return ParsedAgentResponse(
                human_text=content[: fallback.start()].strip(),
                raw_structured=content[fallback.start() :].strip(),
                malformed_structured=content[fallback.start() :].strip(),
                errors=["malformed_or_unclosed_structured_response"],
            )
        return ParsedAgentResponse(human_text=content.strip(), errors=["missing_structured_response"])

    raw, block_start, block_end = structured_block
    human = (content[:block_start] + content[block_end:]).strip()
    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError as exc:
        return ParsedAgentResponse(
            human_text=human,
            raw_structured=raw,
            malformed_structured=raw,
            errors=[f"malformed_json:{exc.msg}"],
        )
    if not isinstance(envelope, dict):
        return ParsedAgentResponse(
            human_text=human,
            raw_structured=raw,
            malformed_structured=raw,
            errors=["structured_response_not_object"],
        )

    errors = validate_agent_envelope(envelope)
    return ParsedAgentResponse(human_text=human, envelope=envelope, raw_structured=raw, errors=errors)


def _extract_structured_block(content: str) -> tuple[str, int, int] | None:
    """Extract a complete JSON object from a fenced audit block.

    A non-greedy regex cannot parse nested JSON objects: it stops at the first
    closing brace inside ``checks`` or ``claims``. Use the JSON decoder to find
    the balanced object, then remove the whole fence from user-facing text.
    """
    decoder = json.JSONDecoder()
    fence_re = re.compile(r"```(?:json)?[ \t]*(?:\r?\n)?", re.IGNORECASE)
    for match in fence_re.finditer(content):
        start = match.end()
        try:
            payload, relative_end = decoder.raw_decode(content[start:])
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        object_end = start + relative_end
        closing = content.find("```", object_end)
        block_end = closing + 3 if closing >= 0 else object_end
        return content[start:object_end].strip(), match.start(), block_end

    tag_re = re.compile(r"<structured_response>\s*", re.IGNORECASE)
    for match in tag_re.finditer(content):
        start = match.end()
        try:
            payload, relative_end = decoder.raw_decode(content[start:])
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        object_end = start + relative_end
        closing_match = re.search(r"</structured_response>", content[object_end:], re.IGNORECASE)
        block_end = object_end + closing_match.end() if closing_match else object_end
        return content[start:object_end].strip(), match.start(), block_end
    return None


def _extract_leading_json_object(content: str) -> tuple[str, int] | None:
    stripped = content.lstrip()
    leading_offset = len(content) - len(stripped)
    if not stripped.startswith("{"):
        return None
    decoder = json.JSONDecoder()
    try:
        payload, end_index = decoder.raw_decode(stripped)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    raw = stripped[:end_index]
    return raw, leading_offset + end_index


def _extract_embedded_schema_json_object(content: str) -> tuple[str, int, int] | None:
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", content):
        start_index = match.start()
        try:
            payload, relative_end = decoder.raw_decode(content[start_index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("schema_version") == RESPONSE_SCHEMA_VERSION:
            end_index = start_index + relative_end
            return content[start_index:end_index], start_index, end_index
    return None


def _strip_orphan_json_fence(text: str) -> str:
    clean = text.strip()
    clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r"\s*```$", "", clean).strip()
    if clean.lower() == "json":
        return ""
    return clean


def validate_agent_envelope(envelope: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(envelope))
    if missing:
        errors.append(f"missing_fields:{','.join(missing)}")
    if envelope.get("schema_version") != RESPONSE_SCHEMA_VERSION:
        errors.append("unsupported_schema_version")
    for key in (
        "files_read",
        "files_created",
        "files_modified",
        "files_deleted",
        "checks",
        "findings",
        "risks",
        "knowledge_used",
        "standards_used",
    ):
        if key in envelope and not isinstance(envelope[key], list):
            errors.append(f"{key}_must_be_list")
    return errors
