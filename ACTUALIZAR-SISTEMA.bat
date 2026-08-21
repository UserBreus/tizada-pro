@echo off
REM ============================================================================
REM  TIZADA PRO - ACTUALIZAR EL SISTEMA (correr EN el servidor)
REM
REM  Doble clic y listo: baja la ultima version publicada del sistema y
REM  recompila la pantalla. No toca los datos del cliente (datos/, entrada/,
REM  trabajos/, config_externo.json): esos no viajan por git.
REM
REM  Requiere que el sistema haya sido instalado por git (por ejemplo con
REM  INSTALAR-EN-OTRA-PC.bat). Si esta copia vino de un RAR/ZIP, este bat
REM  lo avisa y explica el cambio, que se hace UNA sola vez.
REM ============================================================================
title TIZADA PRO - Actualizar sistema
color 0B
cd /d "%~dp0"

echo.
echo   ===========================================================
echo     TIZADA PRO - Actualizar a la ultima version
echo   ===========================================================
echo.

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo   Esta copia NO esta conectada a git ^(vino de un RAR/ZIP^), asi que
    echo   no puede actualizarse sola. Para que las proximas actualizaciones
    echo   sean doble clic, UNA sola vez:
    echo.
    echo     1. En una carpeta NUEVA, correr INSTALAR-EN-OTRA-PC.bat
    echo        ^(instala lo necesario y baja el sistema por git; pide la
    echo        cuenta de GitHub con acceso al repositorio^).
    echo     2. Copiar de la carpeta vieja a la nueva: datos\, entrada\,
    echo        trabajos\ y config_externo.json.
    echo     3. Arrancar el servidor desde la carpeta nueva ^(iniciar.bat^).
    echo.
    echo   Desde ahi en adelante: doble clic a ESTE bat y ya.
    pause
    exit /b 1
)

echo   [1/3] Bajando la ultima version...
git pull --ff-only
if errorlevel 1 (
    echo.
    echo   ERROR al bajar la actualizacion. Causas tipicas:
    echo    - sin internet o sin acceso al repositorio ^(credenciales^)
    echo    - archivos del sistema tocados a mano en esta carpeta
    echo   Ver el mensaje de arriba. No se cambio nada.
    pause
    exit /b 1
)

echo   [2/3] Compilando la pantalla...
cd frontend
call npm run build >nul 2>&1
if errorlevel 1 (
    echo   ERROR compilando la pantalla. Correr a mano para ver el detalle:
    echo      cd frontend ^&^& npm run build
    pause
    exit /b 1
)
cd ..

echo   [3/3] Listo.
echo.
echo   ===========================================================
echo     ACTUALIZADO. Falta un solo paso a mano:
echo     reiniciar el servidor ^(cerrar la ventana donde corre
echo     "py servidor.py" y volver a abrir iniciar.bat^).
echo   ===========================================================
echo.
pause
