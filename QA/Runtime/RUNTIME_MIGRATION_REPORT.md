# Runtime Migration Report

Status: `BLOCKED - external candidate gate incomplete`  
Date: 2026-08-30  
Latest commit: `38377e6`

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
- Real bounded LangGraph graph model execution passed with classification
  `WORK`.
- Real bounded Google ADK model execution passed with classification `WORK`.
- Real bounded OpenAI Agents SDK execution passed with classification `WORK`
  through its `Runner` path.
- Real bounded AutoGen model-client execution passed with classification
  `WORK` through `OpenAIChatCompletionClient`.
- OpenAI Agents and AutoGen tool smokes also created physical observation
  artifacts; Google ADK tool retry was blocked by provider `429` quota.
- Full regression after fallback protection: `522 passed`, two existing
  non-fatal warnings.
- Full regression after Iris boundary: `524 passed` in `180.01s`, with the
  same two non-fatal warnings.
- Commits were pushed to `origin/main` after each completed milestone.

## Not complete

- OpenAI Agents and AutoGen now have real bounded model-backed classification
  runs through their official SDK paths.
- LangGraph has real model-backed graph execution; normalized
  tool/artifact/restart evidence remains pending for all candidates.
- Normalized external adapters are not promoted into production routing.
- A policy-oriented candidate recommendation is recorded, but no candidate is
  production-promoted before the parity gate.
- Normalized adapters now reject replay fallback when an external failure
  reports a committed side effect.
- Runtime-neutral services and durable journal are registered in the FastAPI
  Core composition root; the existing Native goal route remains unchanged.
- `QA/Runtime/BAKEOFF_MATRIX.json` records the latest bounded matrix run;
  provider quota failures are explicit and do not overwrite prior successful
  SDK evidence.

## Blocker

The complete normalized artifact/restart bake-off is not complete. Google ADK
tool evidence is additionally blocked until provider quota is available.
Production
routing stays on Native until every
promoted candidate passes the complete normalized execution gate.

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
