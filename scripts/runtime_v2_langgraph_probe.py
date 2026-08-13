"""Optional packaging probe; requires LangGraph on the import path."""

from __future__ import annotations

from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph


class ProbeState(TypedDict, total=False):
    completed: bool


def main() -> int:
    graph = StateGraph(ProbeState)
    graph.add_node("work", lambda state: {**state, "completed": True})
    graph.add_edge(START, "work")
    graph.add_edge("work", END)
    app = graph.compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "windows-package-probe"}}
    result = app.invoke({}, config)
    return 0 if result.get("completed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
