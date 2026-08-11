@echo off
setlocal
cd /d "%~dp0.."

rem Use a separate user directory so the source checkout never receives chat history.
set "ROMAN2050_HOME=%LOCALAPPDATA%\Roman2050-Clean"
call scripts\run_windows.bat
