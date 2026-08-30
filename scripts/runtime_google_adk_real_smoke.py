"""Bounded Google ADK model smoke; credentials are read from the environment."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner


async def main() -> None:
    with tempfile.TemporaryDirectory(prefix="team2050-adk-tool-") as temp_dir:
        artifact = Path(temp_dir) / "observation.txt"

        def write_observation(content: str) -> str:
            """Write the requested bounded observation artifact."""
            artifact.write_text(content, encoding="utf-8")
            return "artifact written"

        agent = LlmAgent(
            name="runtime_bakeoff_probe",
            model="gemini-3.6-flash",
            instruction="Classify as WORK and call write_observation exactly once with content WORK.",
            tools=[write_observation],
        )
        runner = InMemoryRunner(agent=agent, app_name="team2050-runtime-bakeoff")
        events = await asyncio.wait_for(
            runner.run_debug("Prepare a PCB converter specification"),
            timeout=25,
        )
        text = " ".join(str(event).upper() for event in events)
        assert "WORK" in text, "model result did not contain WORK classification"
        assert artifact.is_file(), "Google ADK did not execute the write tool"
        assert artifact.read_text(encoding="utf-8") == "WORK"
    print("PASS google-adk real model tool observation=WORK")


if __name__ == "__main__":
    asyncio.run(main())
