@echo off
REM ============================================================================
REM  TIZADA PRO - MODO PUBLICADO (para que lo usen desde afuera)
REM
REM  Diferencias con iniciar.bat (el de todos los dias):
REM    - usa WAITRESS, un servidor de verdad (el otro es de desarrollo: un hilo
REM      por conexion, sin limite de cola, se cae con varios usuarios)
REM    - usa una clave de sesion FIJA (config_publicado.env): sin ella, cada
REM      reinicio desloguea a todos
REM    - escucha en 0.0.0.0 -> acepta conexiones de otras maquinas
REM
REM  IMPORTANTE: esto NO cifra. Delante tiene que ir el HTTPS. Mientras se
REM  prueba dentro de la red de casa, TIZADA_HTTPS=0 permite entrar por http://
REM  (si no, el navegador no guarda la sesion y no se puede ni entrar).
REM ============================================================================
title TIZADA PRO - PUBLICADO
cd /d "%~dp0"
where py >nul 2>nul && (set "PY=py") || (set "PY=python")

REM --- clave de sesion: se genera UNA vez y queda guardada (no se versiona) ---
if not exist "config_publicado.env" (
  echo Generando la clave de sesion (primera vez)...
  %PY% -c "import secrets;open('config_publicado.env','w').write('TIZADA_SECRET='+secrets.token_hex(32)+'\n')"
)
for /f "usebackq tokens=1,* delims==" %%A in ("config_publicado.env") do set "%%A=%%B"

if "%TIZADA_SECRET%"=="" (
  echo [ERROR] No se pudo leer TIZADA_SECRET de config_publicado.env
  pause
  exit /b 1
)

set "TIZADA_MODO=publicado"
if "%PORT%"=="" set "PORT=8443"
set "TIZADA_HILOS=8"

REM --- HTTPS: si esta el certificado, lo hace el propio servidor (cheroot) ---
if exist "certificados\tizada.crt" (
  set "TIZADA_TLS_CERT=%~dp0certificados\tizada.crt"
  set "TIZADA_TLS_KEY=%~dp0certificados\tizada.key"
  set "TIZADA_HTTPS=1"
  set "ESQUEMA=https"
) else (
  echo   [AVISO] No hay certificado: se arranca SIN cifrar, solo sirve para probar
  echo           en tu red. Genera uno con GENERAR-CERTIFICADO.bat antes de abrir
  echo           el puerto en el router.
  set "TIZADA_HTTPS=0"
  set "ESQUEMA=http"
)

echo.
echo   MODO PUBLICADO . puerto %PORT% . %TIZADA_HILOS% hilos
echo   Desde esta PC:      %ESQUEMA%://localhost:%PORT%
echo   Desde la red:       %ESQUEMA%://192.168.0.120:%PORT%
echo.
%PY% servidor.py
pause
