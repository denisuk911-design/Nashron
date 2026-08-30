# Multi-Runtime Migration Execution Log

## Phase 0 - baseline - 2026-08-30

- Confirmed Web baseline commit `f875922` and preserved Native Runtime/PySide fallback.
- Confirmed Python `3.14.5`, Web/API live `200`, full suite `511 passed`, targeted Web suite `22 passed`.
- No database migration or destructive change performed.
- Baseline details: `QA/Runtime/BASELINE.md`.

## Phase 1 - decoupling audit - 2026-08-30

- Completed the Product/Core versus Native Runtime audit.
- Added `QA/Runtime/DECOUPLING_AUDIT.md` with concrete coupling points and the
  target adapter boundary.
- Commit: `1934196 Document runtime decoupling audit`.

## Phase 2-4 - contracts and Native adapter - 2026-08-30

- Added runtime-neutral `ExecutionPolicy`, `ExecutionRequest`, `EmployeeRef`,
  `RuntimeEvent`, `ExecutionResult` and `RuntimeAdapter` contracts in
  `core/runtime_contracts.py`.
- Added `core/native_runtime_adapter.py`; it wraps the validated Native
  `RuntimeV3GoalService` and maps Native traces to normalized events without
  changing the scheduler or Product identity.
- Added `QA/Runtime/RUNTIME_CONTRACT.md` and targeted tests in
  `tests/test_runtime_contracts.py`.
- Targeted contract result: `4 passed`.

## Phase 5-6 - isolated candidate installation and smoke - 2026-08-30

- Created isolated, Git-ignored environments under `.runtime_envs` for all
  four required candidates; the application `.venv` was unchanged.
- Installed and imported: OpenAI Agents `0.22.0`, LangGraph `1.2.11`, Google
  ADK `2.8.0`, AutoGen AgentChat/Ext `0.7.5`.
- Ran `scripts/runtime_candidate_smoke.py` in each environment. All four
  package/object or local graph smokes passed.
- These are installation/framework smokes only; no model-backed PASS is
  claimed yet. Full candidate bake-off must use bounded real provider runs and
  record authentication/network availability explicitly.

## Phase 7 - candidate gate and selector - 2026-08-30

- Added `core/runtime_selector.py` with semantic policy selection, mandatory
  Native baseline and exception fallback that executes Native once and records
  the fallback reason.
- Added `QA/Runtime/BAKEOFF_PLAN.md` with promotion gate, scenarios and
  measurements. Import/version output is explicitly insufficient for PASS.
- Targeted selector/runtime result: `66 passed`.

## Candidate bake-off checkpoint - 2026-08-30

- Recorded partial results in `QA/Runtime/BAKEOFF_RESULTS.md`.
- Recorded conservative recommendation in
  `QA/Runtime/RUNTIME_RECOMMENDATION.md`: Native remains baseline; no external
  candidate is promoted from import-only evidence.
- Added `core/runtime_execution_service.py` as the Product-facing facade that
  translates `ChatAgent` records to `EmployeeRef` and delegates by semantic
  policy through `RuntimeSelector`.
- Targeted facade/runtime result: `67 passed`.

## Phase 8-11 - external adapter normalization - 2026-08-30

- Added normalized callback adapters for OpenAI Agents, LangGraph, Google ADK
  and AutoGen in `core/external_runtime_adapters.py`.
- Adapters emit normalized run, observation and artifact events and preserve
  organization/correlation scope; SDK clients remain outside Product code.
- Targeted adapter/contract/selector result: `10 passed`.

## Regression checkpoint - 2026-08-30

- Full suite after migration scaffolding: `519 passed` in `184.45s`.
- Warnings only: Starlette/httpx deprecation and the existing duplicate zip
  entry warning in the tampered-backup fixture.
- No database migration performed; the four pre-existing untracked review
  artifacts remain intentionally unstaged.

## Real candidate smoke - 2026-08-30

- Google ADK real bounded model path passed through `InMemoryRunner` using the
  configured environment credential; result was `WORK` for a work prompt.
- The probe used `gemini-3.6-flash` after the provider rejected the older
  model name. No credential value was printed or persisted.
- OpenAI Agents and AutoGen real bounded SDK model paths passed classification
  `WORK` through the OpenAI-compatible Gemini endpoint.
- LangGraph bounded graph model execution passed with classification `WORK`
  using `ChatGoogleGenerativeAI` inside a compiled graph node.

## Migration report checkpoint - 2026-08-30

- Added `QA/Runtime/RUNTIME_MIGRATION_REPORT.md` with the completed work,
  evidence and explicit blocker. Native remains the only production-promoted
  runtime until the remaining candidate runs are available.
