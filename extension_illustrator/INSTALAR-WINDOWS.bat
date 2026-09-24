@echo off
rem USER PRO para Illustrator - instalador manual (Windows). Lo comun es el .exe.
rem Copia la extension a la carpeta de extensiones de Adobe del usuario y habilita las extensiones
rem sin firma de Adobe (PlayerDebugMode) para todas las versiones de Illustrator.
setlocal
set "DEST=%APPDATA%\Adobe\CEP\extensions\com.tizadapro.illustrator"
echo Instalando USER PRO para Illustrator...
if exist "%DEST%" rmdir /s /q "%DEST%"
xcopy /e /i /y /q "%~dp0com.tizadapro.illustrator" "%DEST%" >nul
if errorlevel 1 (
  echo.
  echo No se pudo copiar la extension a "%DEST%".
  pause
  exit /b 1
)
for %%v in (9 10 11 12 13 14 15 16) do reg add "HKCU\Software\Adobe\CSXS.%%v" /v PlayerDebugMode /t REG_SZ /d 1 /f >nul
echo.
echo Listo. Cerra Illustrator (si esta abierto) y volve a abrirlo.
echo En Illustrator: Ventana ^> Extensiones ^> USER PRO muestra si esta conectada.
echo.
pause
