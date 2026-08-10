@echo off
setlocal
cd /d "%~dp0\.."

if exist ".venv\Scripts\python.exe" (
  set "APP_PYTHON=.venv\Scripts\python.exe"
  goto install_deps
)

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
set "APP_PYTHON=.venv\Scripts\python.exe"

:install_deps
echo Ustanovka zavisimostey...
"%APP_PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Ne udalos ustanovit zavisimosti.
  pause
  exit /b 1
)

echo Zapusk Roman 2050...
"%APP_PYTHON%" app.py
if errorlevel 1 (
  echo Prilozhenie zavershilos s oshibkoy.
  pause
  exit /b 1
)
