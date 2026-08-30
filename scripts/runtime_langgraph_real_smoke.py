"""Bounded LangGraph execution with a real model call inside a graph node."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langchain_google_genai import ChatGoogleGenerativeAI


class State(TypedDict):
    prompt: str
    result: str
    artifact: str


def main() -> None:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required")
    model = ChatGoogleGenerativeAI(
        model=os.environ.get("RUNTIME_MODEL", "gemini-3.6-flash"),
        google_api_key=key,
        max_output_tokens=32,
    )

    def infer(state: State) -> dict[str, str]:
        response = model.invoke(state["prompt"])
        return {"result": str(response.content).strip().upper()}

    def write_observation(state: State) -> dict[str, str]:
        artifact = Path.cwd() / ".runtime_langgraph_observation.txt"
        artifact.write_text(f"classification={state['result']}\n", encoding="utf-8")
        return {"artifact": str(artifact)}

    graph = StateGraph(State)
    graph.add_node("infer", infer)
    graph.add_node("write_observation", write_observation)
    graph.add_edge(START, "infer")
    graph.add_edge("infer", "write_observation")
    graph.add_edge("write_observation", END)
    result = graph.compile().invoke({"prompt": "Reply with exactly the single word WORK and nothing else.", "result": "", "artifact": ""})
    assert "WORK" in result["result"], f"unexpected model result: {result['result']!r}"
    assert Path(result["artifact"]).is_file(), "tool observation artifact was not created"
    print("PASS langgraph real model tool observation=WORK")


if __name__ == "__main__":
    main()
