@echo off
setlocal
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
  set "PYTHON_EXE="
  where py >nul 2>nul && set "PYTHON_EXE=py -3"
  if not defined PYTHON_EXE (
    where python >nul 2>nul && set "PYTHON_EXE=python"
  )
  if not defined PYTHON_EXE (
    echo Python 3.12+ ne nayden. Ustanovite Python i vklyuchite punkt Add python.exe to PATH.
    pause
    exit /b 1
  )
  echo Sozdanie virtualnogo okruzheniya...
  %PYTHON_EXE% -m venv .venv
  if errorlevel 1 (
    echo Ne udalos sozdat .venv.
    pause
    exit /b 1
  )
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

set "CODEX_BINARY_ARG="
if exist "vendor\codex\win-x64\codex.exe" (
  set "CODEX_BINARY_ARG=--add-binary vendor\codex\win-x64\codex.exe;vendor\codex\win-x64"
)

".venv\Scripts\pyinstaller.exe" ^
  --noconfirm ^
  --windowed ^
  --name "Roman 2050" ^
  --add-data "prompts\roman_system.md;prompts" ^
  --add-data "data\roman_identity.json;data" ^
  --add-data "data\roman_timeline.json;data" ^
  --add-data "data\agent_skills.json;data" ^
  --add-data "data\app_settings.json;data" ^
  --add-data "data\avatars;data\avatars" ^
  %CODEX_BINARY_ARG% ^
  app.py

if errorlevel 1 (
  echo Sborka EXE zavershilas s oshibkoy.
  pause
  exit /b 1
)

echo EXE sozdan v papke dist\Roman 2050
