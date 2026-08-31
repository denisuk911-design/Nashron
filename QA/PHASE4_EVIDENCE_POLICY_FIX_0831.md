# PHASE 4 Evidence Policy Fix

Date: 2026-08-31

## Change

`RuntimeV3GoalService.project_for_chat` now distinguishes blocked work by its
durable reason. An unsupported claim remains explicitly negative and requires a
tool-backed result or bounded rework. An owner confirmation request is reported
as HITL waiting, and provider failure is reported as provider failure. A valid
goal is no longer mislabeled as an unsupported claim merely because it is
waiting for confirmation.

## Evidence

- Clean API smoke: `QA/PHASE4_EVIDENCE_POLICY_SMOKE.json`.
  Real team, Goal, 3 WorkItems, 2 artifacts, 4 evidence records, receipt, and
  restart persistence; `checks_passed=true` and `goal_start_result.ok=true`.
- Negative unsupported-claim coverage remains in
  `tests/runtime_v3/test_hybrid_runtime.py` and passes with BLOCKED/negative
  evidence semantics.
- Summary classification coverage is in `tests/test_runtime_v3_service.py`.
- Packaged API/Web health: both `200` after `dist/Luminifera.exe` rebuild.
- Packaged captures: `QA/PHASE4_PACKAGED_1920/manifest.json` and
  `QA/PHASE4_PACKAGED_1440/manifest.json`, all routes captured.
- Targeted tests: `54 passed`.
- Full pytest: `559 passed, 2 warnings`.
- `node --check` and `git diff --check`: passed.
