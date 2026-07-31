@echo off
REM ============================================================================
REM  TIZADA PRO - INSTALAR EN OTRA COMPUTADORA
REM
REM  Copiar ESTE archivo solo (o bajarlo del repositorio) a la PC nueva, ponerlo
REM  en la carpeta donde quieras que viva el sistema, y hacerle doble clic.
REM
REM  Hace todo: baja el sistema, instala lo que necesita y deja la pantalla
REM  compilada. Lo unico que pide es la cuenta de GitHub (el repositorio es
REM  privado) y eso lo escribis vos en la ventana que abre Windows.
REM
REM  OJO: esto trae el SISTEMA, no tus datos. Los moldes, los disenos y los
REM  pedidos se copian aparte -> ver COPIAR-MIS-DATOS.bat
REM ============================================================================
title TIZADA PRO - Instalar en esta PC
color 0B
cd /d "%~dp0"

echo.
echo   ===========================================================
echo     TIZADA PRO - Instalacion en esta computadora
echo   ===========================================================
echo.

REM --- 1) Revisar que este todo lo necesario -------------------------------
set "FALTA="
echo   [1/5] Revisando que este instalado lo necesario...
echo.

where git >nul 2>nul
if errorlevel 1 (
  echo      FALTA  Git          ^-^> bajalo de: https://git-scm.com/download/win
  set "FALTA=1"
) else ( echo      OK     Git )

where py >nul 2>nul
if errorlevel 1 (
  where python >nul 2>nul
  if errorlevel 1 (
    echo      FALTA  Python      ^-^> bajalo de: https://www.python.org/downloads/
    echo             ^(al instalar, TILDAR "Add Python to PATH"^)
    set "FALTA=1"
  ) else ( set "PY=python" & echo      OK     Python )
) else ( set "PY=py" & echo      OK     Python )

where npm >nul 2>nul
if errorlevel 1 (
  echo      FALTA  Node.js      ^-^> bajalo de: https://nodejs.org  ^(version LTS^)
  set "FALTA=1"
) else ( echo      OK     Node.js )

if defined FALTA (
  echo.
  echo   ===========================================================
  echo     Instala lo que dice FALTA, reinicia la PC y volve a
  echo     hacerle doble clic a este archivo.
  echo   ===========================================================
  echo.
  pause
  exit /b 1
)

REM --- 2) Bajar el sistema --------------------------------------------------
echo.
echo   [2/5] Bajando el sistema desde GitHub...
echo         ^(si te pide usuario y clave, es la cuenta de GitHub^)
echo.
if exist "tizada-pro\.git" (
  echo         Ya estaba bajado: se actualiza a la ultima version.
  cd tizada-pro
  git fetch origin
  git checkout entrega-programadores
  git pull origin entrega-programadores
) else (
  git clone -b entrega-programadores https://github.com/UserBreus/tizada-pro.git
  if errorlevel 1 (
    echo.
    echo   [X] No se pudo bajar. Suele ser por la cuenta de GitHub:
    echo       revisa que tengas permiso sobre el repositorio.
    echo.
    pause
    exit /b 1
  )
  cd tizada-pro
)

REM --- 3) Instalar lo que usa el sistema ------------------------------------
echo.
echo   [3/5] Instalando lo que usa el sistema ^(tarda unos minutos^)...
echo.
%PY% -m pip install --upgrade pip >nul 2>nul
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo   [X] Fallo la instalacion. Copiá el error de arriba y pedí ayuda.
  echo.
  pause
  exit /b 1
)

REM --- 4) Preparar la pantalla ---------------------------------------------
echo.
echo   [4/5] Preparando la pantalla ^(tarda unos minutos la primera vez^)...
echo.
cd frontend
call npm install
if errorlevel 1 ( echo   [X] Fallo npm install & pause & exit /b 1 )
call npm run build
if errorlevel 1 ( echo   [X] Fallo la compilacion de la pantalla & pause & exit /b 1 )
cd ..

REM --- 5) Listo -------------------------------------------------------------
echo.
echo   [5/5] Listo.
echo.
echo   ===========================================================
echo     EL SISTEMA YA ESTA INSTALADO EN ESTA PC
echo   ===========================================================
echo.
echo   Para usarlo: doble clic en  iniciar.bat  ^(en esta misma carpeta^)
echo   y despues abri  http://localhost:8050  en el navegador.
echo.
echo   FALTAN TUS DATOS: los moldes, los disenos y los pedidos NO
echo   viajan por GitHub. En la PC de siempre corre COPIAR-MIS-DATOS.bat,
echo   llevate la carpeta que arma y pegala aca adentro.
echo.
echo   Si el sistema usa la base de datos SQL Server, ademas hay que
echo   configurar la conexion ^(ver ENTREGA_PROGRAMADOR.md, punto 4^).
echo.
pause
