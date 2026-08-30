# Multi-Runtime Decoupling Audit

Date: 2026-08-30  
Baseline commit: `9da7de7`  
Product baseline: Luminifera Web working baseline `f875922`

## Scope

This audit separates the Luminifera product/application layer from the
currently validated Native Runtime. It records coupling that must be removed
or contained before external runtimes are promoted. No database migration or
runtime replacement is performed by this audit.

## Product-owned surfaces

- Organization and employee identity are owned by `core/database.py`,
  `core/agent_directory.py`, and the application services.
- Chat-visible employee records are built by
  `core/agent_directory.py:list_chat_agents`; organization filtering happens
  before an employee enters a chat/runtime request.
- Skills, knowledge, competence, artifacts, evidence, review records, goals,
  work and provider registrations are exposed through Core/Application
  Services and Web API routes. These records must remain stable when the
  execution runtime changes.
- The `ChatAgent` identity (`agent_id`, display name, roles, provider binding,
  avatar and skills) is product data. It must not become an SDK agent object.

## Current runtime boundary

### Direct coupling that must be contained

1. `services/api/app.py:194-198` constructs
   `RuntimeV3GoalService` directly as a Core singleton and injects provider
   adapters into it.
2. `services/api/app.py:599-635` starts a goal by calling
   `core.runtime_v3.run_goal` in a thread and reads its Native checkpoint file
   to publish events. The route therefore knows the Native checkpoint layout
   and legacy goal path.
3. `core/runtime_v3_service.py:32-60` converts `ChatAgent` records into
   Native `EmployeeBinding` snapshots, constructs `HybridWorkflowEngine`,
   `ProviderAgentRuntime`, `HybridSupervisorPolicy`, creates the goal and
   starts the plan. This is an application boundary carrying Native mechanics
   rather than a runtime-neutral execution request.
4. `runtime_v3/engine.py:40-63` owns Native employee snapshots, permissions,
   provider capabilities, `ToolRuntime`, JSON checkpoints and the
   `GoalSupervisor`. This is valid Native behavior but must be behind an
   adapter contract.
5. `runtime_v3/engine.py:73-95` hard-wires the
   `Goal -> Plan -> WorkItem -> start` deterministic workflow. That workflow
   remains an optional `deterministic_workflow` policy, not a requirement for
   conversational, direct-action, or external-runtime execution.
6. `runtime_v3/engine.py:270-398` owns scheduling, concurrent execution,
   retries/replanning, provider decisions and Native state mutation. External
   adapters must not call this scheduler as their orchestration engine.
7. `runtime_v3/engine.py:494-563` performs artifact reading and review/rework
   inside the Native engine. The normalized contract must carry artifact and
   evidence references without making another runtime emulate this code.

### Existing isolation that can be reused

- `core/agent_directory.py` already filters agents by organization and
  permission before chat use (`list_chat_agents`, lines 124-174).
- `core/runtime_v3_service.py:_employee_bindings` creates an immutable
  runtime snapshot from product identity and permissions. This is a useful
  adapter input, but it is not the employee model.
- `runtime_v3/local_supervisor.py` already isolates the bundled local model in
  a worker process (`local_supervisor_worker` command at line 96). Its bounded
  process boundary is suitable for a runtime adapter, not a replacement for
  Product Services.
- `services/api/app.py` publishes typed Web events from Core traces. This
  should be mapped to normalized runtime events at one boundary rather than
  exposed as Native trace internals.

## Required target boundary

```text
Product UI / Iris
  -> Application Services (organization, employee, goal, artifact, review)
  -> ExecutionPolicy + runtime-neutral ExecutionRequest
  -> RuntimeSelector
  -> RuntimeAdapter (Native or external)
  -> normalized events / artifacts / evidence / result
  -> Application Services persist product-owned records
```

The selector receives a semantic policy, not keyword checks or SDK-specific
objects. Every adapter receives employee identity plus a provider binding as
data and returns normalized events/results. The Native adapter is the first
implementation and wraps the existing `RuntimeV3GoalService`; it is not
rewritten during the decoupling phase.

## Gaps and risk classification

| Gap | Classification | Required treatment |
| --- | --- | --- |
| No shared execution request/result contract | Blocking architecture gap | Add runtime-neutral contracts before external adapters |
| Native trace types are published from API polling | Boundary leakage | Map traces to normalized events; keep checkpoint internals private |
| Legacy scheduler is embedded in goal service | Policy/runtime conflation | Wrap as Native deterministic policy/adapter |
| No runtime selector or adapter registry | Missing capability | Add selector with explicit fallback and diagnostics |
| External candidate environments absent | Missing capability | Create isolated envs and record exact versions/import checks |
| Employee identity represented as Native binding in engine | Contained risk | Keep `Employee` product model separate; binding becomes adapter DTO |
| Product-owned artifact/evidence records live in Native state during run | Persistence risk | Define references and ownership rules in normalized result contract |
| Existing Web API has no runtime-neutral execution endpoint | Integration gap | Add service-level boundary first, then API route |

## Non-goals for this phase

- No deletion or replacement of the Native Runtime.
- No direct SDK dependency in Product UI or database schema.
- No cloud/marketplace work.
- No cosmetic PySide/Web redesign.

## Audit conclusion

The current Native Runtime is a valid baseline, but it is not yet an
interchangeable runtime engine. Phase 2 should introduce contracts and
normalized event vocabulary, followed by a Native adapter that proves behavior
parity before installing or evaluating external runtimes.
