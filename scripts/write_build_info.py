from __future__ import annotations

import argparse
import json
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--version", required=True)
parser.add_argument("--commit", required=True)
parser.add_argument("--timestamp", required=True)
args = parser.parse_args()

args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(
    json.dumps(
        {"version": args.version, "commit": args.commit, "timestamp": args.timestamp},
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
