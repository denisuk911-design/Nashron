from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_v3.local_supervisor import LocalSupervisorRuntime


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", default=str(ROOT / "vendor/local_supervisor/llama.cpp/llama-server.exe"))
    parser.add_argument("--model", default=str(ROOT / "vendor/local_supervisor/models/qwen2.5-0.5b-instruct-q4_k_m.gguf"))
    parser.add_argument("--worker", default="")
    parser.add_argument("--evidence", default=str(ROOT / "QA/Task065/local_inference.json"))
    args = parser.parse_args()
    worker_command = [args.worker] if args.worker else None
    result = LocalSupervisorRuntime(args.runtime, args.model, timeout_seconds=90, worker_command=worker_command).infer(
        "Добрый день, как дела?"
    )
    payload = {
        "inference_ok": result.ok,
        "label": result.label,
        "model": Path(args.model).name,
        "runtime": Path(args.runtime).name,
        "timed_out": result.timed_out,
        "external_provider_calls": result.external_provider_calls,
        "stdout_excerpt": result.stdout[-500:],
        "stderr_excerpt": result.stderr[-500:],
    }
    output = Path(args.evidence)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if result.ok and result.label == "SOCIAL" and result.external_provider_calls == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
