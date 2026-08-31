@echo off
REM ------------------------------------------------------------------------
REM  Deshace INSTALAR-ARRANQUE-AUTOMATICO.bat: el sistema deja de arrancar solo.
REM  El servidor que este andando NO se apaga; para eso, CERRAR-SERVIDOR.bat
REM ------------------------------------------------------------------------
title TIZADA PRO - quitar arranque automatico
cd /d "%~dp0"
echo.
schtasks /delete /tn "TIZADA PRO" /f
echo.
echo   Listo. Ahora hay que arrancarlo a mano con INICIAR-SIN-VENTANA.vbs
echo.
pause
