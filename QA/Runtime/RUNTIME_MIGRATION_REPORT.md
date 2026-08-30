# Runtime Migration Report

Status: `BLOCKED - external candidate gate incomplete`  
Date: 2026-08-30  
Latest commit: `27a1079`

## Completed

- Native Runtime preserved as baseline; no database migration performed.
- Product/Core versus Native coupling audit completed.
- Runtime-neutral contracts added: semantic `ExecutionPolicy`,
  `ExecutionRequest`, `EmployeeRef`, normalized events, result and adapter
  protocol.
- Native adapter and Product-facing `RuntimeExecutionService` added.
- Policy selector added with mandatory Native baseline and recorded fallback.
- Isolated environments created and official candidates installed:
  OpenAI Agents `0.22.0`, LangGraph `1.2.11`, Google ADK `2.8.0`, AutoGen
  `0.7.5`.
- Real local LangGraph graph execution passed.
- Real bounded Google ADK model execution passed with classification `WORK`.
- Full regression: `519 passed`, two existing non-fatal warnings.
- Commits were pushed to `origin/main` after each completed milestone.

## Not complete

- OpenAI Agents and AutoGen have package/object smoke only; no model-backed
  run is claimed.
- LangGraph still needs model/tool/artifact/restart bake-off evidence.
- Normalized external adapters are not promoted into production routing.
- No final runtime recommendation can be made from the current evidence.

## Blocker

The required model-backed bake-off for OpenAI Agents and AutoGen cannot be
completed in this environment because their provider credentials are absent.
Google ADK can run with the configured credential and proved its real path, but
that does not substitute for the missing candidates. Production routing stays
on Native until the remaining bounded runs and artifact/evidence checks pass.

## Evidence files

- `QA/Runtime/BASELINE.md`
- `QA/Runtime/DECOUPLING_AUDIT.md`
- `QA/Runtime/RUNTIME_CONTRACT.md`
- `QA/Runtime/RUNTIME_DEPENDENCIES.md`
- `QA/Runtime/BAKEOFF_PLAN.md`
- `QA/Runtime/BAKEOFF_RESULTS.md`
- `QA/Runtime/RUNTIME_RECOMMENDATION.md`
- `scripts/runtime_candidate_smoke.py`
- `scripts/runtime_google_adk_real_smoke.py`
