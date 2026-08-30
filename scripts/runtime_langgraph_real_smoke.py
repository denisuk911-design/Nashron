"""Bounded LangGraph execution with a real model call inside a graph node."""

from __future__ import annotations

import os
from typing import TypedDict

from google import genai
from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    prompt: str
    result: str


def main() -> None:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required")
    client = genai.Client(api_key=key)

    def infer(state: State) -> dict[str, str]:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=state["prompt"],
            config={"max_output_tokens": 8},
        )
        value = str(response.text or "").strip().upper()
        if not value and response.candidates and response.candidates[0].content:
            parts = response.candidates[0].content.parts or []
            if parts and parts[0].text:
                value = str(parts[0].text).strip().upper()
        if not value:
            print("EMPTY_RESPONSE", response.model_dump(exclude_none=True))
        return {"result": value}

    graph = StateGraph(State)
    graph.add_node("infer", infer)
    graph.add_edge(START, "infer")
    graph.add_edge("infer", END)
    result = graph.compile().invoke({"prompt": "Classify as exactly SOCIAL or WORK: prepare a PCB converter specification", "result": ""})
    assert "WORK" in result["result"], f"unexpected model result: {result['result']!r}"
    print("PASS langgraph real model classification=WORK")


if __name__ == "__main__":
    main()
