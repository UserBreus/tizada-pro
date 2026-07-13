@echo off
title Motor de Sublimacion
cd /d "%~dp0"
echo Cerrando cualquier servidor anterior en el puerto 8050...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8050 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }" 2>nul
echo Iniciando servidor (se actualiza solo cuando cambia el codigo)...
where py >nul 2>nul && (py servidor.py) || (python servidor.py)
pause
