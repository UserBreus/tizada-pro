' ══════════════════════════════════════════════════════════════════════════════
'  TIZADA PRO — VIGILANTE del servidor.
'
'  Lo ejecuta la tarea de Windows «TIZADA PRO». No se corre a mano.
'
'  POR QUÉ EXISTE (dos problemas reales, 2026-08-27):
'
'   1) LA VENTANA QUE APARECÍA Y DESAPARECÍA. La tarea ejecutaba `cmd.exe`
'      directamente y, al correr como el usuario con sesión iniciada, Windows le
'      abría una consola. `<Hidden>` en la tarea NO la tapa: sólo la esconde de la
'      lista del Programador. Lanzándolo desde acá con `sh.Run(..., 0, ...)` no
'      aparece ninguna ventana, nunca.
'
'   2) LOS 2 MINUTOS SIN SISTEMA. Antes la tarea sólo revisaba cada 2 minutos: si
'      el servidor se cerraba, faltaba hasta 2 minutos. Ahora este vigilante se
'      queda ESPERANDO al servidor y, apenas termina, lo vuelve a levantar en
'      segundos. La revisión cada 2 minutos queda como red de seguridad por si
'      este vigilante también se cayera.
'
'  Se apaga de verdad con CERRAR-SERVIDOR.bat (deja logs\apagado.flag).
' ══════════════════════════════════════════════════════════════════════════════
Option Explicit

Const ESPERA_ENTRE_INTENTOS = 1500   ' ms antes de volver a levantarlo
Const ARRANQUE_SANO_SEG     = 20     ' si dura menos, cuenta como intento fallido
Const FALLOS_SEGUIDOS_MAX   = 5      ' tras esto se rinde y espera a la tarea
Const BANDERA_MINUTOS       = 15     ' una bandera olvidada no deja el sistema muerto

Dim sh, fso, carpeta, logs, bandera, caidas
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

carpeta = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = carpeta
logs = fso.BuildPath(carpeta, "logs")
If Not fso.FolderExists(logs) Then fso.CreateFolder(logs)
bandera = fso.BuildPath(logs, "apagado.flag")
caidas  = fso.BuildPath(logs, "caidas.log")

' ── ¿lo apagaron a propósito? ────────────────────────────────────────────────
Function ApagadoAProposito()
    ApagadoAProposito = False
    If Not fso.FileExists(bandera) Then Exit Function
    ' una bandera vieja se descarta sola: si algo la dejó colgada, el sistema vuelve igual
    If DateDiff("n", fso.GetFile(bandera).DateLastModified, Now) > BANDERA_MINUTOS Then
        On Error Resume Next
        fso.DeleteFile bandera, True
        On Error GoTo 0
        Exit Function
    End If
    ApagadoAProposito = True
End Function

' ── ¿ya hay un servidor atendiendo? ──────────────────────────────────────────
Function Contesta()
    Dim http
    Contesta = False
    On Error Resume Next
    Set http = CreateObject("MSXML2.XMLHTTP")
    http.Open "GET", "http://127.0.0.1:8050/api/salud", False
    http.Send
    If Err.Number = 0 And http.Status = 200 Then Contesta = True
    Err.Clear
    On Error GoTo 0
End Function

Sub Anotar(txt)
    Dim f
    On Error Resume Next
    Set f = fso.OpenTextFile(caidas, 8, True)   ' 8 = agregar al final
    f.WriteLine FormatDateTime(Now, 0) & "  " & txt
    f.Close
    On Error GoTo 0
End Sub

' ── si ya hay otro vigilante trabajando, este sobra ──────────────────────────
If ApagadoAProposito() Then WScript.Quit 0
If Contesta() Then WScript.Quit 0

' ── LA VIGILANCIA ────────────────────────────────────────────────────────────
Dim fallos, t0, duro, cod
fallos = 0

Do
    If ApagadoAProposito() Then Exit Do

    ' UN SOLO VIGILANTE POR SERVIDOR. Si en esta vuelta YA hay alguien atendiendo, es que otro
    ' vigilante lo levanto: este sobra y se va. Sin esto quedaban dos peleando por el puerto
    ' 8050 --el perdedor muere enseguida y su vigilante lo relanza-- y el servidor se levantaba
    ' una y otra vez (reporte del usuario 2026-09-14: se levanto 11 veces sin parar).
    ' El chequeo de arriba solo corria al ARRANCAR, y entre el kill y el relanzamiento hay una
    ' ventana en la que nadie contesta: los dos pasaban.
    If Contesta() Then
        Anotar "ya hay otro servidor atendiendo: este vigilante se retira"
        Exit Do
    End If

    ' el registro anterior se conserva: sin él no se puede investigar la caída
    On Error Resume Next
    If fso.FileExists(fso.BuildPath(logs, "servidor.log")) Then
        fso.CopyFile fso.BuildPath(logs, "servidor.log"), fso.BuildPath(logs, "servidor.anterior.log"), True
    End If
    On Error GoTo 0

    t0 = Now
    ' 0 = sin ventana · True = esperar acá hasta que el servidor termine
    cod = sh.Run("cmd /c """ & fso.BuildPath(carpeta, "_arrancar-oculto.bat") & """", 0, True)
    duro = DateDiff("s", t0, Now)

    If ApagadoAProposito() Then
        Anotar "el servidor se apago a proposito (CERRAR-SERVIDOR.bat)"
        Exit Do
    End If

    Anotar "el servidor termino (codigo " & cod & ") despues de " & duro & " s -> se vuelve a levantar"

    ' Un arranque que muere enseguida es un problema de verdad (código roto, puerto
    ' tomado, base caída): reintentar sin freno sólo quemaría la máquina. Tras varios
    ' seguidos se rinde y deja que la tarea reintente en su próxima pasada.
    If duro < ARRANQUE_SANO_SEG Then
        fallos = fallos + 1
    Else
        fallos = 0
    End If
    If fallos >= FALLOS_SEGUIDOS_MAX Then
        Anotar "NO arranca (" & fallos & " intentos seguidos fallaron): mira logs\servidor.log"
        Exit Do
    End If

    WScript.Sleep ESPERA_ENTRE_INTENTOS
Loop
