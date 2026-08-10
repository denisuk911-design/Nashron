# Agent Work Context and Handoff

Status: `REWORK_REQUIRED`

## Root Cause

The router selected employees, but each user message was treated as a new isolated task. A useful response that existed only in chat was not registered as an artifact. The next employee therefore had no authoritative object and could choose an unrelated template, such as `memo_001.md`.

## Implemented Architecture

The application now persists the coordination state in SQLite:

- `ActiveWorkContext` stores task, owner, previous owner, active and primary artifacts, operation, expected output, handoff state and last action.
- `IntentResolver` classifies controlled operations such as `CREATE`, `FORMAT`, `REVIEW`, `MODIFY`, `INSPECT` and `CONTINUE` before provider invocation.
- `ArtifactReferentResolver` resolves explicit artifacts first, then active context. An explicit BOM request cannot fall back to an unrelated memo.
- `HandoffService` stores structured transfers between employees.
- `AgentExecutionContract` is created after the run is allocated and before the provider starts. It contains the selected agent, intent, input artifacts, operation, expected output, evidence and forbidden substitutions.
- `OutputValidator` rejects a memo when the contract expects `BOM_DOCUMENT`.
- Plain chat results can be registered as `CHAT_ARTIFACT` records. A BOM response is registered as type `BOM` and remains addressable by the next employee.

The prompt receives the persistent context and execution contract as authoritative application state. They are not stored only in the prompt: the SQLite records survive restart.

## Exact Regression Scenario

The service-level regression is implemented and passes:

1. `Давай BOM` creates the task context.
2. Roman's BOM containing `AP63205WU-7` is registered as a BOM artifact.
3. `Шушанна, оформляй` resolves that artifact, selects only Shushanna, creates a handoff and creates a contract with expected output `BOM_DOCUMENT`.
4. A stale memo cannot satisfy an explicit BOM reference.
5. A provider result describing only `memo_001.md` is rejected as `OUTPUT_TYPE_MISMATCH`.

The exact visible provider sequence in the built EXE has not yet been executed in this environment. Therefore this report intentionally remains `REWORK_REQUIRED` until that manual check is completed.

## Tests and Build

- `212 passed` with `pytest -q` after the final test correction.
- `compileall` passes for `core` and `gui`.
- `scripts\build_windows.bat` completed successfully.
- `dist\Roman 2050\Roman 2050.exe` stayed alive during an 8-second smoke launch.
- Exact visible provider scenario: pending manual verification with authenticated Codex/Gemini CLIs.
