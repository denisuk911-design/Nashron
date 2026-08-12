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

if not exist "build" mkdir "build"
for /f "delims=" %%i in ('git rev-parse --short HEAD') do set "BUILD_COMMIT=%%i"
for /f "delims=" %%i in ('powershell -NoProfile -Command "(Get-Date).ToUniversalTime().ToString('o')"') do set "BUILD_TIMESTAMP=%%i"
".venv\Scripts\python.exe" scripts\write_build_info.py --output build\build_info.json --version 2.5.0 --commit "%BUILD_COMMIT%" --timestamp "%BUILD_TIMESTAMP%"
if errorlevel 1 exit /b 1

".venv\Scripts\pyinstaller.exe" --noconfirm --clean Team2050.spec

if errorlevel 1 (
  echo Sborka EXE zavershilas s oshibkoy.
  pause
  exit /b 1
)

echo EXE sozdan v papke dist\Team2050
