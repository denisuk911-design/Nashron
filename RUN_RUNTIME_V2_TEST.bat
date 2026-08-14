@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
echo Runtime V2: тестовый запуск
echo.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "scripts\runtime_v2_smoke.py" %*
) else (
  python "scripts\runtime_v2_smoke.py" %*
)
echo.
echo Готово. Нажмите любую клавишу, чтобы закрыть окно.
pause >nul
endlocal
