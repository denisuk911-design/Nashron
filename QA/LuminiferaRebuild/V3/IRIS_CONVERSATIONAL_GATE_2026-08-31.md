# Packaged Iris conversational gate

Build under test: `dist/Luminifera.exe`, rebuilt after commit `594a164`.

## Packaged observations

- `Привет` returned a conversational Iris response and did not start work.
- `Как дела?` returned a conversational Iris response; Home remained `Нет активной работы`.
- `Собери мне команду` invoked the real `/api/chat` application boundary and returned a real team activation result.
- The same packaged flow produced `Команда «ENGINEERING_PRODUCT_TEAM team» создана...`.
- No fake team records were injected by the UI; the response came from the existing application service and persisted backend state.
- A pending destructive intent was safely cleared by `Отмени это`; no deletion occurred.
- `да, сделай так` after cancellation returned a no-pending confirmation state and started nothing.

## Targeted checks

- `tests/test_supervisor_chat_application_service.py`: PASS, including UI paraphrases and social guard.
- `tests/test_web_api.py`: PASS.
- Packaged GUI interaction at `http://127.0.0.1:55372/app`: PASS.
- Fresh packaged GUI context/cancel interaction at `http://127.0.0.1:56045/app`: PASS.

## Scope note

This gate fixes only the missing team paraphrase mapping and generic cancel/confirm context handling. No Product UI redesign was performed.
