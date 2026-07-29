@echo off
REM ============================================================================
REM  TIZADA PRO - LIBERAR ESPACIO EN DISCO
REM
REM  El disco lleno rompe TODO y de formas que no parecen de disco:
REM    - no se puede publicar        -> "HTTP Error 500"
REM    - se cortan las descargas     -> ERR_QUIC_PROTOCOL_ERROR / pantalla en blanco
REM    - falla al generar la tizada  -> std::bad_alloc (Windows no puede agrandar
REM      el archivo de paginacion, y las reservas de memoria fallan)
REM
REM  Borra SOLO cosas que se pueden volver a generar:
REM    trabajos\      tizadas YA generadas (mas viejas que los dias que elijas)
REM    dist\*.zip     paquetes de instalacion viejos
REM    *_cache        caches de deteccion y de render (se rehacen solas)
REM  NO toca datos\ ni entrada\: ahi viven los moldes, los disenos y la config.
REM ============================================================================
title TIZADA PRO - Liberar espacio
cd /d "%~dp0"
where py >nul 2>nul && (set "PY=py") || (set "PY=python")

echo.
echo  ESPACIO EN DISCO
powershell -NoProfile -Command "Get-PSDrive -Name ((Get-Location).Drive.Name) | ForEach-Object { '   libre: {0:N1} GB de {1:N1} GB' -f ($_.Free/1GB), (($_.Free+$_.Used)/1GB) }"
echo.
echo  QUE OCUPA CADA COSA
%PY% -c "import os;f=lambda p:sum(os.path.getsize(os.path.join(r,x)) for r,_,fs in os.walk(p) for x in fs if os.path.exists(os.path.join(r,x)));[print('   %-16s %8.1f MB'%(d,f(d)/2**20)) for d in ('trabajos','dist','datos','entrada') if os.path.isdir(d)]" 2>nul
echo.

set "DIAS="
set /p DIAS=  Borrar las tizadas de mas de cuantos DIAS? (Enter = 15, 0 = todas):
if "%DIAS%"=="" set DIAS=15

echo.
echo  Se van a borrar las carpetas de trabajos\ con mas de %DIAS% dia(s).
echo  Son tizadas YA generadas: los moldes y disenos NO se tocan.
choice /c SN /n /m "  Seguro? (S/N): "
if errorlevel 2 goto :fin

echo.
echo  Limpiando ...
powershell -NoProfile -Command ^
  "$d=[int]'%DIAS%'; $lim=(Get-Date).AddDays(-$d); $n=0; $mb=0;" ^
  "if (Test-Path 'trabajos') { Get-ChildItem 'trabajos' -Directory | Where-Object { $_.LastWriteTime -lt $lim } | ForEach-Object {" ^
  "  $mb += ((Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum)/1MB;" ^
  "  Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue; $n++ } }" ^
  "Get-ChildItem 'dist\*.zip' -ErrorAction SilentlyContinue | ForEach-Object { $mb += $_.Length/1MB; Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue };" ^
  "Get-ChildItem 'datos\productos' -Directory -ErrorAction SilentlyContinue | ForEach-Object {" ^
  "  foreach ($c in 'deteccion_cache','piezas_cache') { $p=Join-Path $_.FullName $c; if (Test-Path $p) {" ^
  "    $mb += ((Get-ChildItem $p -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum)/1MB;" ^
  "    Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue } } };" ^
  "'   {0} tizada(s) borrada(s) - {1:N0} MB liberados' -f $n, $mb"

echo.
echo  ESPACIO AHORA
powershell -NoProfile -Command "Get-PSDrive -Name ((Get-Location).Drive.Name) | ForEach-Object { '   libre: {0:N1} GB de {1:N1} GB' -f ($_.Free/1GB), (($_.Free+$_.Used)/1GB) }"
echo.
echo  Listo. Las caches se rehacen solas la proxima vez (la 1a carga tarda un poco mas).

:fin
echo.
pause
