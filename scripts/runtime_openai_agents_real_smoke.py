"""Bounded OpenAI Agents SDK run through an OpenAI-compatible Gemini endpoint."""

from __future__ import annotations

import asyncio
import os

from openai import AsyncOpenAI
from agents import Agent, OpenAIChatCompletionsModel, Runner


async def main() -> None:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required")
    client = AsyncOpenAI(
        api_key=key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        timeout=20,
    )
    model = OpenAIChatCompletionsModel(model="gemini-3.6-flash", openai_client=client)
    agent = Agent(
        name="runtime_bakeoff_probe",
        instructions="Classify the user message as exactly SOCIAL or WORK. Return only one label.",
        model=model,
    )
    result = await asyncio.wait_for(Runner.run(agent, "Prepare a PCB converter specification", max_turns=1), timeout=25)
    value = str(result.final_output).strip().upper()
    assert "WORK" in value, f"unexpected model result: {value!r}"
    print("PASS openai-agents real model classification=WORK")


if __name__ == "__main__":
    asyncio.run(main())
