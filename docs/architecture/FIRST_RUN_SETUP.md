# First Run Setup

Target design: on first application launch, ROMAN2025 should run a setup wizard for AI providers.

## Target Pages

```text
Добро пожаловать
Проверка ИИ-провайдеров
Установка CLI
Авторизация
Проверка доступа
Проверка сотрудников
Завершение настройки
```

## Phase 2A.1

Not implemented as a blocking startup wizard.

Reason: provider installation/authentication flows are high risk and require a staged implementation. The application currently starts in limited mode and exposes provider status in Director Console -> `ИИ и CLI`.

## Future Requirements

- run lightweight checks asynchronously;
- never block the whole application because an optional provider is unavailable;
- allow deferred setup;
- recover interrupted provisioning sessions;
- do not restart installation blindly after crash/restart.
