"""Bounded AutoGen model-client run through an OpenAI-compatible Gemini endpoint."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from autogen_core import CancellationToken
from autogen_core.models import ModelFamily
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient


async def main() -> None:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required")
    client = OpenAIChatCompletionClient(
        model="gemini-3.6-flash",
        api_key=key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        model_info={"vision": False, "function_calling": True, "json_output": True,
                    "family": ModelFamily.GPT_4O, "structured_output": True, "multiple_system_messages": True},
    )
    with tempfile.TemporaryDirectory(prefix="team2050-autogen-tool-") as temp_dir:
        artifact = Path(temp_dir) / "observation.txt"

        def write_observation(content: str) -> str:
            """Write the requested bounded observation artifact."""
            artifact.write_text(content, encoding="utf-8")
            return "artifact written"

        agent = AssistantAgent(
            "runtime_bakeoff_probe", model_client=client, tools=[write_observation],
            system_message="Classify as WORK and call write_observation exactly once with content WORK.",
        )
        try:
            result = await asyncio.wait_for(
                agent.on_messages([TextMessage(content="Prepare a PCB converter specification", source="user")], CancellationToken()),
                timeout=25,
            )
            assert artifact.is_file(), "AutoGen did not execute the write tool"
            assert artifact.read_text(encoding="utf-8") == "WORK"
            print("PASS autogen real model tool observation=WORK")
        finally:
            await client.close()


if __name__ == "__main__":
    asyncio.run(main())
