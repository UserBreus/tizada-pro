@echo off
REM ============================================================================
REM  TIZADA PRO - COPIAR MIS DATOS (para llevarlos a otra PC)
REM
REM  Arma una carpeta con TODO lo tuyo: los moldes, los disenos, las tipografias,
REM  los pedidos generados y la configuracion. Eso NO viaja por GitHub (son tus
REM  archivos, no el programa), asi que hay que llevarlo a mano: pendrive, disco
REM  o carpeta compartida.
REM
REM  En la PC nueva: pegar el CONTENIDO de esa carpeta adentro de la carpeta del
REM  sistema, reemplazando lo que pregunte.
REM ============================================================================
title TIZADA PRO - Copiar mis datos
color 0B
cd /d "%~dp0"

set "DESTINO=%~dp0MIS-DATOS-TIZADA"

echo.
echo   ===========================================================
echo     TIZADA PRO - Copiar mis datos para llevarlos a otra PC
echo   ===========================================================
echo.
echo   Se va a armar esta carpeta:
echo     %DESTINO%
echo.

if exist "%DESTINO%" (
  echo   Ya existe de una vez anterior: se va a actualizar.
  echo.
)
if not exist "%DESTINO%" mkdir "%DESTINO%"

echo   [1/4] Copiando la base de datos y la configuracion...
if exist "datos" ( robocopy "datos" "%DESTINO%\datos" /E /NFL /NDL /NJH /NJS /nc /ns /np >nul ) else ( echo         ^(no hay carpeta datos^) )

echo   [2/4] Copiando los moldes y los disenos...
if exist "entrada" ( robocopy "entrada" "%DESTINO%\entrada" /E /NFL /NDL /NJH /NJS /nc /ns /np >nul ) else ( echo         ^(no hay carpeta entrada^) )

echo   [3/4] Copiando las tipografias...
if exist "catalogo_fuentes" ( robocopy "catalogo_fuentes" "%DESTINO%\catalogo_fuentes" /E /NFL /NDL /NJH /NJS /nc /ns /np >nul ) else ( echo         ^(no hay tipografias^) )

echo   [4/4] Copiando la configuracion de la API de telas...
if exist "config_externo.json" ( copy /Y "config_externo.json" "%DESTINO%\" >nul ) else ( echo         ^(no hay config_externo.json^) )

REM Los pedidos ya generados son opcionales: suelen pesar mucho.
echo.
set /p LLEVAR="   Llevar tambien los pedidos ya generados? (pesan bastante) [s/N]: "
if /i "%LLEVAR%"=="s" (
  echo   Copiando pedidos generados...
  if exist "trabajos" robocopy "trabajos" "%DESTINO%\trabajos" /E /NFL /NDL /NJH /NJS /nc /ns /np >nul
)

echo.
echo   ===========================================================
echo     LISTO
echo   ===========================================================
echo.
echo   Tus datos quedaron en:
echo     %DESTINO%
echo.
echo   QUE HACER AHORA:
echo     1. Copia esa carpeta a un pendrive.
echo     2. En la PC nueva, entra a la carpeta del sistema
echo        ^(la que armo INSTALAR-EN-OTRA-PC.bat^).
echo     3. Pega ADENTRO el contenido de MIS-DATOS-TIZADA
echo        ^(las carpetas datos, entrada, catalogo_fuentes y el archivo
echo         config_externo.json^). Si pregunta, reemplazar.
echo.
echo   OJO: si las dos PC van a trabajar con los MISMOS pedidos al mismo
echo   tiempo, no alcanza con copiar: hay que conectarlas a la misma base
echo   de datos. Preguntá antes de hacerlo asi.
echo.
pause
