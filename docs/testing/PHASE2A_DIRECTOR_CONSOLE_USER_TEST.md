# Phase 2A Director Console User Test

Use the built executable:

```text
dist/Roman 2050/Roman 2050.exe
```

## Test Steps

1. Start the application.
   Expected: splash appears, then main chat opens.

2. Click `Команда`.
   Expected: separate Director Console window opens.

3. Open `Сотрудники`.
   Expected: Roman and Petr are listed.

4. Select Roman.
   Expected: detail panel shows stable ID `agent-roman`, provider `CODEX_CLI`, persona and effective permissions.

5. Select Petr.
   Expected: detail panel shows stable ID `agent-petr`, provider `GEMINI_CLI`.

6. Click `Добавить сотрудника`.
   Expected: multi-step wizard opens.

7. Enter display name `Деловод`.
   Expected: stable agent ID is generated automatically and starts with `agent-`.

8. Keep lifecycle `DRAFT`.
   Expected: employee will not start work automatically.

9. Select role `DOCUMENT_CONTROL_OFFICER`.
   Expected: inherited permissions preview includes document-control-related permissions.

10. Select provider `Codex CLI` or `Не настроен`.
    Expected: provider status is shown; unavailable provider does not secretly start work.

11. Select persona `document_control`.
    Expected: persona is stored separately from authority and permissions.

12. On permissions page, leave destructive and owner-only permissions disabled.
    Expected: owner-only permissions cannot be selected in standard UI.

13. On review page click `Проверить без сохранения`.
    Expected: preview shows database rows and files; employee does not appear in the list yet.

14. Click `Создать сотрудника`.
    Expected: wizard closes and `Деловод` appears as `DRAFT`.

15. Select `Деловод` and click `Редактировать`.
    Expected: edit dialog opens.

16. Change display name to `Деловод проекта`.
    Expected: after save, display name changes but stable agent ID remains unchanged.

17. Click `Приостановить` for the test employee and enter a reason.
    Expected: status changes to `SUSPENDED`, history remains visible.

18. Click `Вернуть в работу` and enter a reason.
    Expected: reactivation succeeds only if configuration has no blocking errors.

19. Click `Архивировать`.
    Expected: if transition is not allowed from current state, UI shows an understandable rejection. Disable first if needed, then archive in later lifecycle path.

20. Open `Права`.
    Expected: inherited permissions, direct grants, direct denies and effective permissions are visible.

21. Open `Роли`.
    Expected: role definitions are visible; role editing is clearly not enabled in Phase 2A.

22. Open `Журнал действий`.
    Expected: profile creation, edit and lifecycle actions are visible and read-only.

23. Restart the application.
    Expected: created employee and audit records persist.

24. Return to main chat and send a message to Roman/Petr.
    Expected: existing chat still works and no new employee starts autonomous work.

25. Try launching the executable a second time while the first instance is open.
    Expected: message says `Программа уже запущена`.

## Pass Criteria

- Roman/Petr compatibility remains intact.
- New employee management does not start autonomous work.
- Stable IDs are never replaced by display names.
- Audit log records management actions.
- Owner-only permissions are not assignable through standard UI.
