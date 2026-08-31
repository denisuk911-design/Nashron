"""Prepare a distributable Luminifera sidecar runtime bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--source-env", type=Path, default=Path(".runtime_envs/openai-agents"))
    args = parser.parse_args()
    root = Path.cwd().resolve()
    dist = (root / args.dist).resolve()
    source = (root / args.source_env).resolve()
    executable = source / "Scripts" / "python.exe"
    worker = root / "scripts" / "runtime_external_goal_worker.py"
    if not executable.is_file() or not worker.is_file():
        raise SystemExit("openai-agents environment or worker is missing")
    runtime = dist / "runtime"
    target_env = runtime / ".runtime_envs" / "openai-agents"
    target_env.parent.mkdir(parents=True, exist_ok=True)
    if not target_env.exists():
        shutil.copytree(source, target_env)
    target_worker = runtime / "scripts" / worker.name
    target_worker.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(worker, target_worker)
    bundled_executable = target_env / "Scripts" / "python.exe"
    manifest = {
        "manifest_version": "1",
        "runtime": "openai-agents",
        "runtimes": {"openai-agents": {"version": "0.22.0", "sha256": hashlib.sha256(bundled_executable.read_bytes()).hexdigest()}},
        "license": "OpenAI Agents SDK package licenses are included in the bundled environment metadata.",
    }
    (runtime / "runtime_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"runtime_root": str(runtime), "python": str(bundled_executable), "sha256": manifest["runtimes"]["openai-agents"]["sha256"]}, indent=2))


if __name__ == "__main__":
    main()
