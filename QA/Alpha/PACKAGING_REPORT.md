# Alpha Packaging Report

Entry point: `scripts/run_luminifera_alpha.bat`

The entry point delegates to `scripts/run_web.ps1`, starts `uvicorn` as a hidden child process, polls `/api/health`, and only then starts the static Web host. API and Web ports are configurable. On shutdown the API child is stopped. Startup failure is reported in the console instead of presenting an unusable blank page.
