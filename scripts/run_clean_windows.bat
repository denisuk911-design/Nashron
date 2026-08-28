@echo off
setlocal
cd /d "%~dp0.."

rem Use a separate Team2050 Preview profile and workspace.
set "TEAM2050_PREVIEW=1"
set "TEAM2050_PREVIEW_HOME=%LOCALAPPDATA%\Team2050-Preview"
call scripts\run_windows.bat
