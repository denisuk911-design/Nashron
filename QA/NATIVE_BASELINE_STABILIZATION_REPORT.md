# Native Baseline Stabilization

Date: 2026-08-31

## Root cause

Normal `filesystem.write` actions were incorrectly escalated to HITL when a generated artifact's **content** contained a risk word such as `publish`, `deploy`, or `payment`. The autonomy policy scanned every payload value instead of only action routing and target fields. This blocked the primary deliverable before its tool observation, leaving the goal RUNNING with one artifact and a pending review.

## Fix

`runtime_v3/autonomy_policy.py` now evaluates risk using only `path`, `source`, `destination`, `command`, `adapter_id`, and `tool_name`. Artifact content remains provider output and cannot independently request an external or financial action. External actions and risky targets still require owner approval.

## Evidence

- Five independent clean-profile Native E2E runs: `QA/BAKEOFF_NATIVE_STABILIZATION_20260831212625.json`
- Each run: `3 WorkItems`, `2 artifacts`, `4 evidence`, `receipt_ready=true`, `persistence_after_webcore_restart=true`, process exit `0`.
- Raw per-run checkpoints and traces are retained under the five `QA/BAKEOFF_NATIVE_STABILIZATION_20260831212625_*` profiles.
- Negative-path regression remains covered by HITL, REWORK/BLOCKED, budget, and restart tests.

## Verification

- Targeted Native/runtime tests: `40 passed`
- Full pytest: `561 passed, 2 warnings`
- Warnings are pre-existing dependency/test-fixture warnings (Starlette/httpx deprecation and duplicate backup fixture entry).
