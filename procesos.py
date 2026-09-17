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
import time

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


def matar_arbol(pid):
    """Mata al proceso `pid` Y A TODOS SUS DESCENDIENTES. Devuelve True si pudo.

    🔴 POR QUÉ HACE FALTA, SI YA ESTÁ EL JOB OBJECT (2026-09-15). El Job mata a los hijos cuando
    muere EL QUE LOS ATÓ. Pero el corredor de contratos no se muere al cortar UN contrato: le
    aplica `timeout` y sigue con el siguiente. `subprocess` en ese caso mata sólo al hijo directo
    —el contrato— y el pool que ese contrato había levantado queda vivo hasta el final de la
    tanda. Medido: 13 procesos sueltos con 930 MB mientras el corredor seguía corriendo.
    Cortar un proceso que lanzó otros es cortar el ÁRBOL, no la raíz sola.

    Es un `taskkill` sobre un PID CONCRETO con `/T` (su descendencia). NO es un mass-kill: nunca
    se mata por nombre de imagen — eso está prohibido en este repo y se llevaría puesto al
    servidor del usuario."""
    if os.name != "nt":
        try:
            os.kill(pid, 9)
            return True
        except Exception:
            return False
    import subprocess
    try:
        r = subprocess.run(["taskkill", "/T", "/F", "/PID", str(int(pid))],
                           capture_output=True, timeout=20)
        return r.returncode == 0
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


# ══ CÓMO SE CREAN LOS PROCESOS DE DIBUJO ═════════════════════════════════════════════════════
# 🔴 SIEMPRE `spawn`, EN TODOS LOS SISTEMAS (2026-09-16). Ningún pool elegía cómo arrancar a sus
# hijos, y en Linux con Python 3.12 eso es `fork`: el servidor publicado (Linux, 8 hilos atendiendo
# pedidos) se copiaba a sí mismo en medio de su trabajo. Si en ese instante otro hilo tenía tomado
# un candado (el del registro, el de la base, uno interno de una biblioteca), el hijo lo heredaba
# TRABADO para siempre. Es una trampa documentada (Python 3.12 lo avisa, 3.14 cambió el default) y
# es la explicación más probable del cuelgue silencioso del 14/9 en el publicado: hilos esperando a
# hijos que nunca contestan, sin errores ni muertes por memoria en el registro.
# `spawn` arranca cada hijo limpio. Es lo que ya usa Windows desde siempre, así que el código ya
# está preparado (`_es_proceso_principal`, las funciones de worker a nivel de módulo).
# No `forkserver`: su proceso servidor importa el programa sin padre, y `servidor.py` lo tomaría
# por el principal.

def contexto():
    """El contexto de multiprocessing de TODOS los pools del sistema."""
    import multiprocessing
    return multiprocessing.get_context("spawn")


# ══ CUÁNTOS PROCESOS DE TRABAJO A LA VEZ, EN TODO EL SERVIDOR ═══════════════════════════════
# 🔴 EL CUPO ES GLOBAL (2026-09-17, por lo del 16/09 en el publicado). Cada tarea abría SU pool
# con sus propios procesos y nadie los sumaba: a las 16:53 había DOS camisetas preparándose a la
# vez, cada una con 3 procesos nuevos parseando el molde entero, en un servidor de 3 núcleos y
# poca RAM. La máquina se ahogó (hasta el SQL Server dio «Query timeout»), ninguno de los 6 terminó
# en 30 minutos, y de ahí en más el «plan B» de cada lugar hizo el trabajo ADENTRO del servidor con
# el GIL tomado hasta las 18:02 — 8 hilos trabados, 34 pedidos en cola. Las mismas mesas, de a una,
# tardan un minuto (16:52: 57 s y 72 s).
# Ahora todos los pools de trabajo (desplegado, etiquetas, páginas por talle, aplanado, SVG) toman
# lugar de UN cupo (`cupo_total`): el que no tiene lugar ESPERA a que otro termine —avisando en la
# consola— y si no lo consigue en `TIZADA_ESPERA_LUGAR_S` falla con un error claro en vez de
# sumarse al ahogo. Con lugar para algunos, arranca con menos procesos antes que esperar a todos.
# Los dos pools permanentes del servidor (render y visor) no cuentan: son fijos y viven siempre.
# `TIZADA_PROCESOS` manda si está; si no, los núcleos menos uno, acotado por la RAM libre (cada
# proceso con un molde pesado adentro pesa ~400 MB).

class SinLugar(RuntimeError):
    """No hubo procesos libres en el tiempo de espera: el servidor está ocupado con otros trabajos."""


_CUPO = {"total": None, "usado": 0, "cond": None, "quien": {}}


def _cond():
    if _CUPO["cond"] is None:
        import threading
        _CUPO["cond"] = threading.Condition()
    return _CUPO["cond"]


