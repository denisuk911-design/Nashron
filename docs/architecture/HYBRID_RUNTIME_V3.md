# Team2050 Hybrid Runtime V3

Runtime V3 starts the migration from chat-driven agent behavior to execution-oriented goal handling.

## Ownership

Team2050 remains authoritative for:

- Employee
- Organization
- Profession
- Role
- Personality
- Skill
- Knowledge
- Experience
- Goal
- WorkItem
- Artifact
- Evidence
- Finding
- Decision
- ProviderBinding

External frameworks are execution infrastructure behind adapters. Product code must depend on Team2050 interfaces, not on framework-specific APIs.

## Layering

```text
Team2050 Product Layer
  -> Organization Runtime
  -> Goal Supervisor
  -> Workflow Engine
  -> Agent Runtime
  -> Tool Runtime
  -> Provider Adapter
```

The first implementation lives in `runtime_v3/` and is intentionally local and deterministic. It proves the product invariants before any Microsoft Agent Framework, LangGraph, or OpenHands adapter is added.

## Goal Model

The old model was:

```text
Goal -> prompt all agents -> discussion -> promise -> maybe blocked
```

Runtime V3 uses:

```text
User Goal
  -> Supervisor
  -> Plan
  -> WorkItems
  -> Executors
  -> Actions
  -> Tools
  -> Observations
  -> Artifacts
  -> Review
  -> Rework
  -> Complete
```

The Supervisor owns planning and assignment. Employees do not negotiate who does what.

## WorkItem

The generic WorkItem is domain-neutral:

- `work_item_id`
- `goal_id`
- `objective`
- `assigned_employee_id`
- `dependencies`
- `input_artifact_ids`
- `required_capabilities`
- `required_tools`
- `expected_artifact_types`
- `acceptance_criteria`
- `evidence_requirements`
- `status`
- `attempt`
- `checkpoint`
- `result`

## P0: Text Is Not Work

Runtime V3 treats text claims as insufficient:

- A file claim without `filesystem.write` observation is not complete.
- A directory claim without filesystem observation is not complete.
- A research claim without source/evidence records is not complete.
- A fix claim without a new artifact revision is not complete.
- A done claim without acceptance verification is not complete.

`runtime_v3` records unsupported claims as failed evidence and keeps the WorkItem open or blocked.

## Action -> Tool -> Observation

The first Tool Runtime supports:

- `filesystem.write`
- `filesystem.read`
- `filesystem.list`
- `terminal.execute` boundary for future use

Every tool returns a typed `Observation`. Artifacts are created only from successful observations.

## Artifact-First Handoff

Handoff is structured:

- `from_employee_id`
- `to_employee_id`
- `work_item_id`
- `artifact_ids`
- `context_refs`
- `expected_result`
- `acceptance`
- `evidence_requirements`

The reviewer receives artifact IDs, not "look above in chat".

## Durable State

The current V3 prototype uses `JsonCheckpointRepository`:

- checkpoint after goal creation
- checkpoint after plan creation
- checkpoint after item start
- checkpoint after item completion
- checkpoint after unsupported claim
- checkpoint after goal status update

The persistence shape is Team2050-owned and can later be backed by SQLite or a framework adapter.

## Current Scope

Implemented:

- Supervisor-owned plan creation.
- Competency-based WorkItem assignment.
- Action -> Tool -> Observation execution.
- Artifact and Evidence creation after successful effects.
- Fake claim rejection.
- Structured handoff.
- Review and bounded rework.
- Checkpoint/resume.
- Social chat guard.
- Provider-neutral employee binding.

Not yet implemented:

- Packaged GUI Goal mode.
- Real provider adapters.
- Real web/source research tool.
- SQLite-backed V3 state.
- External framework adapters.
