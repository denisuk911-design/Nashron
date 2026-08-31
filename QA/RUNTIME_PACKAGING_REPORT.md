# OpenAI Agents Packaging Checkpoint

The sidecar package is prepared by `scripts/package_luminifera_runtime.py`:

- `dist/Luminifera.exe`
- `dist/runtime/.runtime_envs/openai-agents/`
- `dist/runtime/scripts/runtime_external_goal_worker.py`
- `dist/runtime/runtime_manifest.json` with SDK version and SHA-256

The packaged launcher starts successfully and the API remains stable. The
packaged Goal E2E also completes with physical Core artifacts/evidence and
restart persistence. The runtime journal for the latest check is:

`QA/PACKAGED_WINNER_20260831215606/workspace/runtime_execution/ORG-7E2B46BBD344/1.json`

It records `runtime_id=native`, so this is a verified deterministic fallback,
not a winner PASS. The remaining acceptance issue is making the packaged
sidecar use OpenAI Agents with the protected provider credential in a fresh
profile, then repeating the required 3/3 packaged winner E2E.