def memoria_libre_mb():
    """MB de RAM disponible, o None si no se puede saber."""
    try:
        if os.name == "nt":
            import ctypes

            class _MEM(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = _MEM()
            m.dwLength = ctypes.sizeof(_MEM)
            ctypes.windll.kernel32.GlobalMemoryStatusEx.restype = ctypes.c_int
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
                return None
            return m.ullAvailPhys / (1024 * 1024)
        with open("/proc/meminfo", encoding="ascii", errors="replace") as fh:
            for ln in fh:
                if ln.startswith("MemAvailable:"):
                    return float(ln.split()[1]) / 1024
    except Exception:
        return None
    return None


def _cupo_por_defecto():
    try:
        n = int(os.environ.get("TIZADA_PROCESOS") or 0)
    except ValueError:
        n = 0
    if n:
        return max(1, n)
    n = max(1, (os.cpu_count() or 2) - 1)
    libre = memoria_libre_mb()
    if libre:
        n = max(1, min(n, int(max(0.0, libre - 1024) // 400)))
    return n


def cupo_total():
    """Cuántos procesos de trabajo puede haber a la vez (se decide una vez, al primer uso)."""
    if _CUPO["total"] is None:
        _CUPO["total"] = _cupo_por_defecto()
    return _CUPO["total"]


def cupo_usado():
    return _CUPO["usado"]


def _soltar(ex):
    n, ex._lugares = getattr(ex, "_lugares", 0), 0
    if n:
        cond = _cond()
        with cond:
            _CUPO["usado"] = max(0, _CUPO["usado"] - n)
            _CUPO["quien"].pop(getattr(ex, "_que", None), None)
            cond.notify_all()


def _tomar(n, espera, que):
    """Toma `n` lugares (o menos, si hay algunos libres tras una espera corta). Devuelve cuántos."""
    total = cupo_total()
    n = max(1, min(int(n or 1), total))
    cond = _cond()
    t0 = time.time()
    avisado = False
    with cond:
        while True:
            libres = total - _CUPO["usado"]
            pasado = time.time() - t0
            if libres >= n or (libres >= 1 and pasado >= 10):
                tomo = min(n, libres)
                _CUPO["usado"] += tomo
                _CUPO["quien"][que] = tomo
                if avisado:
                    print(f"[procesos] {que}: lugar para {tomo} proceso(s) tras {pasado:.0f} s de espera")
                return tomo
            if pasado >= espera:
                ocupados = ", ".join(f"{k} ({v})" for k, v in _CUPO["quien"].items())
                raise SinLugar(f"no hubo procesos libres en {espera/60:.0f} minutos: "
                               f"{_CUPO['usado']} de {total} ocupados por {ocupados or 'otros trabajos'}")
            if not avisado:
                avisado = True
                print(f"[procesos] {que}: sin lugar ({_CUPO['usado']} de {total} procesos ocupados); espero")
            cond.wait(timeout=max(0.5, min(5.0, espera - pasado)))


def _pool_crudo(max_workers):
    from concurrent.futures import ProcessPoolExecutor

    class _PoolConLugar(ProcessPoolExecutor):
        _lugares = 0

        def shutdown(self, wait=True, *, cancel_futures=False):
            try:
                super().shutdown(wait=wait, cancel_futures=cancel_futures)
            finally:
                _soltar(self)

        def __del__(self):
            _soltar(self)

    return _PoolConLugar(max_workers=max_workers, mp_context=contexto())


def pool(max_workers, cupo=True, espera=None, que="un trabajo"):
    """Un `ProcessPoolExecutor` con el contexto correcto (ver arriba) y, con `cupo`, con lugar
    tomado del cupo global (se devuelve solo al apagar el pool: `shutdown`, `descartar`, `seguro`).
    `cupo=False` es para los pools permanentes del servidor. Levanta `SinLugar` si no hay lugar."""
    if not cupo:
        return _pool_crudo(max_workers)
    if espera is None:
        espera = tope_segundos("TIZADA_ESPERA_LUGAR_S", 900)
    n = _tomar(max_workers, espera, que)
    ex = None
    try:
        ex = _pool_crudo(n)
        ex._lugares = n
        ex._que = que
    finally:
        if ex is None:                      # no se pudo armar: el lugar vuelve al cupo
            with _cond():
                _CUPO["usado"] = max(0, _CUPO["usado"] - n)
                _CUPO["quien"].pop(que, None)
                _CUPO["cond"].notify_all()
    return ex


def tope_segundos(variable, por_defecto):
    """Cuánto se espera a un proceso antes de darlo por trabado (variable de entorno o default)."""
    try:
        return max(5.0, float(os.environ.get(variable) or por_defecto))
    except ValueError:
        return float(por_defecto)


def descartar(ex):
    """Apaga un pool SIN esperar a sus procesos: los mata.

    🔴 `shutdown(wait=True)` —lo que hace el `with`— espera a que cada hijo termine: con uno trabado,
    espera para siempre, y el hilo que atendía el pedido queda perdido. Un hijo trabado no se
    destraba solo; lo único que sirve es matarlo."""
    try:
        for p in list((getattr(ex, "_processes", None) or {}).values()):
            try:
                p.terminate()
            except Exception:
                pass
    except Exception:
        pass
    try:
        ex.shutdown(wait=False, cancel_futures=True)
    except TypeError:
        try:
            ex.shutdown(wait=False)
        except Exception:
            pass
    except Exception:
        pass


class seguro:
    """`with seguro(pool(n)) as ex:` — como el `with` de siempre, pero si adentro salta cualquier
    error (un tope de espera vencido, un hijo que murió) el pool se DESCARTA en vez de esperarlo."""

    def __init__(self, ex):
        self.ex = ex

    def __enter__(self):
        return self.ex

    def __exit__(self, tipo, valor, tb):
        if tipo is not None:
            descartar(self.ex)
            return False
        try:
            self.ex.shutdown(wait=True)
        except Exception:
            pass
        return False
