@echo off
REM ===========================================================================
REM   TIZADA PRO - INSTALADOR PARA EL SERVIDOR
REM
REM   Clic DERECHO en este archivo -> "Ejecutar como administrador".
REM   Hace TODO solo (incluso instalar Python si no esta) y deja el detalle en
REM   instalacion_log.txt, al lado de este archivo.
REM ===========================================================================
title Instalar TIZADA PRO en el servidor
cd /d "%~dp0"
color 0F

REM ---------- 0) Pedir permisos de administrador SOLO (sin clic derecho) ----------
REM  Hacen falta para nginx y para el arranque automatico. Si no los tiene, se
REM  relanza pidiendolos: Windows muestra el cartel de "Desea permitir...", se
REM  dice que SI y sigue. Sin esto habia que acordarse del clic derecho.
net session >nul 2>&1
if not errorlevel 1 goto ES_ADMIN
echo.
echo  Pidiendo permisos de administrador (deci que SI en el cartel de Windows)...
powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs" >nul 2>&1
if errorlevel 1 (
  echo.
  echo  [X] No se pudieron pedir los permisos.
  echo      Hace clic DERECHO en este archivo y elegi "Ejecutar como administrador".
  echo.
  pause
)
exit /b
:ES_ADMIN
cd /d "%~dp0"
echo.
echo  ============================================================
echo    INSTALADOR DE TIZADA PRO
echo    No cierres esta ventana. Al final te dice como quedo.
echo  ============================================================
echo.

REM ---------- 1) Buscar Python ----------
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY (
  for %%D in ("%ProgramFiles%\Python312" "%ProgramFiles%\Python311" "%LocalAppData%\Programs\Python\Python312") do (
     if exist "%%~D\python.exe" set "PY=%%~D\python.exe"
  )
)

REM ---------- 2) Si no esta, instalarlo solo ----------
if not defined PY (
  echo  [1/2] Este servidor no tiene Python. Lo descargo e instalo yo.
  echo        Son unos 30 MB, tarda 2 o 3 minutos. NO cierres la ventana.
  echo.
  powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe' -OutFile \"$env:TEMP\tizada-python.exe\""
  if not exist "%TEMP%\tizada-python.exe" (
     echo.
     echo  [X] No se pudo descargar Python ^(sin internet en el servidor?^).
     echo      Instalalo a mano desde https://www.python.org/downloads/
     echo      tildando "Add python.exe to PATH", y volve a ejecutar este archivo.
     echo.
     pause
     exit /b 1
  )
  echo        Instalando...
  start /wait "" "%TEMP%\tizada-python.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1
  for %%D in ("%ProgramFiles%\Python312" "%LocalAppData%\Programs\Python\Python312") do (
     if exist "%%~D\python.exe" set "PY=%%~D\python.exe"
  )
  if not defined PY (where py >nul 2>nul && set "PY=py")
  if not defined PY (
     echo.
     echo  [X] Python se instalo pero no lo encuentro. Cerra esta ventana,
     echo      abri otra y volve a ejecutar este archivo.
     echo.
     pause
     exit /b 1
  )
  echo        Python instalado.
  echo.
)

REM ---------- 3) Instalar TIZADA PRO ----------
echo  [2/2] Instalando TIZADA PRO...
echo.
"%PY%" -u instalar_servidor.py %*

echo.
echo  ============================================================
echo    El detalle quedo en:  %~dp0instalacion_log.txt
echo    Si algo fallo, mandale ese archivo a quien te ayuda.
echo  ============================================================
echo.
pause
