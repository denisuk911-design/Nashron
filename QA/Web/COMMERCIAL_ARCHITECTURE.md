# Luminifera Commercial Architecture Foundation

The local product boundary is split into three layers:

```text
Browser Web UI
    -> FastAPI /api/* + WebSocket /api/events
    -> Application Services / product read models
    -> Python Core, SQLite profile, Runtime V3 and provider adapters
```

The browser owns presentation, local view state and reconnect behavior only. It does not import Python modules, open SQLite, create domain records directly or decide organization workflows. API handlers validate the selected organization, call an existing service, serialize a human-facing view model and publish a typed event.

The current local boundary is intentionally auth-ready rather than commercial-auth complete. A future deployment can place user identity and membership in front of the same organization-scoped service boundary. Server-side organization checks must remain mandatory when that identity layer is added.

Prepared extension points: memberships, roles/permissions, subscription plans, usage metering, audit log and storage quotas. Payments and cloud workers are out of scope for this local build.
