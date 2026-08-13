# Runtime V2 Data Model

Status: prototype schema. It does not alter the production SQLite database.

## Aggregate roots

`WorkflowState` is the prototype aggregate. It references portable string IDs,
not provider sessions or absolute filesystem paths.

| Entity | Key fields | Ownership |
|---|---|---|
| Workflow | workflow_id, task_id, organization_id, goal, status, revision | Team2050 |
| WorkflowStep | step_id, employee_id, operation, dependencies, expected_output, status, attempts | Team2050 |
| Handoff | handoff_id, task_id, source_employee, target_employee, input_artifacts, expected_output, status | Team2050 |
| Artifact | artifact_id, task_id, artifact_type, revisions | Team2050 |
| ArtifactRevision | revision, producer, provider, content_hash, evidence, created_at | Team2050 |
| Finding | finding_id, artifact_id, revision, severity, evidence, owner, status | Team2050 |
| ProviderRun | run_id, employee_id, step_id, provider/model, tokens, duration, failure | Telemetry |
| TraceEvent | trace_id, workflow_id, event_type, detail, created_at | Telemetry |

## State machines

Workflow:

```text
DRAFT -> READY -> RUNNING -> COMPLETED
                    |  |       
                    |  +-> WAITING_FOR_OWNER -> RUNNING
                    +----> PAUSED -> RUNNING
                    +----> CANCEL_REQUESTED -> CANCELLING -> CANCELLED
                    +----> FAILED
```

Step:

```text
PENDING -> READY -> RUNNING -> COMPLETED
                      |          |
                      |          +-> INVALIDATED -> PENDING
                      +-> READY (reason-specific retry)
                      +-> WAITING_APPROVAL
                      +-> FAILED / CANCELLED
```

Finding:

```text
OPEN -> ASSIGNED -> RESOLVED -> CLOSED
          ^            |          |
          +-- REOPENED <-+---------+
```

## Persistence rules

- Checkpoint after every externally visible transition.
- Use optimistic `revision` for a future transactional repository.
- Store artifact content outside the aggregate in production; keep hash,
  revision and evidence in the registry.
- Keep provider runs append-only.
- Never infer progress from chat claims. Progress is derived from step states.
- Never accept "file created" without artifact evidence.
- Scope repository queries by organization and conversation/workflow IDs.

The prototype JSON repository uses write, flush, fsync and atomic replace. A
production repository should provide the same contract with transactional
locking and migrations. A future PostgreSQL implementation maps cleanly because
domain services do not issue SQLite SQL.

## Skill package

Portable package layout:

```text
skills/<skill-id>/
  SKILL.md
  metadata.json
  sources/
  examples/
  tests/
  history/
```

Metadata includes skill_id, name, semantic version, domain, description, owner
and compatibility. Knowledge describes what an employee knows; skill describes
what the employee can do; experience records what was actually performed.

Levels are LEARNING, PRACTICED, VALIDATED, PROFICIENT and EXPERT. They are based
on studies, successful and failed tasks, tests, repeated use and independent
validation. An LLM claim cannot promote itself.
