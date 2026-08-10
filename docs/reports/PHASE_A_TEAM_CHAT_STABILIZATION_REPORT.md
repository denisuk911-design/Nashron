# Phase A — стабилизация рабочего чата

Дата проверки: 2026-08-10.

## 1. Baseline

До изменений: `194 passed`.

## 2. Корневые причины

- общий ping проходил через role-relevant subset и fallback на Roman;
- прямое обращение к inactive/no-CHAT сотруднику могло перейти к default responder;
- контекстный handoff мог загрязнять обычный direct run автономной целью;
- structured JSON извлекался регулярным выражением и обрывался на вложенной `}`;
- timeout не имел отдельного состояния run;
- статусы были только текстом GUI без записи lifecycle в `agent_runs`.

## 3. Архитектура до

`MainWindow` вызывал `TeamRouter`, но общий выбор часто ограничивался двумя role-relevant агентами. Provider readiness проверялась после выбора, а пользовательский текст и heuristics влияли на последующие handoff-переходы.

## 4. Архитектура после

`TeamRouter` сначала определяет режим и responders:

```text
user message
  → direct / multi-direct / team-call / general-ping / continuation / info-only
  → active + CHAT + eligible roster
  → только выбранные provider calls
  → run status / result / evidence gate
```

Direct вызывает одного сотрудника. Team-call и general ping выбирают весь активный доступный состав. Неадресованный сотрудник молчит, кроме явного bounded handoff или критического исключения.

## 5. Context

`ContextAssembler` теперь возвращает категории immediate, task, organization и conversation context. `PromptBuilder` дополнительно передаёт task state, transitions, artifacts и findings. Новый employee получает релевантный контекст, а не только последнюю реплику.

## 6. Conversation ownership

Direct/continuation owner сохраняется в `conversation_threads` и переживает перезапуск. Короткое продолжение вроде «А по второму пункту?» возвращается владельцу текущей ветки. Team-call фиксирует ожидаемый набор ответственных.

## 7. Evidence

Claim validator отделяет планы от claims о выполненной работе. Фраза о проверке, чтении или изменении файла без структурированного evidence блокирует skill update и показывает предупреждение. Сам текст сотрудника не считается доказательством.

## 8. Timeout/cancel

Добавлены run statuses `QUEUED`, `PREPARING_CONTEXT`, `STARTING_PROVIDER`, `WAITING_FOR_PROVIDER`, `READING_FILES`, `RUNNING_TOOLS`, `PREPARING_RESPONSE`, `COMPLETED`, `FAILED`, `CANCELLED`, `TIMED_OUT`. Статус хранится в `agent_runs`. Cancelled и timed-out runs никогда не помечаются успешными.

## 9. Дубли и служебный JSON

Structured response извлекается через JSON decoder с учётом вложенных объектов. Повторяющиеся provider blocks и недавние near-duplicate сообщения подавляются до записи/отображения.

## 10. Изменённые файлы

Ключевые изменения: `core/team_routing.py`, `core/agent_directory.py`, `core/context_assembler.py`, `core/prompt_builder.py`, `core/structured_response.py`, `core/claim_evidence.py`, `core/database.py`, `core/run_status.py`, `core/task_orchestrator.py`, `core/models.py`, `core/codex_client.py`, `core/gemini_client.py`, `core/response_cleaner.py`, `gui/main_window.py`, `gui/worker.py`.

## 11. Tests

После изменений: `205 passed in 18.27s`.

Покрыты direct, multi-direct, team-call, general ping, continuation, info-only, blocked/inactive/no-CHAT, provider eligibility, unsupported claim, nested structured JSON, duplicate suppression и timed-out run.

## 12. Build result

Успешно: `cmd /c scripts\\build_windows.bat`. PyInstaller 6.21.0 создал `dist\\Roman 2050\\Roman 2050.exe`.

## 13. Smoke result

Собранный EXE запущен в Windows-процессе и оставался активным 8 секунд без немедленного падения; после проверки процесс остановлен вручную. Реальный provider smoke с Codex/Gemini credentials не выполнялся. Ручной smoke-план остаётся обязательным.

## 14. Known limitations

- UI всё ещё содержит часть orchestration policy в `MainWindow`;
- provider provisioning и полноценный readiness wizard относятся к Phase C;
- skills/knowledge qualification ещё не перенесены в полный evidence lifecycle Phase D;
- параллельное выполнение provider calls не реализовано;
- semantic retrieval контекста пока заменён детерминированным ranking;
- полное переименование в Team2050 не выполнялось.

## 15. Phase B proposal

Следующий этап: UTF-8 audit, единый RU/UK/EN catalog, user-facing Team2050 rename с compatibility layer, контрастные light/dark темы и перенос run status/cancel в компактную UI-панель.

## NORTH STAR IMPACT

Командная работа: responders выбираются приложением до provider call, роли не подменяют друг друга, общие обращения доходят до всей активной команды.

Skills/knowledge quality: unsupported claims больше не считаются evidence и не обновляют skill progress; task context включает artifacts/findings.

Управление без кода: routing, статус и блокировка не требуют правки prompts или JSON.

Доверие: добавлены реальные lifecycle statuses, timeout/cancel semantics, structured JSON parsing и evidence gate.

Удобство: direct запросы короче, общий ping предсказуем, повторы и служебный JSON не засоряют чат.

Final status: `READY_FOR_USER_TEST`.
