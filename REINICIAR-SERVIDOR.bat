@echo off
REM ------------------------------------------------------------------------
REM  TIZADA PRO - reinicia el servidor DE VERDAD (para que tome codigo nuevo).
REM
REM  POR QUE EXISTE: `schtasks /end` termina la TAREA pero no siempre se lleva al
REM  proceso de Python que cuelga de ella. Como _arrancar-oculto.bat es idempotente
REM  (si el 8050 contesta, no hace nada), el `schtasks /run` de despues no arrancaba
REM  nada: el servidor VIEJO seguia atendiendo. Paso de verdad el 2026-08-27: dos
REM  horas y media de cambios en Python que nunca llegaron a correr.
REM
REM  Por eso aca se MATA el proceso del puerto primero, y sin dejar la bandera de
REM  apagado (esa es para CERRAR-SERVIDOR.bat, que si apaga a proposito).
REM ------------------------------------------------------------------------
title Reiniciar TIZADA PRO
cd /d "%~dp0"
if not exist "logs" mkdir "logs"
if exist "logs\apagado.flag" del /q "logs\apagado.flag"
echo Cerrando el servidor actual...
schtasks /end /tn "TIZADA PRO" >nul 2>nul
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8050 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
powershell -NoProfile -Command "Start-Sleep -Seconds 2"
echo Arrancando de nuevo...
schtasks /run /tn "TIZADA PRO" >nul 2>nul
powershell -NoProfile -Command "$ok=$false; foreach ($i in 1..40) { Start-Sleep -Seconds 2; try { if ((Invoke-WebRequest 'http://127.0.0.1:8050/api/salud' -UseBasicParsing -TimeoutSec 4).StatusCode -eq 200) { $ok=$true; break } } catch { } }; if ($ok) { $p = Get-NetTCPConnection -LocalPort 8050 -State Listen | Select-Object -ExpandProperty OwningProcess -Unique; Write-Host ('  Listo. Arrancado a las ' + (Get-Process -Id $p).StartTime.ToString('HH:mm:ss')) } else { Write-Host '  NO levanto: mira logs\servidor.log' }"
echo.
ping -n 4 127.0.0.1 >nul
