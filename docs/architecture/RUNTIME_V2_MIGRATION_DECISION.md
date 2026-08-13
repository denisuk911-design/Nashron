# Runtime V2 Migration Decision

Decision date: 2026-08-13.

## Verdict

**ADOPT_CUSTOM_ABSTRACTION**, with a later isolated **LangGraph adapter pilot**.

This means adopting Team2050-owned contracts and data semantics, not building a
general orchestration framework indefinitely. Framework APIs remain hidden
behind `WorkflowEngine`; product entities remain Team2050-owned.

## Evidence

1. The isolated contracts implement the required product semantics that no
   candidate owns: Employee/provider separation, organization scope, artifact
   revision, findings, evidence-based skills and social/work separation.
2. The prototype passes crash recovery, selective interruption, provider switch,
   approval, cancellation, parallel dependency and anti-loop budget tests.
3. LangGraph supplies the strongest match for persistent graph execution with a
   moderate measured dependency footprint (38.3 MiB isolated, 35 resolved
   distributions), but its graph import measured about 3.1 seconds in the
   Python 3.14 Windows probe. Its minimal packaged probe was 29.3 MiB and started
   in 1.61 seconds. It must load only for work mode, never social chat.
4. MAF's concepts are a strong fit and its checkpoint sample passed, but the
   tested 1.13.0 meta-package resolved 200 distributions and occupied about
   801.5 MiB. Its functional workflow sample also reports an experimental API.
5. OpenHands is valuable for runtime/workspace patterns but too broad as the
   product core. Temporal is appropriate for a future cloud control plane, not
   a local-first desktop prerequisite. Langfuse is an optional trace backend.

## Phased migration proposal

No production migration is authorized by this document.

1. Owner approves a LangGraph adapter spike using a separate test profile and
   only the expense-app golden workflow.
2. Compare adapter behavior and packaged size against the pure abstraction.
3. Add a repository implementation with transactional SQLite and schema
   migrations, still isolated from production data.
4. Black-box QA validates crash/restart, cancellation and owner interruption.
5. Move one non-critical work workflow behind `V2_EXPERIMENTAL`; keep social
   chat and all ordinary users on LEGACY.
6. Decide again before any default change or data migration.

## Rejected now

- KEEP_CURRENT: current workflow cannot express the target graph/recovery model.
- ADOPT_MAF: useful but current package budget and experimental surfaces are too
  costly for the desktop default.
- ADOPT_LANGGRAPH directly: would leak framework concepts into product code.
- ADOPT_HYBRID: combining workflow frameworks has no demonstrated benefit and
  would multiply operational complexity.

## Rollback

`runtime_engine` defaults to LEGACY and resolves to LEGACY unless developer mode
is enabled. Removing `runtime_v2/` and its developer setting restores the exact
production path; no production database has been migrated.
