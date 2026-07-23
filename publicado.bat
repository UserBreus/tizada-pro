@echo off
REM ============================================================================
REM  TIZADA PRO — arranque del SERVIDOR PUBLICADO (el de internet).
REM  Para el taller (la maquina de todos los dias) seguir usando iniciar.bat.
REM  Ver PLAN_PUBLICACION.md.
REM
REM  COMPLETAR antes de usar:
REM   TIZADA_SECRET  clave fija de sesion. Generala UNA vez y no la cambies mas
REM                  (si cambia, se cierra la sesion de todos):
REM                      py -c "import secrets;print(secrets.token_hex(32))"
REM   TIZADA_DATOS / TIZADA_ENTRADA / TIZADA_TRABAJOS  carpetas de datos del
REM                  servidor (conviene un disco aparte, para el backup).
REM ============================================================================
title TIZADA PRO - PUBLICADO
cd /d "%~dp0"

set TIZADA_MODO=publicado
set TIZADA_SECRET=PONER_LA_CLAVE_ACA
set PORT=8050
set HOST=127.0.0.1
REM  HOST=127.0.0.1 a proposito: el que da la cara a internet es el proxy inverso
REM  (el que pone el HTTPS). Si se expone el puerto directo, poner 0.0.0.0 y
REM  TIZADA_HTTPS=0 SOLO mientras no haya certificado.

REM set TIZADA_DATOS=D:\tizada\datos
REM set TIZADA_ENTRADA=D:\tizada\entrada
REM set TIZADA_TRABAJOS=D:\tizada\trabajos
REM set TIZADA_HILOS=8

REM  MEMORIA: cada proceso de render pesa ~200 MB (medido). Sin esta variable usa hasta 6
REM  procesos = ~1.2 GB. En un servidor con ~1 GB libre, poner 2 (o 1 si queda corto).
set TIZADA_PROCESOS=2

if "%TIZADA_SECRET%"=="PONER_LA_CLAVE_ACA" (
  echo.
  echo  [ERROR] Falta poner TIZADA_SECRET en este archivo.
  echo          Genera una con:  py -c "import secrets;print^(secrets.token_hex^(32^)^)"
  echo.
  pause
  exit /b 1
)

where py >nul 2>nul && (py servidor.py) || (python servidor.py)
pause
