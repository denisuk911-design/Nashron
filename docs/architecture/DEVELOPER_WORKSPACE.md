# TEAM2050 — Developer Workspace

## Назначение

Developer Workspace — будущая отдельная рабочая область для разработки Team2050 и подключённых проектов. Она не заменяет рабочий чат и не превращает каждого сотрудника в разработчика приложения.

## Предлагаемая структура

```text
Team2050
├── Рабочий чат
├── Команда
├── Developer Workspace
│   ├── File Explorer
│   ├── Code Editor
│   ├── Tabs
│   ├── Search
│   ├── Terminal
│   ├── Problems
│   ├── Tests
│   ├── Diff
│   └── AI Developer
└── Settings
```

## Границы безопасности

- workspace выбирается пользователем и проходит `PathGuard`;
- доступ AI Developer выдаётся отдельно от разрешений сотрудников чата;
- чтение, запись, команда и destructive action имеют разные permissions;
- удаление и перемещение требуют подтверждения и создают recoverable operation;
- секреты не попадают в prompt, diff, журнал или ChangeSet;
- по умолчанию `SELF_MODIFICATION_AUTONOMY = OFF`.

## ChangeSet

Каждое изменение имеет:

`change_id`, `agent_id`, `task_id`, `timestamp`, `reason`, `files_created`, `files_modified`, `files_deleted`, `diff`, `tests`, `build_result`, `status`, `rollback`.

Статусы: `PROPOSED`, `OWNER_APPROVAL_REQUIRED`, `APPLIED`, `TESTED`, `BUILD_FAILED`, `READY_FOR_REVIEW`, `ROLLED_BACK`, `REJECTED`.

## Поток работы

```text
Пользователь
  → AI Developer: найти/исправить проблему
  → анализ source tree
  → ChangeSet и diff
  → подтверждение владельца
  → patch
  → tests/build
  → результат и rollback
```

AI Developer обязан сообщать фактический файл, команду, результат и оставшиеся ограничения. Описание предполагаемого изменения не считается выполненной работой.
