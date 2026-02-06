@echo off
chcp 65001 >nul
title Iniciando Servidor Flask
echo ========================================
echo    Iniciando Servidor Flask
echo ========================================
echo.

REM Cambiar al directorio del script
cd /d "%~dp0"

REM Verificar si Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no está instalado o no está en el PATH
    echo Por favor, instala Python o agrega Python al PATH del sistema
    pause
    exit /b 1
)

echo Ejecutando run.py...
echo.
python run.py

if errorlevel 1 (
    echo.
    echo ERROR: El servidor no pudo iniciarse correctamente
    pause
    exit /b 1
)

pause
