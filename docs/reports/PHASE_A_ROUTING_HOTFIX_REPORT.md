# Phase A Routing Hotfix Report

Status: `IMPLEMENTED_WITH_LIMITATIONS`

## Root cause

The production GUI path had three independent defects:

1. `Шуша` was not a token for a configured employee named `Шушанна`, so `TeamRouter` did not see the explicit recipient and reused the previous thread owner, often Roman.
2. A delayed `MainWindow._ensure_generation_started()` watchdog created a second routing decision when the original worker had already consumed the queue. That could duplicate work and select a different employee.
3. `pending_agent_keys` shared the mutable list stored in `RoutingDecision.selected`. Popping a worker removed it from the diagnostic decision and from the stored owner list.

There was also a legacy Roman/Petr alternation in autonomous continuation and a static response splitter that classified unknown employee labels as Roman.

## Authoritative production call chain

```text
ChatWidget.send_requested
  -> MainWindow.send_message
  -> MainWindow._route_agents
  -> TeamRouter.decide
  -> MainWindow._prepare_generation_state
  -> MainWindow._start_next_agent_run
  -> TaskOrchestrator.start_run
  -> AgentRouter.route
  -> CodexClient or GeminiClient
  -> GenerateWorker
```

`TeamRouter` is the only responder selector. The worker guard fails closed when a key is not in the current authorized routing decision. The delayed watchdog no longer re-routes an already completed queue.

## Changes

- Explicit current-message names and aliases are resolved before continuation ownership.
- Safe normalized name forms and optional persisted `AgentProfile.aliases` are supported. Long names such as `Шушанна` resolve `Шуша` without unrestricted fuzzy matching.
- `Остальные что?` excludes employees who already answered the current exchange.
- No role match now means no automatic response; Roman is not a universal fallback.
- Autonomous continuation rotates only through the active roster and cannot invent Roman/Petr when the roster is empty.
- Dynamic employee speaker labels are passed to `ResponseSplitter`; they are not classified as Roman.
- Routing diagnostics persist normalized text, explicit tokens, owners before/after, selected responders, reason, router version and fallback state.
- The two chat controls are labelled `Кому: Авто` and `Режим: Авто`.
- General team pings use a short response style.

## Regression coverage

The new production-path fixture verifies:

- `А Шуша?` -> `shushan` only;
- `Шушанна?` -> `shushan` only;
- `А Пётр?` -> `petr` only;
- `А Роман?` -> `roman` only;
- `Остальные что?` after Roman -> Petr and Shushanna;
- continuation ownership after an explicit Shushanna address;
- the actual `MainWindow` worker creation path creates `shushan`, not Roman;
- dynamic `Шушанна:` response labels remain assigned to Shushanna.

Full automated result: `209 passed`.

## Build and manual limitation

Build result: `cmd /c scripts\\build_windows.bat` completed successfully. Artifact: `dist/Roman 2050/Roman 2050.exe`.

Smoke result: the built EXE stayed alive for 8 seconds after launch and was then stopped by the smoke harness. No startup exception was observed.

The provider-backed interactive sequence from the acceptance request was not executed through the visible EXE in this environment. It still requires manual execution on the target machine with the user’s active Codex/Gemini configuration; it must not be represented as an automated test.
