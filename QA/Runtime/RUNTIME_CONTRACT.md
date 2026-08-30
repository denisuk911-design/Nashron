# Runtime Contract

Date: 2026-08-30

The Product/Core boundary uses `core.runtime_contracts` for runtime-neutral
execution. `EmployeeRef` carries stable product identity and permissions; it
is not an SDK agent and is never persisted as an external runtime object.
Permissions are populated by the server-side Product resolver before routing;
external adapters never receive authority to infer or grant permissions.

## Request

`ExecutionRequest` contains `organization_id`, objective, semantic
`ExecutionPolicy`, employee references, correlation ID and product metadata.
Policies are explicit values: conversational, direct action, managed agent,
dynamic multi-agent, deterministic workflow, and long-running project.

## Result and events

`ExecutionResult` returns success, runtime ID, summary, goal/artifact/evidence
references, normalized `RuntimeEvent` records, usage, structured errors and a
trace reference. `RuntimeCapabilities` and `RuntimeHealth` describe a runtime
without exposing its SDK. Product UI must consume these contracts instead of
Native checkpoint files or SDK-specific events.

The normalized event vocabulary includes execution/run aliases, agent lifecycle, tool calls and
completion/failure, observations, artifact create/update, review request and
completion, replanning and clarification. The external boundary emits an
explicit `tool.called` before observation and artifact events.

## Native baseline

`NativeRuntimeAdapter` wraps the existing `RuntimeV3GoalService`. It translates
Native trace stages to normalized events and preserves the existing Native
Goal/Plan/WorkItem/Review behavior. It does not change the Native scheduler.

## Adapter rule

External runtimes implement the same adapter boundary and must not invoke the
legacy Native scheduler merely to appear compatible. Application Services own
organization scope and persistence of product records.

`core.external_runtime_adapters` provides the normalization boundary for real
SDK bridges. The bridge is injected from the isolated runtime environment;
the adapter emits only normalized events and keeps SDK objects out of Product
code.

`SubprocessRuntimeBridge` is the bounded IPC implementation: it sends only a
JSON execution request to an isolated SDK process, enforces a hard subprocess
timeout (terminating the bounded child process), rejects non-JSON responses,
and maps the response into the neutral payload before any Product-facing event
is emitted. A returned organization scope, when supplied by the bridge, must
match the request scope before any artifact/evidence refs are accepted.

An adapter failure may set `side_effects_committed = True` on its exception.
The selector then re-raises instead of replaying through Native, preventing
duplicate external writes. Failures without committed effects may use the
recorded Native fallback.

`IrisOrchestrationService` is the single Product-facing supervisor boundary.
It receives an explicit semantic policy and organization-scoped employee
records, then delegates to `RuntimeExecutionService`; no external SDK defines
an Iris implementation.

Employee resolution inside the execution service is context-local, so a
concurrent execution cannot replace another execution's product employee map.

`RuntimeExecutionJournal` persists normalized run status atomically by
organization and correlation ID. It supports restart recovery of completed
results without exposing or depending on SDK checkpoints.

`RuntimeSelector` requires explicit promotion for every non-Native adapter;
unpromoted candidates remain available for diagnostics and bake-off only and
cannot enter Product routing by registration alone.
When health is supplied, an unavailable external candidate is skipped before
execution and Native remains the safe baseline.

Web Product API exposes `POST /api/executions` through
`IrisOrchestrationService`; it accepts semantic policy and returns only
Product-owned execution fields, normalized events, artifacts and evidence.
The legacy Goal endpoints remain available as compatibility paths.
