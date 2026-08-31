@echo off
REM ------------------------------------------------------------------------
REM  Se ejecuta UNA SOLA VEZ. Deja TIZADA PRO andando como un servicio:
REM  arranca solo con la maquina y, si se cayera, vuelve solo.
REM  Para deshacerlo: QUITAR-ARRANQUE-AUTOMATICO.bat
REM ------------------------------------------------------------------------
title TIZADA PRO - arranque automatico
cd /d "%~dp0"
echo.
echo   Instalando el arranque automatico de TIZADA PRO...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0_instalar-tarea.ps1"
echo.
pause
