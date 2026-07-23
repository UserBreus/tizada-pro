@echo off
REM ===========================================================================
REM   TIZADA PRO - DIAGNOSTICO
REM   Doble clic. Averigua en que estado quedo la instalacion, guarda todo en
REM   DIAGNOSTICO.txt y lo abre en el Bloc de notas para copiar y pegar.
REM   No instala ni cambia NADA: solo mira.
REM ===========================================================================
title Diagnostico TIZADA PRO
cd /d "%~dp0"
set "R=%~dp0DIAGNOSTICO.txt"

echo Revisando... (10 segundos)

> "%R%" echo ===== DIAGNOSTICO TIZADA PRO =====
>> "%R%" echo fecha: %date% %time%
>> "%R%" echo carpeta: %~dp0
>> "%R%" echo.

>> "%R%" echo --- 1. WINDOWS ---
>> "%R%" ver
for /f "skip=1 tokens=*" %%m in ('wmic OS get FreePhysicalMemory 2^>nul') do (
   if not "%%m"=="" ( >> "%R%" echo memoria libre ^(KB^): %%m & goto :memlisto )
)
:memlisto
>> "%R%" echo.

>> "%R%" echo --- 2. PYTHON ---
where py >> "%R%" 2>&1
where python >> "%R%" 2>&1
py -V >> "%R%" 2>&1
python -V >> "%R%" 2>&1
>> "%R%" echo.

>> "%R%" echo --- 3. ARCHIVOS EN ESTA CARPETA ---
if exist "servidor.py"            (>> "%R%" echo [SI] servidor.py)            else (>> "%R%" echo [NO] servidor.py  ^<== el zip no se descomprimio aca)
if exist "instalar_servidor.py"   (>> "%R%" echo [SI] instalar_servidor.py)   else (>> "%R%" echo [NO] instalar_servidor.py)
if exist "INSTALAR.bat"           (>> "%R%" echo [SI] INSTALAR.bat)           else (>> "%R%" echo [NO] INSTALAR.bat)
if exist "frontend\dist\index.html" (>> "%R%" echo [SI] frontend compilado)   else (>> "%R%" echo [NO] frontend compilado)
if exist "datos"                  (>> "%R%" echo [SI] datos\)                 else (>> "%R%" echo [NO] datos\)
if exist "config_publicado.bat"   (>> "%R%" echo [SI] config_publicado.bat  ^<== el instalador SI llego a configurar) else (>> "%R%" echo [NO] config_publicado.bat  ^<== el instalador NO llego a configurar)
if exist "arrancar.bat"           (>> "%R%" echo [SI] arrancar.bat)           else (>> "%R%" echo [NO] arrancar.bat)
>> "%R%" echo.

>> "%R%" echo --- 4. ESTA CORRIENDO? ---
netstat -ano | findstr ":8050" >> "%R%" 2>&1
if errorlevel 1 (>> "%R%" echo nada escuchando en el puerto 8050)
tasklist /fi "imagename eq python.exe" 2>nul | findstr /i python >> "%R%" 2>&1
if errorlevel 1 (>> "%R%" echo no hay ningun python.exe corriendo)
>> "%R%" echo.

>> "%R%" echo --- 5. ARRANQUE AUTOMATICO ---
schtasks /query /tn "TIZADA PRO" >> "%R%" 2>&1
>> "%R%" echo.

>> "%R%" echo --- 6. NGINX ---
tasklist /fi "imagename eq nginx.exe" 2>nul | findstr /i nginx >> "%R%" 2>&1
if errorlevel 1 (>> "%R%" echo nginx no aparece corriendo)
if exist "C:\nginx\conf\nginx.conf" (>> "%R%" echo [SI] C:\nginx\conf\nginx.conf)
if exist "C:\Program Files\nginx\conf\nginx.conf" (>> "%R%" echo [SI] C:\Program Files\nginx\conf\nginx.conf)
>> "%R%" echo.

>> "%R%" echo --- 7. REGISTRO DE LA INSTALACION ---
if exist "instalacion_log.txt" (
   >> "%R%" echo ---------- instalacion_log.txt ----------
   type "instalacion_log.txt" >> "%R%" 2>&1
   >> "%R%" echo ---------- fin del log ----------
) else (
   >> "%R%" echo NO existe instalacion_log.txt  ^<== el instalador nunca llego a arrancar
)
>> "%R%" echo.
>> "%R%" echo ===== FIN =====

echo.
echo  Listo. Se abre el Bloc de notas con el resultado.
echo  Selecciona todo (Ctrl+E), copia (Ctrl+C) y pegalo en el chat.
echo.
start notepad "%R%"
timeout /t 3 >nul
