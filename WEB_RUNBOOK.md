# Luminifera Web Runbook

## Prerequisites

- Windows, Python 3.12+
- repository virtual environment at `.venv`

## Install

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run

From `Roman2050`:

```powershell
.venv\Scripts\python.exe -m services.api.run
```

Equivalent helper: `powershell -ExecutionPolicy Bypass -File .\scripts\run_web.ps1`.

Open `http://localhost:8000`. API documentation is available at `http://localhost:8000/api/docs`.

## Checks

```powershell
.venv\Scripts\python.exe -m pytest tests/test_web_api.py
```

Run an isolated service-backed smoke:

```powershell
.venv\Scripts\python.exe scripts\web_smoke.py --profile .tmp_web_smoke --report QA\Web\web_smoke.json
```

The web process uses the normal Team2050 profile. Set `TEAM2050_HOME` to an isolated profile for a clean local demo.

## Troubleshooting

- `API недоступен`: start the command above and reload the browser.
- Empty organization list: create one from the first screen or select an existing profile.
- Provider diagnostics and credentials stay in the deeper desktop/developer surfaces until their API extraction is complete.
