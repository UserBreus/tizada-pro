@echo off
REM ============================================================================
REM  TIZADA PRO - ARRANQUE DEL SERVIDOR PUBLICADO (el de internet).
REM  Para la maquina del taller seguir usando iniciar.bat.
REM
REM  SE USA ASI: doble clic. Nada mas.
REM   - Si falta waitress, lo instala solo.
REM   - Si falta la clave de sesion, la genera sola y la guarda en secret.txt
REM     (se genera UNA vez: si cambiara, se cerraria la sesion de todos).
REM ============================================================================
title TIZADA PRO - PUBLICADO
cd /d "%~dp0"

REM --- interprete de Python ---------------------------------------------------
where py >nul 2>nul && (set "PY=py") || (set "PY=python")

REM --- waitress: es el servidor de VERDAD --------------------------------------
REM  Sin el, Flask usa su servidor de DESARROLLO: corta las descargas grandes a
REM  mitad de camino y el navegador muestra ERR_QUIC_PROTOCOL_ERROR / ERR_FAILED.
%PY% -c "import waitress" >nul 2>nul || (
  echo Instalando waitress ...
  %PY% -m pip install waitress
)

REM --- clave de sesion: se genera UNA sola vez y queda en secret.txt -----------
if not exist "%~dp0secret.txt" (
  echo Generando la clave de sesion ^(una sola vez^) ...
  %PY% -c "import secrets;open(r'%~dp0secret.txt','w').write(secrets.token_hex(32))"
)
for /f "usebackq delims=" %%K in ("%~dp0secret.txt") do set "TIZADA_SECRET=%%K"

REM --- configuracion ----------------------------------------------------------
set TIZADA_MODO=publicado
set PORT=8050
set HOST=127.0.0.1
REM  HOST=127.0.0.1 a proposito: el que da la cara a internet es el proxy/IIS de
REM  adelante (el del HTTPS). Si se expone el puerto directo, poner 0.0.0.0.

REM  MEMORIA: cada proceso de render pesa ~200 MB. Sin esto usa hasta 6 (~1.2 GB).
set TIZADA_PROCESOS=2
REM set TIZADA_HILOS=8

REM  Carpetas de datos del servidor (descomentar si van en otro disco):
REM set TIZADA_DATOS=D:\tizada\datos
REM set TIZADA_ENTRADA=D:\tizada\entrada
REM set TIZADA_TRABAJOS=D:\tizada\trabajos

REM --- cerrar el servidor anterior del puerto ---------------------------------
echo Cerrando el servidor anterior del puerto %PORT% ...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort %PORT% -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }" 2>nul

echo.
echo  Arrancando en modo PUBLICADO ^(waitress^) ...
echo  Tiene que decir:  modo PUBLICADO . waitress
echo.
%PY% servidor.py
pause
