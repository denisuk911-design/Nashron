@echo off
setlocal
cd /d "%~dp0.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_web.ps1" %*
if errorlevel 1 (
  echo.
  echo Luminifera could not start. See the message above.
  pause
)
