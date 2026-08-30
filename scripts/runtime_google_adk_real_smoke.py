"""Bounded Google ADK model smoke; credentials are read from the environment."""

from __future__ import annotations

import asyncio

from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner


async def main() -> None:
    agent = LlmAgent(
        name="runtime_bakeoff_probe",
        model="gemini-3.6-flash",
        instruction="Classify the user message as exactly SOCIAL or WORK. Return only one label.",
    )
    runner = InMemoryRunner(agent=agent, app_name="team2050-runtime-bakeoff")
    events = await asyncio.wait_for(
        runner.run_debug("Prepare a PCB converter specification"),
        timeout=25,
    )
    text = " ".join(str(event).upper() for event in events)
    assert "WORK" in text, "model result did not contain WORK classification"
    print("PASS google-adk real model classification=WORK")


if __name__ == "__main__":
    asyncio.run(main())
