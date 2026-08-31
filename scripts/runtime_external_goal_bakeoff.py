"""Run real external adapters on a repeatable Core contract benchmark."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.external_runtime_factory import build_external_runtime_adapters
from core.runtime_contracts import EmployeeRef, ExecutionPolicy, ExecutionRequest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("QA/RUNTIME_EXTERNAL_BAKEOFF.json"))
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    adapters = build_external_runtime_adapters(root)
    matrix: list[dict[str, object]] = []
    for runtime_id, adapter in adapters.items():
        for run in range(1, args.runs + 1):
            workspace = root / "QA" / "runtime_external_bakeoff" / runtime_id / f"run-{run}"
            request = ExecutionRequest(
                organization_id=f"BAKEOFF-{runtime_id.upper()}-{run}",
                objective="Prepare a verified PCB converter technical specification.",
                policy=ExecutionPolicy.LONG_RUNNING_PROJECT,
                employees=(EmployeeRef("employee-engineer", "Engineer", "PCB engineer", competencies=("engineering",)), EmployeeRef("employee-reviewer", "Reviewer", "QA reviewer", competencies=("review",))),
                correlation_id=f"bakeoff-{runtime_id}-{run}",
                metadata={"workspace_root": str(workspace), "runtime_id": runtime_id},
            )
            started = time.perf_counter()
            try:
                result = adapter.execute(request)
                paths = [Path(path) for path in result.artifact_refs + result.evidence_refs]
                physical = all(path.is_file() for path in paths)
                passed = bool(result.ok and result.organization_id == request.organization_id and len(result.artifact_refs) >= 2 and len(result.evidence_refs) >= 3 and physical)
                matrix.append({"runtime": runtime_id, "run": run, "status": "PASS" if passed else "FAIL", "ok": result.ok, "latency_ms": round((time.perf_counter() - started) * 1000), "artifacts": len(result.artifact_refs), "evidence": len(result.evidence_refs), "physical_artifacts": physical, "external_429": False, "summary": result.summary, "workspace": str(workspace)})
            except Exception as error:
                message = str(error)
                matrix.append({"runtime": runtime_id, "run": run, "status": "FAIL", "ok": False, "latency_ms": round((time.perf_counter() - started) * 1000), "artifacts": 0, "evidence": 0, "physical_artifacts": False, "external_429": "429" in message or "RESOURCE_EXHAUSTED" in message, "error": f"{type(error).__name__}: {message}", "workspace": str(workspace)})
    grouped = {runtime: [row for row in matrix if row["runtime"] == runtime] for runtime in adapters}
    candidates = [runtime for runtime, rows in grouped.items() if all(row["status"] == "PASS" for row in rows)]
    winner = min(candidates, key=lambda runtime: sum(int(row["latency_ms"]) for row in grouped[runtime])) if candidates else "native"
    output = {"matrix_version": "2", "runs_per_runtime": args.runs, "winner": winner, "selection": "lowest total latency among candidates with 3/3 real PASS and physical artifact/evidence refs", "results": matrix, "candidates": candidates}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False))
    if not candidates:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
