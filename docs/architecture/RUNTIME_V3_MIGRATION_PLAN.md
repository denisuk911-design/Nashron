# Runtime V3 Migration Plan

Runtime V3 is a staged migration. It is not a big-bang replacement.

## Feature Flag

Current runtime selector values:

- `LEGACY`
- `V2_SHADOW`
- `V2_EXPERIMENTAL`
- `HYBRID_V3_EXPERIMENTAL`

V3 remains available only in developer mode. Legacy remains the default rollback backend.

## Stage 1: Local V3 Slice

Status: started.

Scope:

- New `runtime_v3/` package.
- Local deterministic agent runtime.
- Local tool runtime.
- JSON checkpoints.
- Unit coverage for core invariants.

Exit criteria:

- Supervisor owns goal plan.
- Goal decomposes into WorkItems.
- Work runs through Action -> Tool -> Observation.
- Artifact/evidence only after successful tool effect.
- Fake claim is rejected.
- Review/rework works.
- Resume does not repeat completed work.

## Stage 2: SQLite V3 State

Move checkpoint repository from JSON to SQLite tables while keeping the same Team2050 dataclasses and interfaces.

## Stage 3: GUI Goal Mode

Add an experimental Goal mode to the packaged GUI:

- normal chat remains stable;
- social chat does not create goals;
- goal prompt creates plan and shows user-friendly statuses;
- internal enums and IDs are projected into readable text.

## Stage 4: Provider Adapters

Add provider-neutral adapters:

- Codex CLI adapter;
- Gemini CLI/API adapter;
- optional Claude/OpenHands adapter later.

Employee state must survive provider switch.

## Stage 5: External Framework Adapters

Only after Stage 1-4 pass:

- `MAFWorkflowEngine`
- `LangGraphWorkflowEngine`
- OpenHands-style tool/agent adapter

Frameworks remain behind interfaces.

## Stop Condition For Current Stage

Stop after Hybrid Runtime V3 prototype, documents, tests and QA report are ready for architecture review.

Do not start Learning Engine, Provider Hub, Team2050 Assistant or GUI redesign before review.
