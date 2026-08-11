@echo off
setlocal
set "CLEAN_HOME=%LOCALAPPDATA%\Roman2050-Clean"
if not exist "%CLEAN_HOME%" (
  echo Clean profile does not exist.
  exit /b 0
)
choice /M "Delete the clean profile, including chat history and settings"
if errorlevel 2 exit /b 0
powershell -NoProfile -ExecutionPolicy Bypass -Command "Remove-Item -LiteralPath $env:CLEAN_HOME -Recurse -Force"
echo Clean profile removed.
