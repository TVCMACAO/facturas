@echo off
REM Abre el puerto 5000 en el Firewall de Windows para permitir acceso desde la red local.
REM Ejecutar como Administrador: clic derecho en el archivo -> "Ejecutar como administrador"
echo Comprobando permisos de administrador...
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo ERROR: Ejecuta este archivo como Administrador.
    echo Clic derecho en abrir_puerto_firewall.bat -^> "Ejecutar como administrador"
    echo.
    pause
    exit /b 1
)

echo Agregando reglas al Firewall para el puerto 5000 (TCP)...
netsh advfirewall firewall add rule name="Flask Cotizador - Puerto 5000 (privada)" dir=in action=allow protocol=TCP localport=5000 profile=private
netsh advfirewall firewall add rule name="Flask Cotizador - Puerto 5000 (publica)" dir=in action=allow protocol=TCP localport=5000 profile=public

if %errorLevel% equ 0 (
    echo.
    echo Listo. El puerto 5000 esta permitido en redes privadas.
    echo Reinicia la app con: python run.py
    echo Desde otro equipo usa: http://IP_DE_ESTE_PC:5000
) else (
    echo No se pudo agregar la regla. Revisa el Firewall manualmente.
)
echo.
pause
