# Phase 1 Engine Restore

Date: 2026-08-31

## Result

The packaged client was stale relative to the current Web/Core sources. A clean
`dist/Luminifera.exe` rebuild restored the packaged Web -> FastAPI -> Core path.
No Product UI or design files were changed for this repair.

## Packaged evidence

- Fresh packaged launch report: `.tmp-engine-report-0831-new.json`
- Restart launch report: `.tmp-engine-report-0831-restart.json`
- First launch API: `http://127.0.0.1:54213/api/health` returned `200` and `ready`.
- Restart API: `http://127.0.0.1:54284/api/health` returned `200` and `ready`.
- Fresh API returned `200` for Home, Employees, Chat, Goals, Work, Files and Settings.
- Real Iris actions through `POST /api/chat`: organization creation, team creation
  (six persisted employees), and Goal creation all completed through Core services.
- After stopping and relaunching the packaged executable with the same user home,
  the organization, six employees, one Goal, and Iris history were present.
- Packaged browser verification: `window.LuminiferaBridge.connected === true`,
  `window.LUMINIFERA_API_BASE` pointed at the live API port, and Home rendered.

## Known limitation

The clean test profile has no configured external provider, so provider-backed
long-running execution was not invoked. This is unrelated to engine reachability;
the API and deterministic Iris application actions are operational.
