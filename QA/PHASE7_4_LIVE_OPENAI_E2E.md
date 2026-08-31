# Phase 7.4 Live OpenAI E2E

## Result

- Live OpenAI run was not started because `OPENAI_API` is not configured in the
  explicitly permitted environment. No credential was read, displayed,
  changed, or sent.
- Packaged no-credential fallback passed: requested `openai-agents` returned a
  real Native fallback with `runtime_id=native` and `fallback_from=openai-agents`.
- During the first packaged attempt a startup regression was found when the
  selected provider was empty; it was fixed by avoiding an empty credential
  lookup.
- `/api/executions` now returns `runtime_id` and sanitized `data` so the
  packaged result can be verified without exposing secrets.

## Evidence

- Runner: `scripts/luminifera_phase74_live_openai_e2e.py`
- Live status: `BLOCKED` (credential unavailable).
- Fallback status: `PASS`.

The live provider gate remains open until an explicitly permitted OpenAI
credential is available.
