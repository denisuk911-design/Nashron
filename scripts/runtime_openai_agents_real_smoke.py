"""Bounded OpenAI Agents SDK run through an OpenAI-compatible Gemini endpoint."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from openai import AsyncOpenAI
from agents import Agent, OpenAIChatCompletionsModel, Runner, function_tool


async def main() -> None:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required")
    client = AsyncOpenAI(
        api_key=key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        timeout=20,
    )
    with tempfile.TemporaryDirectory(prefix="team2050-openai-tool-") as temp_dir:
        artifact = Path(temp_dir) / "observation.txt"

        @function_tool
        def write_observation(content: str) -> str:
            """Write the requested bounded observation artifact."""
            artifact.write_text(content, encoding="utf-8")
            return "artifact written"

        model = OpenAIChatCompletionsModel(model="gemini-3.6-flash", openai_client=client)
        agent = Agent(
            name="runtime_bakeoff_probe",
            instructions="Classify as WORK and call write_observation exactly once with content WORK.",
            model=model,
            tools=[write_observation],
        )
        result = await asyncio.wait_for(Runner.run(agent, "Prepare a PCB converter specification", max_turns=3), timeout=25)
        assert artifact.is_file(), "SDK did not execute the write tool"
        assert artifact.read_text(encoding="utf-8") == "WORK"
    print("PASS openai-agents real model tool observation=WORK")


if __name__ == "__main__":
    asyncio.run(main())
