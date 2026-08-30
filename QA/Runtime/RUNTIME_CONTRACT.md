# Runtime Contract

Date: 2026-08-30

The Product/Core boundary uses `core.runtime_contracts` for runtime-neutral
execution. `EmployeeRef` carries stable product identity and permissions; it
is not an SDK agent and is never persisted as an external runtime object.

## Request

`ExecutionRequest` contains `organization_id`, objective, semantic
`ExecutionPolicy`, employee references, correlation ID and product metadata.
Policies are explicit values: conversational, direct action, managed agent,
dynamic multi-agent, deterministic workflow, and long-running project.

## Result and events

`ExecutionResult` returns success, runtime ID, summary, goal/artifact/evidence
references and normalized `RuntimeEvent` records. Product UI must consume these
events instead of Native checkpoint files or SDK-specific events.

## Native baseline

`NativeRuntimeAdapter` wraps the existing `RuntimeV3GoalService`. It translates
Native trace stages to normalized events and preserves the existing Native
Goal/Plan/WorkItem/Review behavior. It does not change the Native scheduler.

## Adapter rule

External runtimes implement the same adapter boundary and must not invoke the
legacy Native scheduler merely to appear compatible. Application Services own
organization scope and persistence of product records.
