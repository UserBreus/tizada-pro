@echo off
REM ------------------------------------------------------------------------
REM  Levanta el servidor y se queda ahi hasta que termine. NO se ejecuta a mano:
REM  lo llama _vigilante.vbs, que es quien decide cuando y quien lo vuelve a
REM  levantar. Para verlo en pantalla usa iniciar.bat.
REM
REM  OJO: aca NO se mata a nadie. Antes este archivo cerraba lo que estuviera en
REM  el 8050 si /api/salud no contestaba en 5 segundos -- y armando una tizada el
REM  servidor puede tardar mas que eso: el vigilante lo habria matado en plena
REM  produccion. Si algo esta escuchando el 8050, se respeta.
REM ------------------------------------------------------------------------
cd /d "%~dp0"
if not exist "logs" mkdir "logs"
REM  El log del servidor NO rotaba: lo escribe este .bat con `>` y solo se truncaba al reiniciar.
REM  Con un servidor que no se reinicia en meses (que es el objetivo del vigilante) crecia ~85 MB
REM  al mes, mientras que `consola.log` si rota (registro.py, tope 4 MB). Se conserva UNA vuelta
REM  anterior y se arranca limpio: asi nunca pasa de dos archivos (auditoria 2026-09-14).
if exist "logs\servidor.log" move /y "logs\servidor.log" "logs\servidor.anterior.log" >nul 2>nul
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py servidor.py > "logs\servidor.log" 2>&1
) else (
  python servidor.py > "logs\servidor.log" 2>&1
)
