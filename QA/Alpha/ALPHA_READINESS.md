# Luminifera Alpha Readiness

Status: READY_FOR_CLOSED_ALPHA (Web baseline)

The Product Mode shell is available through one launcher: `scripts/run_luminifera_alpha.bat` (or `scripts/run_web.ps1`). It starts the API, waits for `/api/health`, then serves the Web client. Product navigation is limited to Home, Iris, Team, Work, Files and Settings. Runtime/provider internals remain behind the Python services.

Validated in this checkpoint:

- Iris is presented as one product component with portrait, presence, history and composer.
- Organization selection and creation use the API boundary.
- Chat, goals, work progress, artifacts and settings use scoped API read/write models.
- The API health gate prevents a blank Web start when the backend is unavailable.
- Existing native runtime and legacy PySide harness are preserved.

Known limitation: provider-dependent work execution still depends on the configured organization/provider; unavailable capabilities must be surfaced by the API rather than simulated by the Web shell.
