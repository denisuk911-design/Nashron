@echo off
setlocal
set "CLEAN_HOME=%LOCALAPPDATA%\Team2050-Preview"
if not exist "%CLEAN_HOME%" (
  echo Clean profile does not exist.
  exit /b 0
)
choice /M "Delete the Team2050 Preview profile, including chat history and settings"
if errorlevel 2 exit /b 0
powershell -NoProfile -ExecutionPolicy Bypass -Command "Remove-Item -LiteralPath $env:CLEAN_HOME -Recurse -Force"
echo Clean profile removed.
