# Provider Setup User Test

Phase 2A.1 validates provider visibility and readiness only. Installation and real authentication flows are deferred.

## Steps

1. Start the app.
   Expected: app opens normally; no mandatory provider setup blocks the chat.

2. Open `Команда`.
   Expected: Director Console opens.

3. Open `ИИ и CLI`.
   Expected: Codex CLI, Gemini CLI and Claude CLI rows are visible.

4. Click `Повторить проверку`.
   Expected: provider rows update installation/auth/access/health/capability columns.

5. Inspect Codex row.
   Expected: installation reflects actual Codex CLI detection. Authentication is shown separately.

6. Inspect Gemini row.
   Expected: installation and API-key/auth status are shown separately.

7. Inspect Claude row.
   Expected: Claude is not marked ready unless a tested adapter exists. In Phase 2A.1 it should remain not ready/unknown.

8. Open `Сотрудники`.
   Expected: employee readiness column reflects provider readiness, not just lifecycle.

9. Create a DRAFT employee with provider `Claude CLI / Claude Code`.
   Expected: employee can be saved as DRAFT/SETUP_REQUIRED style configuration, but must not start autonomous work.

10. Restart the app.
    Expected: provider definitions and employee provider assignments persist.

11. Confirm Roman/Petr chat.
    Expected: current Roman/Petr workflow still works.

## Deferred Manual Tests

The following require Phase 2A.2:

- installation preview;
- cancelled installation;
- successful provider login;
- failed login;
- authenticated but access unavailable;
- setup resume;
- uninstall warning.
