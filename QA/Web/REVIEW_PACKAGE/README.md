# Luminifera Web review package

This is an intermediate review entry point for the Web UI. It deliberately uses
the current frontend and the real FastAPI/Core backend; it is not a mocked HTML
prototype.

## Review

From the repository root, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_luminifera_review.ps1
```

Then open:

- Web client: `http://127.0.0.1:3000/`
- API health/docs: `http://127.0.0.1:8000/api/health` and `http://127.0.0.1:8000/api/docs`

The page is the same `apps/web/static/index.html` used by the local product
stack. The reviewer can inspect the landing screen, enter the workspace, open
Iris, switch organizations, view team/work/files and verify the real API state.

Visual evidence is stored in `QA/Web/SCREENSHOTS/`; the latest landing capture
is `phase21_landing_actual.png`.

## Important

Opening `index.html` directly from disk is not a valid product check because the
frontend needs the running API and its real organization-scoped data. Use the
launcher above or the live URL instead.
