# Runtime V2 Test Run

Это запускаемая тестовая версия Runtime V2. Она не трогает рабочие данные клиента и создает проверочный файл в отдельной папке `.tmp_runtime_v2_smoke`.

## Запуск

Двойной клик:

```bat
RUN_RUNTIME_V2_TEST.bat
```

Из PowerShell:

```powershell
.\RUN_RUNTIME_V2_TEST.bat
```

Прямой запуск Python:

```powershell
.\.venv\Scripts\python.exe scripts\runtime_v2_smoke.py
```

## Что проверяется

- Runtime V2 создает задачу.
- Локальный тестовый провайдер реально создает файл.
- Runtime V2 проверяет точное содержимое файла.
- Результат, артефакт, evidence и checkpoint сохраняются в SQLite.
- Повторный запуск не зависит от истории чата.

По умолчанию создается файл:

```text
.tmp_runtime_v2_smoke\.runtime_v2\org-runtime-v2-test\<task-id>\runtime_v2_real.txt
```

Ожидаемое содержимое:

```text
RUNTIME_V2_REAL_OK
```
