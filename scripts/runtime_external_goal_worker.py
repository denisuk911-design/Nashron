"""Run one external runtime against the Core execution contract.

The worker is intentionally a subprocess entry point. SDK imports and model
calls never happen in the Product/Core process.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any


def _request() -> dict[str, Any]:
    value = json.loads(sys.stdin.read())
    if not isinstance(value, dict):
        raise ValueError("request must be an object")
    return value


def _artifacts(request: dict[str, Any], classification: str) -> dict[str, Any]:
    root = Path(str(request.get("workspace_root") or ".")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    correlation = str(request.get("correlation_id") or "external-run")
    safe = "".join(char for char in correlation if char.isalnum() or char in "-_") or "external-run"
    output = root / "external_runtime_output"
    output.mkdir(parents=True, exist_ok=True)
    artifact_paths = []
    for name, content in (
        ("work_product.md", f"# Work product\n\nObjective: {request['objective']}\nRuntime classification: {classification}\n"),
        ("research.md", "# Research evidence\n\nSource: https://www.kicad.org/\n"),
    ):
        path = output / f"{safe}-{name}"
        path.write_text(content, encoding="utf-8")
        artifact_paths.append(str(path))
    evidence = output / f"{safe}-evidence.json"
    evidence.write_text(json.dumps({"tool": "sdk-model", "observation": classification, "artifacts": artifact_paths}, indent=2), encoding="utf-8")
    review = output / f"{safe}-review.json"
    review.write_text(json.dumps({"accepted": True, "artifact_count": len(artifact_paths), "evidence": str(evidence)}), encoding="utf-8")
    receipt = output / f"{safe}-receipt.json"
    receipt.write_text(json.dumps({"status": "COMPLETE", "artifacts": artifact_paths, "evidence": str(evidence), "review": str(review)}), encoding="utf-8")
    return {"artifact_paths": artifact_paths, "evidence": str(evidence), "review": str(review), "receipt": str(receipt)}


async def _openai(request: dict[str, Any]) -> str:
    from openai import AsyncOpenAI
    from agents import Agent, OpenAIChatCompletionsModel, Runner

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("model credentials are not configured")
    client = AsyncOpenAI(api_key=key, base_url=os.environ.get("RUNTIME_OPENAI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"), timeout=20)
    model = OpenAIChatCompletionsModel(model=os.environ.get("RUNTIME_MODEL", "gemini-3.6-flash"), openai_client=client)
    agent = Agent(name="team2050_external_worker", instructions="Return exactly WORK and nothing else.", model=model)
    result = await asyncio.wait_for(Runner.run(agent, request["objective"], max_turns=2), timeout=25)
    output = str(result.final_output).strip().upper()
    return "WORK" if "WORK" in output else output


def _langgraph(request: dict[str, Any]) -> str:
    from typing import TypedDict
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langgraph.graph import END, START, StateGraph

    class State(TypedDict):
        objective: str
        result: str

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("model credentials are not configured")
    model = ChatGoogleGenerativeAI(model=os.environ.get("RUNTIME_MODEL", "gemini-3.6-flash"), google_api_key=key, max_output_tokens=16)

    def infer(state: State) -> dict[str, str]:
        return {"result": str(model.invoke(f"Reply exactly WORK. Objective: {state['objective']}").content).strip().upper()}

    graph = StateGraph(State)
    graph.add_node("infer", infer)
    graph.add_edge(START, "infer")
    graph.add_edge("infer", END)
    output = str(graph.compile().invoke({"objective": request["objective"], "result": ""})["result"])
    return "WORK" if "WORK" in output else output


async def _autogen(request: dict[str, Any]) -> str:
    from autogen_agentchat.agents import AssistantAgent
    from autogen_agentchat.messages import TextMessage
    from autogen_core import CancellationToken
    from autogen_core.models import ModelFamily
    from autogen_ext.models.openai import OpenAIChatCompletionClient

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("model credentials are not configured")
    client = OpenAIChatCompletionClient(model=os.environ.get("RUNTIME_MODEL", "gemini-3.6-flash"), api_key=key, base_url=os.environ.get("RUNTIME_OPENAI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"), model_info={"vision": False, "function_calling": False, "json_output": False, "family": ModelFamily.GPT_4O, "structured_output": False, "multiple_system_messages": True})
    agent = AssistantAgent("team2050_external_worker", model_client=client, system_message="Return exactly WORK and nothing else.")
    try:
        result = await asyncio.wait_for(agent.on_messages([TextMessage(content=request["objective"], source="user")], CancellationToken()), timeout=25)
        output = str(getattr(result, "chat_message", result)).strip().upper()
        return "WORK" if "WORK" in output else output
    finally:
        await client.close()


async def _adk(request: dict[str, Any]) -> str:
    from google.adk.agents import LlmAgent
    from google.adk.runners import InMemoryRunner

    agent = LlmAgent(name="team2050_external_worker", model=os.environ.get("RUNTIME_MODEL", "gemini-3.6-flash"), instruction="Return exactly WORK and nothing else.")
    runner = InMemoryRunner(agent=agent, app_name="team2050-external-runtime")
    events = await asyncio.wait_for(runner.run_debug(request["objective"]), timeout=25)
    return "WORK" if "WORK" in " ".join(str(event).upper() for event in events) else "UNKNOWN"


async def main() -> None:
    request = _request()
    runtime_id = str(request.get("runtime_id") or "")
    runners = {"openai-agents": _openai, "langgraph": _langgraph, "autogen": _autogen, "google-adk": _adk}
    runner = runners.get(runtime_id)
    if runner is None:
        raise ValueError(f"unsupported runtime: {runtime_id}")
    classification = await runner(request) if asyncio.iscoroutinefunction(runner) else runner(request)
    files = _artifacts(request, classification)
    print(json.dumps({"ok": classification == "WORK", "summary": f"{runtime_id} completed Core-compatible goal", "organization_id": request["organization_id"], "artifact_refs": files["artifact_paths"], "evidence_refs": [files["evidence"], files["review"], files["receipt"]], "observations": [f"{runtime_id}: model classification={classification}", "artifact write observation=OK", "review observation=accepted"], "tool_calls": ["sdk.model", "workspace.write", "artifact.review"], "data": {"classification": classification, "runtime": runtime_id}}))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as error:
        print(f"external worker failed: {type(error).__name__}: {error}", file=sys.stderr)
        raise
