@echo off
REM ===========================================================================
REM  TIZADA PRO - Limpieza de carpetas viejas (v2) - se corre EN EL SERVIDOR
REM  Protege al sistema (el que atiende el puerto 8050 en C:\TIZADAPRO) y cierra
REM  todo lo demas que quedo colgado de instalaciones viejas: procesos python
REM  sueltos, consolas y hasta ventanas del Explorador paradas en esas carpetas.
REM  Despues borra las carpetas. NO toca el stock ni ningun otro proyecto.
REM ===========================================================================
title Limpiar carpetas viejas de TIZADA PRO
set "PS1=%TEMP%\limpiar_tizada.ps1"

> "%PS1%" echo $ErrorActionPreference = 'SilentlyContinue'
>> "%PS1%" echo $pats = '*TIZADA PRO - ACTUALIZAR SERVIDOR*','*TIZADA PRO - COPIAR AL SERVIDOR*','*INSTALAR-TIZADAPRO*'
>> "%PS1%" echo # 1) proteger al sistema: el proceso que atiende el 8050 y toda su cadena de padres
>> "%PS1%" echo $protect = @($PID)
>> "%PS1%" echo $own = (Get-NetTCPConnection -LocalPort 8050 -State Listen ^| Select-Object -First 1).OwningProcess
>> "%PS1%" echo $p = $own
>> "%PS1%" echo for ($i=0; $i -lt 5 -and $p; $i++) { $protect += $p; $p = (Get-CimInstance Win32_Process -Filter "ProcessId=$p").ParentProcessId }
>> "%PS1%" echo Write-Output ("  sistema protegido (pid {0} y su cadena)" -f $own)
>> "%PS1%" echo # 2) cerrar ventanas del Explorador paradas en las carpetas viejas
>> "%PS1%" echo $sh = New-Object -Com Shell.Application
>> "%PS1%" echo foreach ($w in @($sh.Windows())) { foreach ($pt in $pats) { if ($w.LocationURL -like $pt.Replace(' ','%%20')) { Write-Output ("  cerrando ventana del Explorador: " + $w.LocationName); $w.Quit() } } }
>> "%PS1%" echo # 3) cerrar procesos colgados: por carpeta en la linea de comando, o pythons sueltos
>> "%PS1%" echo #    de TIZADA PRO que NO son el sistema (el del 8050 ya esta protegido)
>> "%PS1%" echo Get-CimInstance Win32_Process ^| ForEach-Object {
>> "%PS1%" echo   $cl = $_.CommandLine; if (-not $cl) { return }
>> "%PS1%" echo   if ($protect -contains $_.ProcessId) { return }
>> "%PS1%" echo   $hit = $false
>> "%PS1%" echo   foreach ($pt in $pats) { if ($cl -like $pt) { $hit = $true } }
>> "%PS1%" echo   if (-not $hit -and $_.Name -match '^(py^|python^|pythonw)\.exe$' -and $cl -notlike '*multiprocessing*' -and ($cl -like '*servidor.py*' -or $cl -like '*instalar_servidor*' -or $cl -like '*actualizador.py*')) { $hit = $true }
>> "%PS1%" echo   if ($hit) { Write-Output ("  cerrando: {0} (pid {1})" -f $_.Name, $_.ProcessId); Stop-Process -Id $_.ProcessId -Force }
>> "%PS1%" echo }
>> "%PS1%" echo Start-Sleep 2
>> "%PS1%" echo # 4) borrar las carpetas viejas
>> "%PS1%" echo foreach ($base in @("$env:USERPROFILE\Documents", "$env:USERPROFILE\Desktop")) {
>> "%PS1%" echo   foreach ($n in @('TIZADA PRO - ACTUALIZAR SERVIDOR','TIZADA PRO - COPIAR AL SERVIDOR','INSTALAR-TIZADAPRO')) {
>> "%PS1%" echo     $d = Join-Path $base $n
>> "%PS1%" echo     if (Test-Path $d) {
>> "%PS1%" echo       Remove-Item -Recurse -Force $d
>> "%PS1%" echo       if (Test-Path $d) { Write-Output ("  NO SE PUDO: " + $d) } else { Write-Output ("  BORRADA: " + $d) }
>> "%PS1%" echo     }
>> "%PS1%" echo   }
>> "%PS1%" echo }
>> "%PS1%" echo # 5) el sistema tiene que seguir andando
>> "%PS1%" echo try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8050/api/salud' -UseBasicParsing -TimeoutSec 20
>> "%PS1%" echo   if ($r.Content -match '"ok":\s*true') { Write-Output '  OK: TIZADA PRO sigue andando en C:\TIZADAPRO' }
>> "%PS1%" echo   else { Write-Output '  [!] el sistema respondio con fallas' } } catch { Write-Output '  [!] el sistema no respondio' }

echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
del "%PS1%" >nul 2>&1
echo.
echo  Listo. C:\TIZADAPRO no se toco. Este archivo tambien se puede borrar.
echo.
pause
