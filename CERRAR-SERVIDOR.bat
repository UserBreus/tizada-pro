@echo off
REM ------------------------------------------------------------------------
REM  TIZADA PRO - apaga el servidor.
REM
REM  Deja una bandera en logs\apagado.flag para que el vigilante NO lo reviva.
REM  Sin eso, la tarea de Windows lo volveria a levantar a los 2 minutos y no
REM  habria manera de apagarlo. La bandera se borra sola al volver a iniciar,
REM  y caduca a los 15 minutos por las dudas.
REM ------------------------------------------------------------------------
title Cerrar TIZADA PRO
cd /d "%~dp0"
if not exist "logs" mkdir "logs"
echo. > "logs\apagado.flag"
schtasks /end /tn "TIZADA PRO" >nul 2>nul
echo Buscando el servidor en el puerto 8050...
powershell -NoProfile -Command "$p = Get-NetTCPConnection -LocalPort 8050 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; if ($p) { $p | ForEach-Object { Write-Host ('  cerrando PID ' + $_); Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }; Write-Host ''; Write-Host '  Sistema apagado.' } else { Write-Host ''; Write-Host '  No habia ningun servidor corriendo.' }"
echo.
ping -n 4 127.0.0.1 >nul
