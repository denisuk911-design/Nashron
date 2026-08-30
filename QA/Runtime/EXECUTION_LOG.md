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

## Phase 13-14 - fallback side-effect guard - 2026-08-30

- Runtime selector now refuses Native replay when a failed external adapter
  reports `side_effects_committed = True`.
- Clean failures may still use Native fallback with the reason recorded.
- Targeted result: `11 passed`.

## Phase 12 - Iris product boundary - 2026-08-30

- Added `core/iris_orchestration_service.py` as the single Iris Product
  supervisor boundary with explicit policy and organization scope.
- Iris delegates through `RuntimeExecutionService`; adapters remain runtime
  mechanics and do not create separate Iris identities.
- Targeted Iris/runtime result: `9 passed`.

## Durable runtime-neutral journal - 2026-08-30

- Added `core/runtime_journal.py` with atomic organization-scoped run records,
  completion recovery and scope mismatch protection.
- `RuntimeExecutionService` can persist selected runtime results without
  changing Product DB or Native checkpoints.
- Targeted journal/adapter/runtime result: `9 passed`.

## Core composition integration - 2026-08-30

- Registered `RuntimeExecutionService`, `RuntimeExecutionJournal` and
  `IrisOrchestrationService` in the FastAPI Core composition root.
- Existing goal route remains unchanged on the validated Native path; the new
  neutral services are available for migration routing without a UI/DB bypass.
- Web/API/Iris/journal targeted result: `23 passed`.

## Regression after Iris boundary - 2026-08-30

- Full suite: `524 passed` in `180.01s`.
- Warnings unchanged and non-fatal: Starlette/httpx deprecation and the
  existing duplicate zip entry warning in the tampered-backup fixture.

## Final regression checkpoint - 2026-08-30

- Full suite after normalized adapters and fallback protection: `522 passed` in
  `179.30s`.
- Warnings unchanged and non-fatal: Starlette/httpx deprecation plus the
  existing duplicate zip entry warning in the tampered-backup fixture.

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

## Tool observation bake-off - 2026-08-30

- OpenAI Agents and AutoGen real SDK runs invoked their write tools and
  verified physical temporary artifacts.
- Google ADK tool run was rejected by provider `429 RESOURCE_EXHAUSTED` quota;
  candidate remains `PARTIAL` until quota is available.

## Bake-off matrix automation - 2026-08-30

- Added `scripts/runtime_bakeoff_matrix.py` to run the four isolated candidate
  probes with bounded subprocess timeouts and write a compact JSON evidence
  matrix. Provider/quota failures are classified explicitly, never as PASS.
- Script syntax check: PASS.

## External direct-action policy regression - 2026-08-30

- Added a regression proving an external runtime can complete a direct action
  without entering the Native Goal/WorkItem scheduler.
- Fixed selector fallback so direct/conversational policy uses an available
  external candidate when the preferred OpenAI adapter is absent.
- Targeted execution/selector/adapter/journal result: `10 passed`.

## Latest bake-off matrix - 2026-08-30

- Ran the four candidate probes through bounded subprocesses and saved
  `QA/Runtime/BAKEOFF_MATRIX.json`.
- OpenAI Agents tool/artifact probe passed; LangGraph, Google ADK and AutoGen
  were rejected by provider quota during this rerun. Prior successful model
  smokes remain recorded as separate evidence.

## Migration report checkpoint - 2026-08-30

- Added `QA/Runtime/RUNTIME_MIGRATION_REPORT.md` with the completed work,
  evidence and explicit blocker. Native remains the only production-promoted
  runtime until the remaining candidate runs are available.

## 2026-08-30 - normalized tool events and external recovery

- Added explicit `tool_calls` to the external payload normalization boundary;
  emitted events now include `tool.called` before observation/artifact events.
- Added external adapter journal recovery and organization-isolation tests.
- Extended LangGraph smoke with a graph-native physical observation artifact.
- Targeted result: `11 passed`.
- Live LangGraph rerun: blocked by provider `429 RESOURCE_EXHAUSTED`; not
  counted as PASS.
- Full regression after this checkpoint: `528 passed` in `172.85s`; two
  existing non-fatal warnings.
- Extended the runtime-neutral contract with capability/health/usage/error/
  trace DTOs and the remaining normalized lifecycle event types.
- Contract/runtime targeted result: `18 passed`.
- Full regression after contract completion: `529 passed` in `189.44s`; two
  existing non-fatal warnings.
- Completed the required recommendation fields with evidence-based routing
  and explicit non-promotion status for external candidates.
- Aligned lifecycle event values with the canonical `execution.*` vocabulary,
  retaining enum aliases for existing Native callers.
- Full regression after event alignment: `529 passed` in `188.11s`.
- Replaced shared mutable employee resolution state with context-local scope;
  added parallel organization/employee isolation regression.
- Full regression after concurrency isolation: `530 passed` in `186.65s`.
- Added and tested the bounded subprocess JSON bridge for isolated external
  runtime execution and payload normalization.
- External bridge targeted result: `14 passed`.
- Full regression after subprocess bridge: `532 passed` in `173.41s`; no new
  warnings.
- Added a subprocess hang regression proving the bridge enforces its hard
  timeout; external runtime hangs are not treated as successful work.
- Revalidated offline isolated candidate smoke: OpenAI Agents `0.22.0`,
  LangGraph `1.2.11`, Google ADK `2.8.0`, AutoGen `0.7.5` all PASS.
- Recorded owner-directed skip of the quota-blocked live candidate stage;
  blocked candidates are excluded from promotion rather than marked PASS.
- Added explicit external-runtime promotion gating; unpromoted adapters are
  available for bake-off only and cannot be selected by Product routing.
- Added optional runtime health gating; unavailable external candidates are
  skipped before execution and fall back to Native.
- Added explicit capability profiles to Native and external adapters without
  coupling Product code to SDK names.
- Capability/adapter targeted result: `22 passed`.
- Full regression after health-aware routing: `538 passed` in `208.72s`.
- Added external payload organization-scope validation and regression coverage.
- Targeted external/runtime isolation result after scope validation: `17 passed`.
- Added server-side permission resolver propagation into external execution
  requests; targeted runtime result: `16 passed`.
- Full regression after permission propagation: `536 passed` in `185.74s`.
- Added and tested runtime-neutral Web `POST /api/executions` through Iris;
  API targeted result: `30 passed`.
- Full regression after Web execution endpoint: `537 passed` in `176.24s`.
- Hardened bake-off matrix subprocess timeout handling and syntax-checked the
  runner without issuing provider calls.
- Full regression after promotion gating: `534 passed` in `173.13s`.
