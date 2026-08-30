"""Bounded AutoGen model-client run through an OpenAI-compatible Gemini endpoint."""

from __future__ import annotations

import asyncio
import os

from autogen_core.models import ModelFamily, UserMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient


async def main() -> None:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required")
    client = OpenAIChatCompletionClient(
        model="gemini-3.6-flash",
        api_key=key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": True,
            "family": ModelFamily.GPT_4O,
            "structured_output": True,
            "multiple_system_messages": True,
        },
    )
    try:
        result = await asyncio.wait_for(
            client.create([UserMessage(content="Classify as exactly SOCIAL or WORK: prepare a PCB converter specification", source="user")]),
            timeout=25,
        )
        value = str(result.content).strip().upper()
        assert "WORK" in value, f"unexpected model result: {value!r}"
        print("PASS autogen real model classification=WORK")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
