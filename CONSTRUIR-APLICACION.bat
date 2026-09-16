@echo off
REM ============================================================================
REM  TIZADA PRO - ARMAR LA APLICACION DE WINDOWS (con su instalador)
REM  Doble clic. Deja:  escritorio\salida\Instalar TIZADA PRO <version>.exe
REM  Ese archivo es el que se lleva a otra PC: se instala solo, sin permisos de
REM  administrador. La PC donde se instala necesita SQL Server Express.
REM
REM  No toca el sistema del taller ni sus datos: arma todo en la carpeta escritorio\
REM  con un Python propio (escritorio\.venv) y las MISMAS versiones de las
REM  bibliotecas que usa el sistema (escritorio\requisitos_fijos.txt).
REM ============================================================================
title Armar la aplicacion TIZADA PRO
color 0B
cd /d "%~dp0"
REM  TIZADA_ARMADO_SILENCIOSO=1: sin pausas ni ventana del explorador (para armarlo desde otra herramienta)
set "PAUSA=pause"
if defined TIZADA_ARMADO_SILENCIOSO set "PAUSA=rem"

echo.
echo  [1/4] Compilando la pantalla...
pushd frontend
call npm run build >nul
if errorlevel 1 ( popd & echo  [X] No compilo la pantalla. & %PAUSA% & exit /b 1 )
popd

echo  [2/4] Preparando el Python de la aplicacion (la primera vez tarda unos minutos)...
if not exist "escritorio\.venv\Scripts\python.exe" (
  py -m venv escritorio\.venv
  if errorlevel 1 ( echo  [X] No se pudo crear el entorno de Python. & %PAUSA% & exit /b 1 )
)
escritorio\.venv\Scripts\python.exe -m pip install -q --disable-pip-version-check -r escritorio\requisitos_fijos.txt
if errorlevel 1 ( echo  [X] No se pudieron instalar las bibliotecas. & %PAUSA% & exit /b 1 )

echo  [3/4] Empaquetando el programa...
escritorio\.venv\Scripts\pyinstaller.exe --noconfirm --clean --log-level WARN --distpath escritorio\dist --workpath escritorio\build escritorio\TizadaPro.spec
if errorlevel 1 ( echo  [X] No se pudo empaquetar. & %PAUSA% & exit /b 1 )

echo  [4/4] Armando y probando el instalador...
escritorio\.venv\Scripts\python.exe escritorio\armar_instalador.py
if errorlevel 1 ( echo  [X] No se pudo armar el instalador. & %PAUSA% & exit /b 1 )

echo.
echo  Listo. El instalador esta en la carpeta escritorio\salida
if not defined TIZADA_ARMADO_SILENCIOSO explorer "escritorio\salida"
%PAUSA%
