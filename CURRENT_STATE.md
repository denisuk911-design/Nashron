# Team2050 Runtime V3 Baseline

Commit baseline: stabilization after `TEAM2050-V3-STABILIZATION-019`.

## Verified

- Full regression: 371 passed.
- Python compilation: `compileall` passed for app, core, runtime_v3, gui and scripts.
- Packaged `dist/Team2050/Team2050.exe` completed the autonomous Golden Goal.
- Packaged E2E covered autonomous planning, tool observations, artifacts/evidence, review/rework, provider failover, HITL restart/resume and foreign-key integrity.
- Internal Admin Assistant diagnostic harness passed.
- SQLite `PRAGMA foreign_key_check` returned no rows for smoke profiles.

## Runtime V3

`RuntimeState` is the durable source of execution state: goals, plans, work items,
artifacts, evidence, provider runs, handoffs, interrupts, replans and supervisor
decision records. Checkpoints restore the same workflow graph after restart.

The Supervisor policy routes obvious transitions deterministically, uses a local
adapter for medium-complexity decisions, and escalates complex or risky planning
to a provider-neutral strong planner with safe fallbacks.
