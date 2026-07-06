@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0pack-easypanel.ps1" %*
if errorlevel 1 (
    echo.
    echo ERROR al crear el zip.
    pause
    exit /b 1
)
echo.
pause
