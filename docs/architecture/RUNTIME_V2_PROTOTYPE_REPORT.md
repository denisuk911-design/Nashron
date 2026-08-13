# Runtime V2 Prototype Report

Status: PROTOTYPE COMPLETE. Production migration has not started.

## Implemented

- Isolated pure-Python `runtime_v2/`; no imports from the production chat path.
- Product-neutral contracts for WorkflowEngine, AgentRuntime, ProviderAdapter,
  CheckpointStore, TraceService, ArtifactRegistry and FindingRegistry.
- Conservative social/work intent gate.
- Dependency graph, real concurrent ready-step dispatch and typed handoffs.
- Atomic JSON checkpoints, restart recovery and organization isolation guard.
- CANCEL_REQUESTED -> CANCELLING -> CANCELLED lifecycle.
- Reason-specific retry and provider hot swap without changing employee/task.
- Human approval, requirement interruption and selective downstream invalidation.
- Artifact revisions, structured findings and bounded rework loop.
- Workspace path isolation and dangerous-action approval policy.
- Evidence-based skill levels and package validator.
- Neutral local traces containing provider/model/token/duration/call metadata.
- Developer-only `runtime_engine` feature flag; default and normal-user result is
  always `LEGACY`.

## Golden and chaos evidence

The isolated suite covers social messages, direct assignment, director-first
team work, parallel dependency ordering, owner approval, restart, provider
crash, timeout, invalid output, missing artifact, disabled employee,
organization switch, cancellation, provider switch, requirement interruption,
workspace escape, skill validation, artifact revision and finding rework.

The expense workflow runs:

```text
Director plan
  -> Product ---------+
  -> Technical -------+-> Director synthesis -> Reviewer
     -> Documentation -> Owner approval -> Completed
```

Product and Technical share the same execution wave. The owner approval stage
blocks without retry and resumes after an explicit decision. The provider-switch
test records Provider A failure then Provider B success while organization,
employee and task IDs remain unchanged. The interruption test changes the
offline requirement, re-runs Technical and downstream stages, and keeps Product
at one execution.

## Known prototype limits

- JSON checkpoints are single-process research storage, not a production
  multi-process transaction system.
- Thread-based dispatch proves concurrency but does not implement remote worker
  leasing or cooperative cancellation of provider subprocesses.
- Providers are deterministic adapters; live Codex/Gemini integration stays on
  the legacy runtime.
- No V2 GUI is connected. Structured metadata therefore cannot leak into chat.
- Review routing is explicit in workflow definitions; a future Organization
  governance compiler must generate dynamic definitions from presets/RACI.
- Full artifact blobs and skill source material need a content-addressed store.

## Performance and packaging

The local fake-provider reference workflow completed in about 36 ms during the
recorded run, with seven calls, seven artifacts and 25 trace events. This is an
orchestration benchmark only. The framework-neutral probe was packaged as an
8.9 MiB one-file executable and ran successfully from a clean Windows temporary
directory. It was built separately from the production executable. No new
runtime dependency was added to `requirements.txt`, so normal application
startup and package size are unchanged.

## Stop condition

Research, prototype and benchmark are complete. Migration recommendation is
ready. The next production step requires owner approval and a narrow adapter
pilot; Runtime V2 must not replace legacy chat on this branch.
