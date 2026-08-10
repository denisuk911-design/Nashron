# Response Latency Policy

The user must see system progress without fake employee chatter.

Current response stages displayed by the worker:
- `читаю контекст`;
- `ожидаю ответ провайдера`;
- provider tool statuses such as file edits or commands;
- `готовлю ответ`;
- completed, failed or cancelled through the existing run result.

The chat has an `Остановить` control that cancels the active provider process.

Implemented configurable budgets:
- `response_soft_warning_seconds`: first visible warning, default `20`;
- `response_extended_warning_seconds`: extended waiting warning, default `90`;
- `response_timeout_seconds`: optional automatic cancellation, default `0` meaning disabled.

The budgets are edited in the regular settings dialog. They are separate from
`codex_timeout_seconds`, which remains the provider process limit.

When an agent run starts, `MainWindow` starts application-owned timers and logs:
- `response_latency_tracking_started`;
- `response_latency_soft_warning`;
- `response_latency_extended_warning`;
- `response_latency_timeout_cancelled` when automatic cancellation is enabled.

The warning text is displayed as transient activity under the active generated
message. It is application state, not employee speech. The owner can keep
waiting, type live guidance, transfer future work through routing controls, or
press `Остановить`.

Known limitation:
- the first version exposes a global budget for all providers and task types;
- task-specific budgets such as "simple answer" versus "long engineering job"
  still require a future task-classifier.
