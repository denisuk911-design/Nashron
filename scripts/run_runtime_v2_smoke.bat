@echo off
setlocal
cd /d "%~dp0.."
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "scripts\runtime_v2_smoke.py" %*
) else (
  python "scripts\runtime_v2_smoke.py" %*
)
endlocal
