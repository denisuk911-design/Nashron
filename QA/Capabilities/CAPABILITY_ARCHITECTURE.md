# Luminifera Capability Architecture

## Boundary

Iris and Employees request a semantic `capability_id`. They do not select a
provider, SDK, model, or runtime. `CapabilityExecutionService` creates a
product-owned request, `CapabilityRouter` chooses a registered implementation,
and the implementation returns a normalized result.

```text
Iris / Employee
    -> CapabilityExecutionService
    -> CapabilityRouter
    -> CapabilityRegistry
    -> Tool implementation
    -> normalized result/events + telemetry
```

The registry is independent of the Web UI and database. Production starts with
an empty registry where no tool service has been enabled; unavailable
capabilities are reported honestly as `NOT_AVAILABLE`.

## Selection policy

The router filters by availability, health, permissions, organization request
scope, privacy/local constraints, cost and latency limits. Remaining tools are
ranked by historical reliability, then cost, latency and stable tool ID. A
failed primary is excluded and a compatible fallback is attempted once per
registered implementation.

## Product invariants

- provider and runtime metadata is diagnostic-only;
- permissions are checked before executor invocation;
- the executor receives the organization and correlation scope;
- missing capability is failure, never fake success;
- normalized events are consumed above the registry boundary.
