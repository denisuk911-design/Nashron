# Universal Core And Employee Lifecycle Cleanup

Дата проверки: 2026-08-12

## Результат

Клиент переведён на универсальную модель Team2050. На чистом профиле приложение создаёт только системные таблицы и базовые role templates: организации, сотрудники и пользовательские профессии не создаются автоматически.

## Что исправлено

- `ManagementService.ensure_foundations(seed_legacy=False)` используется production runtime. Старые Roman/Petr profiles оставлены только как migration/test compatibility и не создаются при обычном запуске.
- Роутер и provider provisioning работают по текущим `agent_profiles` и roster организации. Глобальный fallback сотрудников из другой организации удалён.
- Prompt/context слой больше не подставляет имена, роли или провайдеры legacy-сотрудников. Поведение определяется профилем, ролью, правами, навыками и назначенным provider.
- Добавлен явный cleanup flow для найденных legacy demo profiles: архивирование через каталог и окончательное удаление через раздел сотрудников.
- Hard delete сотрудника больше не блокируется историей. Профиль, назначения, права, provider assignment, персональные skill assignments и runtime state удаляются; общая история и подтверждаемые артефакты сохраняются. Сообщения получают автора `Удалённый сотрудник · <имя>`.
- Permanent delete организации удаляет её membership/workspace cascade, но не удаляет профили сотрудников.
- Любой результат provider нормализуется в `CodexResult`; `None` и неизвестный формат становятся контролируемой ошибкой.
- Ошибки provider/runtime больше не записываются от имени сотрудника и не попадают в employee bubble. Они идут в system message и event log.
- Нейтральные стартовые identity, timeline, prompt и skill storage больше не содержат готовую команду.

## Проверки

- `python -m compileall -q core gui app.py` — OK.
- `27` существующих тестов архитектуры, lifecycle и director console — passed.
- Добавлены регрессионные тесты clean install, hard delete с историей и `None` provider result.

## Ограничения и совместимость

Пользовательские старые базы не переписываются автоматически: существующие профили считаются обычными пользовательскими данными. Для них доступна явная очистка legacy demo profiles. Доменные PCB/KiCad пакеты и существующие рабочие данные не удаляются.
