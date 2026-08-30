# Runtime Migration Report

Status: `BLOCKED - external candidate gate incomplete`  
Date: 2026-08-30  
Latest commit: `4fc9f88`

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
- External direct-action regression passes without entering the Native
  Goal/WorkItem scheduler; selector chooses an available external candidate.
- External adapter payloads now normalize explicit `tool.called` events, and
  the LangGraph smoke includes a graph-native physical observation artifact.
- External execution journal integration proves restart recovery and
  organization-scope isolation for an adapter result.
- Runtime-neutral contracts now include capabilities, health, usage,
  structured errors, trace references and the complete required event names.
- Full regression after the evidence-boundary update: `528 passed` in
  `172.85s`; the two existing non-fatal warnings remain unchanged.
- Full regression after contract completion: `529 passed` in `189.44s`; the
  same two existing non-fatal warnings remain unchanged.
- Normalized lifecycle names now expose canonical `execution.*` values while
  retaining source-compatible `run.*` enum names.
- Full regression after event contract alignment: `529 passed` in `188.11s`;
  the same two existing non-fatal warnings remain unchanged.
- RuntimeExecutionService employee resolution is now context-local, preventing
  concurrent executions from cross-contaminating product employee identity.
- Full regression after concurrency isolation: `530 passed` in `186.65s`;
  the same two existing non-fatal warnings remain unchanged.
- Added bounded JSON IPC via `SubprocessRuntimeBridge` so external SDK
  adapters can run outside Product/Core with timeout and malformed-payload
  rejection.
- Full regression after subprocess bridge: `532 passed` in `173.41s`; no new
  warnings.
- Offline isolated package/object smoke revalidated for all four candidates;
  all installed environments remain usable.
- Owner-directed continuation skips the quota-blocked live candidate stage;
  LangGraph and Google ADK are explicitly excluded from promotion, while
  OpenAI Agents and AutoGen remain KEEP_FOR_FUTURE until same-environment
  subprocess adapter evidence is collected.
- RuntimeSelector now requires explicit promotion for external adapters;
  registering an unvalidated candidate can no longer route Product work to it.
- RuntimeSelector now also honors supplied external runtime health and skips an
  unavailable promoted candidate before execution.
- Native and external adapters now expose explicit `RuntimeCapabilities` for
  diagnostics and future capability-aware routing.
- Full regression after health-aware routing: `538 passed` in `208.72s`; the
  same two existing non-fatal warnings remain unchanged.
- External adapter results now reject a returned organization scope that does
  not match the Product request before accepting artifacts or evidence.
- RuntimeExecutionService now carries server-resolved permissions into each
  neutral EmployeeRef; external adapters cannot bypass Product authorization.
- Full regression after permission propagation: `536 passed` in `185.74s`;
  the same two existing non-fatal warnings remain unchanged.
- Added runtime-neutral `POST /api/executions` through Iris/Application
  Services; Product responses hide runtime-specific identifiers and expose
  normalized execution data.
- Full regression after Web execution endpoint: `537 passed` in `176.24s`;
  the same two existing non-fatal warnings remain unchanged.
- Hardened bake-off matrix timeout handling; a hung candidate is recorded as
  `TIMEOUT` without aborting results for other candidates.
- Full regression after promotion gating: `534 passed` in `173.13s`; the same
  two existing non-fatal warnings remain unchanged.

## Blocker

The complete normalized artifact/restart bake-off is not complete. Google ADK
tool evidence is additionally blocked until provider quota is available.
Production
routing stays on Native until every
promoted candidate passes the complete normalized execution gate.

The latest LangGraph tool/artifact smoke also reached the model node but was
blocked by the same provider quota. This is an external credential/quota
limitation, not a local adapter or test failure.

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
