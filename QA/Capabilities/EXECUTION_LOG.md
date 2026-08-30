# Capability Execution Log

## 2026-08-30

- Added runtime/provider-neutral capability contracts and canonical capability IDs.
- Added registry supporting multiple implementations per capability.
- Added capability router with permission, health, privacy, cost, latency and
  reliability selection plus bounded fallback.
- Added normalized `capability.requested`, `tool.selected`, `tool.started`,
  `tool.completed`, `tool.failed` and `capability.fallback` events.
- Added Iris capability request boundary and WebCore wiring.
- Default registry intentionally has no fake implementations; unavailable
  capabilities remain explicit.
- Targeted capability/runtime result: `44 passed`.
- Full regression after capability integration: `544 passed` in `177.61s`;
  two pre-existing non-fatal warnings remain.
