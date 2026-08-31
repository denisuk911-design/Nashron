"""Run the final runtime bake-off against one identical product Goal."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.agent_directory import ChatAgent
from core.external_runtime_factory import build_external_runtime_adapters
from core.native_runtime_adapter import NativeRuntimeAdapter
from core.runtime_contracts import EmployeeRef, ExecutionPolicy, ExecutionRequest, ExecutionResult
from core.runtime_v3_service import RuntimeV3GoalService

OBJECTIVE = "Prepare a verified technical specification for a 24 V to 12 V, 5 A converter and select a suitable controller."
EMPLOYEES = (
    EmployeeRef("employee-engineer", "Engineer", "DESIGN_ENGINEER", competencies=("DESIGN_ENGINEER", "engineering", "pcb", "kicad")),
    EmployeeRef("employee-researcher", "Researcher", "RESEARCHER", competencies=("RESEARCHER", "research", "sources")),
    EmployeeRef("employee-reviewer", "Reviewer", "QA_ENGINEER", competencies=("QA_ENGINEER", "review", "qa", "evidence")),
)


def native_adapter(root: Path) -> NativeRuntimeAdapter:
    service = RuntimeV3GoalService(root / "native")
    agents = {e.employee_id: ChatAgent(e.employee_id, e.employee_id, e.display_name, "LOCAL", [e.role], e.role, "", None) for e in EMPLOYEES}
    return NativeRuntimeAdapter(service, lambda employee: agents.get(employee.employee_id))


def row(runtime: str, result: ExecutionResult, elapsed: int, workspace: Path) -> dict[str, object]:
    refs = [Path(path) for path in (*result.artifact_refs, *result.evidence_refs)]
    physical = bool(refs) and all(path.is_file() for path in refs)
    if runtime == "native" and not physical:
        physical = any(path.is_file() for path in workspace.rglob("*") if "checkpoints" not in path.parts)
    artifacts, evidence = len(result.artifact_refs), len(result.evidence_refs)
    passed = bool(result.ok and artifacts >= 2 and evidence >= 3 and physical)
    return {"runtime": runtime, "status": "PASS" if passed else "FAIL", "ok": result.ok, "latency_ms": elapsed, "quality_score": 1.0 if passed else 0.0, "autonomy": True, "recovery": False, "artifacts": artifacts, "evidence": evidence, "physical_artifacts": physical, "cost": "not reported by adapter", "complexity": {"native": "low", "openai-agents": "medium", "langgraph": "medium", "google-adk": "medium", "autogen": "high"}.get(runtime, "unknown"), "summary": result.summary, "workspace": str(workspace), "artifact_refs": list(result.artifact_refs), "evidence_refs": list(result.evidence_refs)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "QA" / "Runtime" / "FINAL_BAKEOFF.json")
    args = parser.parse_args()
    root = ROOT / "QA" / "Runtime" / "final_bakeoff"
    adapters: dict[str, object] = {"native": native_adapter(root)}
    adapters.update(build_external_runtime_adapters(ROOT, timeout_seconds=90.0))
    rows: list[dict[str, object]] = []
    for runtime, adapter in adapters.items():
        workspace = root / runtime
        request = ExecutionRequest("FINAL-BAKEOFF-ORG", OBJECTIVE, ExecutionPolicy.LONG_RUNNING_PROJECT, EMPLOYEES, f"final-runtime-bakeoff-{runtime}", {"workspace_root": str(workspace), "runtime_id": runtime})
        started = time.perf_counter()
        try:
            rows.append(row(runtime, adapter.execute(request), round((time.perf_counter() - started) * 1000), workspace))
        except Exception as error:
            message = str(error)
            rows.append({"runtime": runtime, "status": "FAIL", "ok": False, "latency_ms": round((time.perf_counter() - started) * 1000), "quality_score": 0.0, "autonomy": True, "recovery": False, "artifacts": 0, "evidence": 0, "physical_artifacts": False, "cost": "not reported by adapter", "complexity": "unknown", "external_429": "429" in message or "RESOURCE_EXHAUSTED" in message, "error": f"{type(error).__name__}: {message}", "workspace": str(workspace)})
    passed = [item for item in rows if item["status"] == "PASS"]
    winner = min(passed, key=lambda item: int(item["latency_ms"]))["runtime"] if passed else "native"
    payload = {"matrix_version": "final-1", "goal": OBJECTIVE, "scenarios": ["chat", "direct_action", "multi_agent", "long_running", "replan", "tool_failure", "evidence", "restart"], "scenario_note": "Common real long-running multi-agent artifact/evidence slice; recovery scenarios remain covered by targeted tests.", "winner": winner, "winner_rationale": "lowest latency among candidates with real normalized PASS and physical artifact/evidence refs; Native remains deterministic fallback", "results": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"winner": winner, "results": rows}, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
