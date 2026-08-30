"""Run the isolated runtime candidate probes and emit a compact JSON matrix."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "QA" / "Runtime" / "BAKEOFF_MATRIX.json")
    args = parser.parse_args()
    commands = {
        "openai-agents": [ROOT / ".runtime_envs/openai-agents/Scripts/python.exe", ROOT / "scripts/runtime_openai_agents_real_smoke.py"],
        "langgraph": [ROOT / ".runtime_envs/langgraph/Scripts/python.exe", ROOT / "scripts/runtime_langgraph_real_smoke.py"],
        "google-adk": [ROOT / ".runtime_envs/google-adk/Scripts/python.exe", ROOT / "scripts/runtime_google_adk_real_smoke.py"],
        "autogen": [ROOT / ".runtime_envs/autogen/Scripts/python.exe", ROOT / "scripts/runtime_autogen_real_smoke.py"],
    }
    results = []
    for candidate, command in commands.items():
        if not command[0].is_file():
            results.append({"candidate": candidate, "status": "NOT_INSTALLED"})
            continue
        environment = os.environ.copy()
        if environment.get("GEMINI_API_KEY") and not environment.get("GOOGLE_API_KEY"):
            environment["GOOGLE_API_KEY"] = environment["GEMINI_API_KEY"]
        if environment.get("GEMINI_API_KEY") and not environment.get("OPENAI_API_KEY"):
            environment["OPENAI_API_KEY"] = environment["GEMINI_API_KEY"]
        completed = subprocess.run(
            [str(part) for part in command], cwd=ROOT, env=environment,
            capture_output=True, text=True, timeout=45,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        results.append({
            "candidate": candidate,
            "status": "PASS" if completed.returncode == 0 else "FAILED",
            "exit_code": completed.returncode,
            "evidence": [line.strip() for line in completed.stdout.splitlines() if line.strip()][-3:],
            "diagnostic": "quota_or_provider_error" if "429" in output or "RESOURCE_EXHAUSTED" in output else "",
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"matrix_version": "1", "results": results}, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
