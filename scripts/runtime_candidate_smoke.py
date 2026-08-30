"""Offline candidate smoke used from each isolated runtime environment."""

from __future__ import annotations

import argparse
import importlib.metadata
from typing import TypedDict


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", choices=("openai-agents", "langgraph", "google-adk", "autogen"))
    candidate = parser.parse_args().candidate
    if candidate == "openai-agents":
        from agents import Agent

        agent = Agent(name="offline_probe", instructions="Return a short answer.")
        print(f"PASS openai-agents {importlib.metadata.version('openai-agents')} object={agent.name}")
    elif candidate == "langgraph":
        from langgraph.graph import END, START, StateGraph

        class State(TypedDict):
            value: int

        graph = StateGraph(State)
        graph.add_node("increment", lambda state: {"value": state["value"] + 1})
        graph.add_edge(START, "increment")
        graph.add_edge("increment", END)
        value = graph.compile().invoke({"value": 1})["value"]
        assert value == 2
        print(f"PASS langgraph {importlib.metadata.version('langgraph')} graph_value={value}")
    elif candidate == "google-adk":
        from google.adk.agents import LlmAgent

        agent = LlmAgent(name="offline_probe", model="gemini-2.5-flash", instruction="Return a short answer.")
        print(f"PASS google-adk {importlib.metadata.version('google-adk')} object={agent.name}")
    else:
        from autogen_agentchat.agents import AssistantAgent
        from autogen_ext.models.openai import OpenAIChatCompletionClient

        model = OpenAIChatCompletionClient(model="gpt-4o-mini", api_key="probe-not-used")
        agent = AssistantAgent("offline_probe", model_client=model)
        print(f"PASS autogen {importlib.metadata.version('autogen-agentchat')} object={agent.name}")


if __name__ == "__main__":
    main()
