"""Run the isolated Runtime V2 benchmark without production user data."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from runtime_v2.benchmark import metrics_dict, run_v2_benchmark


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="team2050-runtime-v2-") as directory:
        metrics, state = run_v2_benchmark(Path(directory))
        print(json.dumps(metrics_dict(metrics), ensure_ascii=False, indent=2, default=str))
        return 0 if str(state["status"]) == "COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
