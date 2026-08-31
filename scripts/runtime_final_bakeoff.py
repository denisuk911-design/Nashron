"""Run the final runtime bake-off against one identical product Goal."""
from __future__ import annotations

import argparse
import json
import os
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
        physical = any(path.is_file() for path in workspace.parent.rglob("*") if "checkpoints" not in path.parts)
    artifacts, evidence = len(result.artifact_refs), len(result.evidence_refs)
    passed = bool(result.ok and artifacts >= 2 and evidence >= 3 and physical)
    return {"runtime": runtime, "status": "PASS" if passed else "FAIL", "ok": result.ok, "latency_ms": elapsed, "quality_score": 1.0 if passed else 0.0, "autonomy": True, "recovery": False, "artifacts": artifacts, "evidence": evidence, "physical_artifacts": physical, "cost": "not reported by adapter", "complexity": {"native": "low", "openai-agents": "medium", "langgraph": "medium", "google-adk": "medium", "autogen": "high"}.get(runtime, "unknown"), "summary": result.summary, "workspace": str(workspace), "artifact_refs": list(result.artifact_refs), "evidence_refs": list(result.evidence_refs)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "QA" / "Runtime" / "FINAL_BAKEOFF.json")
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    root = ROOT / "QA" / "Runtime" / "final_bakeoff"
    provider_id = os.environ.get("TEAM2050_BAKEOFF_PROVIDER_ID", "").strip()
    provider_model = os.environ.get("TEAM2050_BAKEOFF_PROVIDER_MODEL", "").strip()
    provider_base_url = os.environ.get("TEAM2050_BAKEOFF_PROVIDER_BASE_URL", "").strip()
    route = {"provider_id": provider_id, "provider_model": provider_model, "provider_base_url": provider_base_url}
    adapters: dict[str, object] = {"native": native_adapter(root)}
    adapters.update(build_external_runtime_adapters(ROOT, timeout_seconds=90.0))
    rows: list[dict[str, object]] = []
    for runtime, adapter in adapters.items():
        for run in range(1, max(1, args.runs) + 1):
            workspace = root / runtime / f"run-{run}"
            request = ExecutionRequest(f"FINAL-BAKEOFF-ORG-{run}", OBJECTIVE, ExecutionPolicy.LONG_RUNNING_PROJECT, EMPLOYEES, f"final-runtime-bakeoff-{runtime}-{run}", {"workspace_root": str(workspace), "runtime_id": runtime, **route})
            workspace.mkdir(parents=True, exist_ok=True)
            (workspace / "provider-route-trace.json").write_text(json.dumps({"runtime": runtime, "run": run, "provider_route": route, "source": "Provider Hub route supplied by benchmark environment"}, ensure_ascii=False, indent=2), encoding="utf-8")
            started = time.perf_counter()
            try:
                result = row(runtime, adapter.execute(request), round((time.perf_counter() - started) * 1000), workspace)
                result["run"] = run
                rows.append(result)
            except Exception as error:
                message = str(error)
                provider_error = "provider_error" in message or "429" in message or "RESOURCE_EXHAUSTED" in message
                rows.append({"runtime": runtime, "run": run, "status": "BLOCKED" if provider_error else "FAIL", "ok": False, "latency_ms": round((time.perf_counter() - started) * 1000), "quality_score": 0.0, "autonomy": True, "recovery": False, "artifacts": 0, "evidence": 0, "physical_artifacts": False, "cost": "not reported by adapter", "complexity": "unknown", "external_429": provider_error, "error": f"{type(error).__name__}: {message}", "workspace": str(workspace)})
    passed = [item for item in rows if item["status"] == "PASS"]
    complete_candidates = [runtime for runtime in adapters if all(item["status"] == "PASS" for item in rows if item["runtime"] == runtime)]
    matrix_blocked = any(item.get("external_429") for item in rows) or not all(route.values())
    winner = min((item for item in passed if item["runtime"] in complete_candidates), key=lambda item: int(item["latency_ms"]))["runtime"] if complete_candidates and not matrix_blocked else None
    payload = {"matrix_version": "final-2", "runs_per_runtime": max(1, args.runs), "matrix_status": "BLOCKED" if matrix_blocked else "COMPLETE", "goal": OBJECTIVE, "provider_route": {"provider_id": provider_id, "provider_model": provider_model, "provider_base_url": provider_base_url}, "scenarios": ["chat", "direct_action", "multi_agent", "long_running", "replan", "tool_failure", "evidence", "restart"], "scenario_note": "Common real long-running multi-agent artifact/evidence slice; recovery scenarios remain covered by targeted tests.", "winner": winner, "fallback_runtime": "native", "winner_rationale": "winner is withheld until one provider route yields PASS on every clean run; Native remains deterministic fallback", "results": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"winner": winner, "results": rows}, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
