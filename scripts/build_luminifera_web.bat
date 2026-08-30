@echo off
setlocal
cd /d "%~dp0.."
call .venv\Scripts\pyinstaller.exe --noconfirm --clean LuminiferaWeb.spec
if errorlevel 1 exit /b %errorlevel%
echo Luminifera package: dist\Luminifera.exe
