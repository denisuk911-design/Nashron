# Runtime Bake-off Plan

Date: 2026-08-30

## Candidate gate

An SDK candidate is only eligible for promotion after: isolated installation,
real runtime execution, normalized events, tool observation, bounded failure
handling, and a result that can be attached to Product-owned organization and
employee identity. Import success or CLI version output is insufficient.

## Scenarios

1. Single-agent direct action with one deterministic tool observation.
2. Multi-agent handoff with two independent work items and normalized events.
3. Durable resume after a forced worker interruption.
4. Product identity and organization isolation across runtime selection.
5. Provider failure followed by Native fallback without duplicate side effects.

## Measurements

- startup and completion latency;
- tool-call and observation counts;
- artifact/evidence reference completeness;
- failure/restart behavior;
- duplicate side effects;
- credentials/network requirements;
- compatibility with Python/runtime isolation.

## Current status

All four official candidates pass isolated package/object smoke. No candidate
has a model-backed promotion yet. Model-backed runs must be bounded and must
record the actual provider path; missing credentials are a candidate blocker,
not a reason to mark PASS.
