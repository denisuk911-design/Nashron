# Runtime Final Bake-off

Date: 2026-08-31

## Scope

Native, OpenAI Agents SDK, LangGraph, AutoGen, and Google ADK were evaluated through the same external runtime contract. UI and Native deterministic semantics were not changed.

## Matrix

| Runtime | Real runs | PASS | Physical artifacts/evidence | Result |
|---|---:|---:|---:|---|
| Native | 5 | 5 | 2 artifacts / 4 evidence / receipt / restart | baseline, fallback |
| OpenAI Agents SDK | 3 | 3 | 2 artifacts / 3 evidence each | winner |
| LangGraph | 3 | 0 | one run wrote files but model result was `[]`; another process failed | rejected |
| AutoGen | 3 | 1 | 2 artifacts / 3 evidence on passing run | rejected for instability |
| Google ADK | 3 | 0 | process failed on all three repeated runs | rejected |

External `429`/`RESOURCE_EXHAUSTED` diagnostics were tracked separately; none were observed in the matrix. Failures are runtime/model/process failures, not hidden as PASS.

## Winner and routing

OpenAI Agents SDK is the only external candidate with 3/3 real passes, so it is the production default for non-deterministic policies. `RuntimeSelector` keeps Native for `DETERMINISTIC_WORKFLOW` and uses Native as the bounded fallback when the promoted winner fails before side effects.

The SDKs execute in separate `.runtime_envs/*` subprocesses through `SubprocessRuntimeBridge`. Core receives one normalized `ExecutionResult`; artifacts, evidence, review record, and receipt are physical files under the run workspace. Organization scope is validated before accepting the result.

## Evidence

- Matrix: `QA/RUNTIME_EXTERNAL_BAKEOFF_MATRIX.json`
- Raw per-run workspaces: `QA/runtime_external_bakeoff/<runtime>/run-*`
- Native baseline: `QA/NATIVE_BASELINE_STABILIZATION_REPORT.md`
