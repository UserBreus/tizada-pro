# ══════════════════════════════════════════════════════════════════════════════
#  Registra la tarea de Windows «TIZADA PRO».
#
#  POR QUÉ EXISTE: un servidor arrancado desde una consola (o desde cualquier
#  programa) es HIJO de esa consola. Cuando el programa que lo lanzó se cierra,
#  Windows se lleva puesto todo el árbol — sin error, sin traza, sin nada. Eso
#  es exactamente lo que venía pasando: el log cortaba en seco.
#
#  La tarea la ejecuta el Programador de tareas de Windows, así que el servidor
#  NO cuelga de nadie. Además:
#    · arranca solo al iniciar sesión,
#    · un VIGILANTE lo vuelve a levantar en segundos si se cierra,
#    · no tiene límite de tiempo (si no, Windows lo mata a los 3 días),
#    · no deja ninguna ventana que se pueda cerrar sin querer.
#
#  Es la MISMA protección que instalar_servidor.py le pone al servidor
#  publicado; acá se la ponemos también al del taller.
# ══════════════════════════════════════════════════════════════════════════════
$ErrorActionPreference = 'Stop'
$TAREA   = 'TIZADA PRO'
$carpeta = Split-Path -Parent $MyInvocation.MyCommand.Path
$arranque = Join-Path $carpeta '_vigilante.vbs'
$usuario = "$env:USERDOMAIN\$env:USERNAME"

if (-not (Test-Path $arranque)) { Write-Host "  FALTA $arranque" -ForegroundColor Red; exit 1 }

# InteractiveToken = corre como vos, sin guardar ninguna contraseña, cuando hay
# sesión iniciada (que es el caso del taller). El servidor conserva tus permisos
# de Windows, que es lo que la base MSSQL usa para dejarlo entrar.
$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>TIZADA PRO - servidor del taller (arranca solo y se levanta si se cae)</Description></RegistrationInfo>
  <Triggers>
    <LogonTrigger><Enabled>true</Enabled><UserId>$usuario</UserId></LogonTrigger>
    <TimeTrigger>
      <StartBoundary>2020-01-01T00:00:00</StartBoundary><Enabled>true</Enabled>
      <Repetition><Interval>PT1M</Interval><StopAtDurationEnd>false</StopAtDurationEnd></Repetition>
    </TimeTrigger>
  </Triggers>
  <Principals><Principal id="Author">
    <UserId>$usuario</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel>
  </Principal></Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Hidden>true</Hidden><Enabled>true</Enabled>
    <IdleSettings><StopOnIdleEnd>false</StopOnIdleEnd><RestartOnIdle>false</RestartOnIdle></IdleSettings>
    <RestartOnFailure><Interval>PT1M</Interval><Count>99</Count></RestartOnFailure>
  </Settings>
  <Actions Context="Author"><Exec>
    <Command>wscript.exe</Command>
    <Arguments>//B //Nologo "$arranque"</Arguments>
    <WorkingDirectory>$carpeta</WorkingDirectory>
  </Exec></Actions>
</Task>
"@

# schtasks SOLO lee XML en UTF-16; con UTF-8 falla con un error que no dice nada.
$tmp = Join-Path $env:TEMP '_tizada_tarea.xml'
[System.IO.File]::WriteAllText($tmp, $xml, [System.Text.Encoding]::Unicode)

# OJO: nada de `2>&1` sobre schtasks. En Windows PowerShell 5.1 eso convierte cada linea de
# error en una excepcion y, con ErrorActionPreference=Stop, el script muere en el /delete —
# que FALLA A PROPOSITO la primera vez (la tarea todavia no existe). Ya paso.
$ErrorActionPreference = 'Continue'
schtasks /delete /tn "$TAREA" /f | Out-Null
$r = schtasks /create /tn "$TAREA" /xml "$tmp" /f
$creada = ($LASTEXITCODE -eq 0)
Remove-Item $tmp -Force -ErrorAction SilentlyContinue

if (-not $creada) {
    Write-Host ""
    Write-Host "  NO se pudo crear la tarea:" -ForegroundColor Red
    Write-Host "  $r"
    exit 1
}
Write-Host "  Listo: el sistema ya no depende de ninguna ventana." -ForegroundColor Green

# Arrancarlo ya, y comprobar que de verdad levantó.
Remove-Item (Join-Path $carpeta 'logs\apagado.flag') -Force -ErrorAction SilentlyContinue
schtasks /run /tn "$TAREA" | Out-Null
Write-Host "  Levantando el servidor..."
$ok = $false
foreach ($i in 1..30) {
    Start-Sleep -Seconds 2
    try {
        if ((Invoke-WebRequest 'http://127.0.0.1:8050/api/salud' -UseBasicParsing -TimeoutSec 4).StatusCode -eq 200) { $ok = $true; break }
    } catch { }
}
if ($ok) {
    Write-Host ""
    Write-Host "  TIZADA PRO esta funcionando en  http://localhost:8050" -ForegroundColor Green
    Write-Host "  Arranca solo al prender la maquina y, si se cayera, vuelve solo en 2 minutos."
} else {
    Write-Host ""
    Write-Host "  La tarea quedo creada pero el servidor no contesto." -ForegroundColor Yellow
    Write-Host "  Mira que paso en:  logs\servidor.log"
    exit 1
}
