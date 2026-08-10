# TEAM2050 — целевая архитектура провайдеров

Провайдер — инфраструктура, а не employee. Личность, роль, история, skills и qualification сотрудника не должны зависеть от смены CLI.

## Слои

```text
Agent
  ├── Role / Persona / Permissions
  └── Provider Assignment
       ├── ProviderRegistry
       ├── ProviderAdapter
       ├── ProviderAccount
       ├── CLI Installation
       ├── Authentication
       ├── Capabilities
       └── Health
```

## Контракт адаптера

Адаптер должен уметь определить executable, версию, доступность, запуск запроса, потоковые статусы, timeout и cancel. Он не должен передавать Team2050 пароли и не должен читать чужие токены из SQLite/JSON.

Поддерживаемые идентификаторы: `CODEX`, `GEMINI`, `CLAUDE`, `DEEPSEEK`, `OTHER`.

## Готовность

Сотрудник считается `READY` только при одновременном выполнении условий:

- CLI установлен;
- provider авторизован официальным flow;
- доступ к модели подтверждён;
- нужные capabilities известны;
- health check завершён успешно.

В противном случае GUI показывает конкретную причину и запускает приложение в `LIMITED MODE`, не подменяя недоступного сотрудника другим.

## Установка и авторизация

Будущий GUI-flow: `Добавить сотрудника` → provider → проверка CLI → официальный источник/версия → явное подтверждение установки → официальный login/device flow → access/capability/health.

Произвольные URL, встроенные формы паролей, тихая установка и скрытая смена provider запрещены.
