# Hybrid Runtime V3 QA

TASK: TEAM2050-HYBRID-RUNTIME-REBUILD-001

This folder stores verification evidence for the first Runtime V3 architecture slice.

## Current Evidence

- `runtime_v3/` package created.
- `docs/architecture/HYBRID_RUNTIME_V3.md` created.
- `docs/architecture/OPEN_SOURCE_ARCHITECTURE_ADOPTION.md` created.
- `docs/architecture/RUNTIME_V3_MIGRATION_PLAN.md` created.
- Unit tests added in `tests/runtime_v3/test_hybrid_runtime.py`.
- GUI Goal mode boundary added in `core/runtime_v3_service.py`.
- Packaged GUI hook added behind developer-only `HYBRID_V3_EXPERIMENTAL`.
- Golden script added in `scripts/runtime_v3_golden.py`.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -m pytest tests\runtime_v3 tests\runtime_v2\test_intent_and_feature_flag.py -q
.\.venv\Scripts\python.exe -m compileall -q runtime_v3
.\.venv\Scripts\python.exe -m pytest tests\runtime_v2 tests\runtime_v3 tests\test_database.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_main_window_helpers.py tests\runtime_v3 tests\test_runtime_v3_service.py -q
.\.venv\Scripts\python.exe scripts\runtime_v3_golden.py
```

## Latest Local Results

- `pytest tests\runtime_v3 tests\runtime_v2\test_intent_and_feature_flag.py -q`: 9 passed.
- `pytest tests\runtime_v2 tests\runtime_v3 tests\test_database.py -q`: 50 passed.
- `pytest -q`: 346 passed.
- `compileall runtime_v3 runtime_v2`: passed.
- `PRAGMA foreign_key_check` on a freshly initialized database: `[]`.
- `pytest tests\test_main_window_helpers.py tests\runtime_v3 tests\test_runtime_v3_service.py -q`: 27 passed.
- `scripts\runtime_v3_golden.py`: passed. Produced 1 goal, 3 work items, 4 actions, 4 observations, 3 artifacts, 4 evidence records, 1 finding, 2 handoffs.

## Current Limitations

- Packaged GUI Golden Scenario has a local deterministic script and GUI hook, but has not yet been verified by launching the packaged executable end-to-end.
- External framework adapters are not implemented yet.
- V3 persistence is JSON checkpoint based; SQLite V3 is planned next.
