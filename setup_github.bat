@echo off
chcp 65001 > nul
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR"

echo.
echo ============================================
echo  Configuración de Repositorio Git para GitHub
echo ============================================
echo.

:: Verificar si Git está instalado
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Git no está instalado.
    echo.
    echo Por favor, instala Git desde: https://git-scm.com/download/win
    echo Durante la instalación, asegúrate de marcar "Add Git to PATH"
    echo.
    echo Después de instalar Git:
    echo 1. Cierra y vuelve a abrir esta ventana
    echo 2. Ejecuta este script nuevamente
    echo.
    pause
    exit /b 1
)

echo [OK] Git está instalado
git --version
echo.

:: Verificar si ya existe un repositorio Git
if exist .git (
    echo [INFO] Ya existe un repositorio Git en este directorio
    echo.
    choice /C SN /M "¿Deseas reinicializar el repositorio? (S/N)"
    if errorlevel 2 goto :skip_init
    echo.
    echo Eliminando repositorio Git existente...
    rmdir /s /q .git
    echo.
)

:skip_init
echo [PASO 1] Inicializando repositorio Git...
git init
if %errorlevel% neq 0 (
    echo [ERROR] No se pudo inicializar el repositorio Git
    pause
    exit /b 1
)
echo [OK] Repositorio inicializado
echo.

echo [PASO 2] Configurando Git (si no está configurado)...
git config user.name >nul 2>nul
if %errorlevel% neq 0 (
    echo Por favor, ingresa tu nombre para Git:
    set /p GIT_NAME=
    git config --global user.name "%GIT_NAME%"
)

git config user.email >nul 2>nul
if %errorlevel% neq 0 (
    echo Por favor, ingresa tu email para Git:
    set /p GIT_EMAIL=
    git config --global user.email "%GIT_EMAIL%"
)
echo [OK] Git configurado
echo.

echo [PASO 3] Agregando archivos al repositorio...
git add .
if %errorlevel% neq 0 (
    echo [ERROR] No se pudieron agregar los archivos
    pause
    exit /b 1
)
echo [OK] Archivos agregados
echo.

echo [PASO 4] Verificando qué archivos se agregarán...
git status --short
echo.

echo [PASO 5] Creando commit inicial...
git commit -m "Initial commit: Sistema de cotizaciones y facturas con validación de stock"
if %errorlevel% neq 0 (
    echo [ERROR] No se pudo crear el commit
    pause
    exit /b 1
)
echo [OK] Commit creado exitosamente
echo.

echo ============================================
echo  ¡Repositorio local configurado!
echo ============================================
echo.
echo SIGUIENTE PASO:
echo.
echo 1. Ve a https://github.com y crea un nuevo repositorio:
echo    - Haz clic en el botón "+" (arriba a la derecha)
echo    - Selecciona "New repository"
echo    - Nombre: sistema-cotizaciones-facturas (o el que prefieras)
echo    - Descripción: Sistema de gestión de cotizaciones, facturas e inventario
echo    - NO marques "Initialize with README" (ya tienes uno)
echo    - Haz clic en "Create repository"
echo.
echo 2. Después de crear el repositorio, GitHub te mostrará comandos.
echo    Ejecuta estos comandos en esta misma ventana:
echo.
echo    git remote add origin https://github.com/TU_USUARIO/nombre-repositorio.git
echo    git branch -M main
echo    git push -u origin main
echo.
echo    (Reemplaza TU_USUARIO y nombre-repositorio con tus datos)
echo.
echo 3. Si te pide autenticación, usa un Personal Access Token
echo    en lugar de tu contraseña de GitHub.
echo.
echo ============================================
echo.
pause
