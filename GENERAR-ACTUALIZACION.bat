@echo off
REM ============================================================================
REM  TIZADA PRO - GENERAR ACTUALIZACION PARA MANDAR
REM
REM  Doble clic y listo: deja en el Escritorio un ZIP con el sistema completo
REM  (codigo + pantalla ya compilada) para mandarselo a quien lo tiene
REM  instalado en un servidor. El que lo recibe lo extrae SOBRE la carpeta
REM  del sistema y reinicia: las instrucciones van adentro del ZIP
REM  (LEEME-ACTUALIZACION.txt).
REM
REM  El ZIP NO lleva datos del cliente: ni datos/, ni entrada/, ni trabajos/,
REM  ni config_externo.json (la clave de la API de telas). Solo codigo.
REM ============================================================================
title TIZADA PRO - Generar actualizacion
color 0B
cd /d "%~dp0"

echo.
echo   ===========================================================
echo     TIZADA PRO - Generar actualizacion para mandar
echo   ===========================================================
echo.

REM --- 0) Avisar si hay cambios sin guardar en git --------------------------
for /f %%A in ('git status --porcelain 2^>nul ^| find /c /v ""') do set PEND=%%A
if not "%PEND%"=="0" (
    echo   AVISO: hay %PEND% archivos con cambios sin commitear en git.
    echo   Esos cambios NO van a viajar en el ZIP. Si tienen que ir,
    echo   pedile a Claude que los suba y volve a correr esto.
    echo.
)

echo   [1/4] Compilando la pantalla (frontend)...
cd frontend
call npm run build >nul 2>&1
if errorlevel 1 (
    echo.
    echo   ERROR: no se pudo compilar la pantalla. Corre a mano:
    echo      cd frontend ^&^& npm run build
    echo   y fijate el error que muestra.
    pause
    exit /b 1
)
cd ..

echo   [2/4] Empaquetando el codigo (sin datos del cliente)...
set STAGE=%TEMP%\tizada_actualizacion
if exist "%STAGE%" rmdir /s /q "%STAGE%"
mkdir "%STAGE%"
git archive --format=zip -o "%STAGE%\codigo.zip" HEAD
if errorlevel 1 (
    echo   ERROR: fallo git archive. ^(Esta carpeta tiene que ser el repo git.^)
    pause
    exit /b 1
)
powershell -NoProfile -Command "Expand-Archive -Path '%STAGE%\codigo.zip' -DestinationPath '%STAGE%\sistema' -Force"
del "%STAGE%\codigo.zip"

echo   [3/4] Agregando la pantalla ya compilada...
xcopy /E /I /Y /Q frontend\dist "%STAGE%\sistema\frontend\dist" >nul

echo   [4/4] Creando el ZIP en el Escritorio...
for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`) do set DESK=%%D
for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"`) do set FECHA=%%F
set SALIDA=%DESK%\actualizacion_TIZADA_%FECHA%.zip
if exist "%SALIDA%" del "%SALIDA%"
powershell -NoProfile -Command "Compress-Archive -Path '%STAGE%\sistema\*' -DestinationPath '%SALIDA%' -Force"
if errorlevel 1 (
    echo   ERROR: no se pudo crear el ZIP.
    pause
    exit /b 1
)
rmdir /s /q "%STAGE%"

echo.
echo   ===========================================================
echo     LISTO. El archivo para mandar quedo en el Escritorio:
echo.
echo     %SALIDA%
echo.
echo     Mandaselo como mandaste el RAR ^(Drive, WhatsApp, mail^).
echo     El que lo recibe sigue el LEEME-ACTUALIZACION.txt que va
echo     adentro: extraer sobre la carpeta del sistema y reiniciar.
echo   ===========================================================
echo.
pause
