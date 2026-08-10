# TEAM2050 — архитектурный план следующих фаз

Этот документ фиксирует границы работ после Phase A. Он не запускает реализацию следующих фаз.

## Phase A — стабилизация рабочего чата

Статус: `READY_FOR_USER_TEST` с ограничениями.

Включает детерминированную маршрутизацию, direct/multi/team обращения, continuation-владельца, контекст задачи, доказательства заявлений, статусы run, timeout/cancel и защиту от дублей/циклов.

## Phase B — UI, UTF-8 и переименование

Цель: единый рабочий интерфейс Team2050.

- завершить аудит UTF-8 для GUI, subprocess, логов, SQLite и PyInstaller;
- перевести все пользовательские строки на RU/UK/EN через единый каталог локализации;
- довести light/dark тему и адаптивное отображение длинных сообщений;
- показать реальный run status, cancel, blocked и provider readiness;
- выполнить user-facing rename `Roman 2050` → `Team2050`, сохранив legacy paths и старые базы.

Граница: Roman остаётся employee key и исторической ролью, технические пути не переименовываются автоматически.

## Phase C — провайдеры

Ввести инфраструктурные интерфейсы `ProviderRegistry`, `ProviderAdapter`, `ProviderInstaller`, `ProviderAuthentication`, `ProviderHealth` и `ProviderCapability`.

Состояние готовности разделяется на installation, authentication, access, capabilities и health. GUI показывает причину, официальное происхождение CLI, версию и безопасный способ отмены.

## Phase D — skills и knowledge

Перенести навыки из декоративного JSON в versioned skill packages и связать employee skill state с реальными evidence: tasks, runs, artifacts, reviews и qualification tasks.

Статус `QUALIFIED` разрешается только после независимой проверки. Знания проходят source/review/status lifecycle и не активируются по одному тексту агента.

## Phase E — Developer Workspace

Добавить отдельную рабочую область файлов: explorer, editor, поиск, terminal, problems, tests, diff и artifact history. Общий чат остаётся отдельным интерфейсом.

Подробная схема: `DEVELOPER_WORKSPACE.md`.

## Phase F — AI Developer

AI Developer является отдельным прямым адресатом, а не обычным сотрудником отдела. Он анализирует source tree, готовит ChangeSet, запускает тесты/build и показывает diff. Самовольное редактирование выключено.

## Phase G — контролируемая модификация

Patch проходит цепочку: предложение → подтверждение владельца → применение → tests → build → результат → rollback. Все операции записываются append-only audit trail.

Нельзя разрешать бесконечное автономное переписывание приложения или изменение базовых правил без подтверждения владельца.
