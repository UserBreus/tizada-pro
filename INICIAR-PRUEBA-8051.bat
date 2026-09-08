@echo off
REM ------------------------------------------------------------------------
REM  TIZADA PRO - PRUEBA DEL CAMINO B  (puerto 8051)
REM
REM  QUE ES: la prueba del molde que ya trae el diseno adentro. Es un CLON
REM  independiente, con su propio git y su propia rama
REM  (pruebas-tizada-con-diseno). NO comparte archivos con el sistema de
REM  produccion: lo que se toque aca no puede llegar al 8050 ni al servidor
REM  publicado.
REM
REM  DATOS: usa sus PROPIAS carpetas datos/ entrada/ trabajos/, vacias. Asi
REM  las pruebas no escriben sobre los moldes del taller.
REM  BASE: usa su PROPIA base MSSQL (TizadaProCaminoB), separada de la del
REM  taller (TizadaPro). Antes era la misma y todo molde de prueba aparecia
REM  en el catalogo de verdad. Su usuario admin es propio de esta base: si
REM  hace falta la contrasena, se saca con
REM     set TIZADA_DB_NAME=TizadaProCaminoB
REM     py -c "import auth; print(auth.bootstrap())"
REM  (con la base sin usuarios). El catalogo del taller no se toca nunca.
REM
REM  El sistema de verdad sigue en la carpeta "TIZADA PRO", puerto 8050.
REM ------------------------------------------------------------------------
title TIZADA PRO - PRUEBA camino B (8051)
cd /d "%~dp0"

set "PORT=8051"
set "TIZADA_DB_NAME=TizadaProCaminoB"
set "TIZADA_DATOS=%~dp0datos"
set "TIZADA_ENTRADA=%~dp0entrada"
set "TIZADA_TRABAJOS=%~dp0trabajos"
set "TIZADA_FUENTES=%~dp0catalogo_fuentes"

echo.
echo   TIZADA PRO - PRUEBA del camino B
echo   http://127.0.0.1:8051
echo.
py servidor.py
pause
