# -*- coding: utf-8 -*-
"""Que los procesos hijos NO sobrevivan al que los lanzó.

🔴 POR QUÉ ESTÁ ACÁ Y NO SÓLO EN EL SERVIDOR (2026-09-15). Windows no mata a los hijos cuando
muere el padre. El servidor ya se ataba con un Job Object desde que 86 procesos sueltos (4,8 GB)
dejaron la máquina del usuario a medio andar — pero **las herramientas del repo no**: al cortar
una corrida de contratos quedaron **18 procesos huérfanos con 8,8 GB**, justo mientras el usuario
trabajaba. Cualquier cosa que lance procesos usa esto y el problema no puede volver.

`atar_hijos()` mete al proceso actual en un Job Object con KILL_ON_JOB_CLOSE: todo lo que cree a
partir de ahí lo hereda, y cuando el padre se va —aunque lo maten— Windows se lleva a los hijos.
BREAKAWAY_OK deja que un hijo se salga si lo PIDE (lo necesita el ayudante de actualización).

`huerfanos()` lista los procesos de Python cuyo padre ya no existe: sirve para decirlo en pantalla
en vez de que se acumulen en silencio.
"""
import os

_JOB = None


def atar_hijos():
    """Que los procesos de dibujo NO sobrevivan al servidor.

    Windows no mata a los hijos cuando muere el padre: al reiniciar el servidor quedaban 6
    procesos de dibujo sueltos ocupando ~1 GB, y se iban acumulando con cada reinicio hasta
    dejar la máquina a medio andar (pasó: 86 procesos, 4,8 GB, y todo tardaba el doble).
    La forma que da Windows para esto es un JOB OBJECT con `KILL_ON_JOB_CLOSE`: se mete a
    ESTE proceso adentro y **todos los que cree lo heredan**, así que cuando el servidor se
    apaga —o lo matan— el sistema se lleva a sus hijos con él.

    Si algo falla (Windows viejo, permisos), se sigue como siempre: no rompe nada."""
    global _JOB
    if os.name != "nt":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        class _LIMITES(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
                        ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
                        ("LimitFlags", wintypes.DWORD),
                        ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t),
                        ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.POINTER(ctypes.c_ulong)),
                        ("PriorityClass", wintypes.DWORD),
                        ("SchedulingClass", wintypes.DWORD)]

        class _IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_ulonglong) for n in
                        ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                         "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

        class _EXT(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", _LIMITES), ("IoInfo", _IO),
                        ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                        ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        # Declarar los tipos es OBLIGATORIO: sin esto ctypes asume enteros de 32 bits y en
        # Windows de 64 el HANDLE se trunca → todo falla en silencio (comprobado: el hijo
        # sobrevivía igual). Con los tipos puestos, el hijo muere con el padre.
        k32.CreateJobObjectW.restype = wintypes.HANDLE
        k32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
        k32.SetInformationJobObject.restype = wintypes.BOOL
        k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                                wintypes.LPVOID, wintypes.DWORD]
        k32.AssignProcessToJobObject.restype = wintypes.BOOL
        k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        job = k32.CreateJobObjectW(None, None)
        if not job:
            return False
        info = _EXT()
        # KILL_ON_JOB_CLOSE: los hijos se mueren con el servidor (eso es lo que evita los procesos
        # sueltos). BREAKAWAY_OK: **el AYUDANTE de actualización tiene que poder salirse**. Sin
        # este segundo flag, `actualizador.py` —que se lanza justo antes del `os._exit(0)` para
        # reemplazar los archivos— quedaba adentro del Job y Windows se lo llevaba puesto en el
        # mismo instante: la actualización quedaba a medias y el servidor no volvía ni con la
        # versión nueva ni con la vieja. Salirse hay que PEDIRLO (CREATE_BREAKAWAY_FROM_JOB): esto
        # sólo lo habilita, no lo aplica a nadie más.
        info.BasicLimitInformation.LimitFlags = 0x2000 | 0x0800   # KILL_ON_JOB_CLOSE | BREAKAWAY_OK
        if not k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
            return False
        if not k32.AssignProcessToJobObject(job, k32.GetCurrentProcess()):
            return False
        _JOB = job       # ¡NO cerrar este handle! Cerrarlo mataría a todo el grupo.
        return True
    except Exception:
        return False

    except Exception:
        return False


def huerfanos():
    """[(pid, MB, linea_de_comando)] de los procesos Python cuyo padre ya no existe."""
    if os.name != "nt":
        return []
    import subprocess
    ps = ("Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,"
          "WorkingSetSize,CommandLine | ConvertTo-Json -Compress")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, timeout=30).stdout
        import json
        todos = json.loads(out or "[]")
    except Exception:
        return []
    vivos = {p.get("ProcessId") for p in todos}
    fuera = []
    for p in todos:
        n = (p.get("Name") or "").lower()
        if not (n.startswith("py") or n == "python.exe"):
            continue
        if p.get("ParentProcessId") in vivos:
            continue
        fuera.append((p.get("ProcessId"), (p.get("WorkingSetSize") or 0) / 1048576,
                      (p.get("CommandLine") or "")[:80]))
    return fuera
