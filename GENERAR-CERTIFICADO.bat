@echo off
REM ============================================================================
REM  CERTIFICADO HTTPS (autofirmado) para entrar por IP, sin dominio.
REM
REM  Uso:   GENERAR-CERTIFICADO.bat  [IP-PUBLICA]
REM  Ej:    GENERAR-CERTIFICADO.bat  190.64.12.34
REM
REM  Como no hay dominio, el certificado no lo puede firmar una autoridad: el
REM  navegador va a avisar "sitio no seguro" la primera vez y hay que aceptar
REM  (Avanzada -> Continuar). La conexion IGUAL viaja cifrada; lo unico que el
REM  navegador no puede es verificar QUIEN esta del otro lado.
REM
REM  Dura 10 anios. Se guarda en certificados\ (no se versiona).
REM ============================================================================
title TIZADA PRO - Certificado HTTPS
cd /d "%~dp0"
set "OPENSSL=C:\Program Files\Git\usr\bin\openssl.exe"
if not exist "%OPENSSL%" (
  echo [ERROR] No se encontro openssl. Viene con Git for Windows.
  pause & exit /b 1
)
if not exist "certificados" mkdir certificados

set "IPPUB=%~1"
set "SAN=DNS:localhost,IP:127.0.0.1,IP:192.168.0.120"
if not "%IPPUB%"=="" set "SAN=%SAN%,IP:%IPPUB%"

echo.
echo   Generando certificado para: %SAN%
echo.
"%OPENSSL%" req -x509 -newkey rsa:2048 -sha256 -days 3650 -nodes ^
  -keyout certificados\tizada.key -out certificados\tizada.crt ^
  -subj "/CN=TIZADA PRO/O=USER" -addext "subjectAltName=%SAN%" ^
  -addext "keyUsage=digitalSignature,keyEncipherment" ^
  -addext "extendedKeyUsage=serverAuth"
if errorlevel 1 (
  echo.
  echo   [ERROR] No se pudo generar el certificado.
  pause & exit /b 1
)
echo.
echo   Listo:
echo     certificados\tizada.crt
echo     certificados\tizada.key
echo.
echo   Ahora arranca el sistema con PUBLICAR-EN-INTERNET.bat
pause
