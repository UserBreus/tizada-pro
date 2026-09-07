# -*- coding: utf-8 -*-
"""
CONTRATO: EL ARRANQUE NO SE MULTIPLICA — se corre con `py verificar_arranque_workers.py`.

Lo que protege (auditoría 2026-09-07, changelog 386):

  1. **Importar `servidor.py` NO toca la base.** Los workers del ProcessPool de dibujo se crean
     con `spawn`: cada uno **re-importa el módulo entero**. La sincronización de permisos vivía a
     nivel de módulo, así que hasta 6 procesos la repetían a la vez (cientos de conexiones y
     UPDATE simultáneos sobre las mismas 18 filas de `permiso`). Y `srv_visor.py` —el sandbox de
     SÓLO LECTURA— importa el mismo módulo: escribía en la base de VERDAD.

  2. **El ayudante de actualización puede salirse del grupo de procesos.** El servidor se mete en
     un Job Object de Windows con `KILL_ON_JOB_CLOSE` para no dejar procesos de dibujo sueltos.
     Los hijos heredan el Job aunque nazcan «detached», así que el `os._exit(0)` del apagado se
     llevaba puesto al `actualizador.py` a mitad de descomprimir. El Job ahora lleva
     `BREAKAWAY_OK` y el ayudante pide `CREATE_BREAKAWAY_FROM_JOB`.

⚠️ No toca nada del usuario: `DATOS` va a un temporal, el módulo `db` se reemplaza por un doble
que sólo ANOTA lo que se le pide (ver [[test-no-toca-mssql]]), y el único proceso que se mata es
el hijo que lanza esta misma prueba, por su PID.
"""
import os
import sys
import tempfile
import types

# El hijo (spawn) re-importa ESTE módulo: las carpetas se pasan por el entorno para que use las
# mismas y no se ponga a crear temporales nuevos.
if not os.environ.get("VERIF_ARRANQUE_TMP"):
    os.environ["VERIF_ARRANQUE_TMP"] = tempfile.mkdtemp(prefix="verif_arranque_")
_TMP = os.environ["VERIF_ARRANQUE_TMP"]
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = "localhost\\NO_EXISTE_ES_UNA_PRUEBA"

# ── EL DOBLE DE `db`: no hace nada, pero ANOTA cada función que le piden ──────────────────────
_PEDIDOS = []
_falso = types.ModuleType("db")


def _anotar(nombre):
    def _fn(*a, **k):
        _PEDIDOS.append(nombre)
        return None
    return _fn


_falso.__getattr__ = _anotar
_falso.get_doc = lambda c, default=None: (_PEDIDOS.append("get_doc"), default)[-1]
_falso.tablas = lambda: (_PEDIDOS.append("tablas"), [])[-1]
sys.modules["db"] = _falso

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# 🔴 El registro va al temporal ANTES de importar `servidor`: una prueba no puede ensuciar el
# registro del sistema de verdad (si no, mañana alguien investiga una falla que provocó un test).
import registro as LOG   # noqa: E402
LOG.usar_carpeta(os.path.join(_TMP, "logs"))

import servidor as S   # noqa: E402   ← ACÁ es donde antes se sincronizaban los permisos

_AL_IMPORTAR = list(_PEDIDOS)
_AQUI = os.path.dirname(os.path.abspath(__file__))


def _lo_que_pidio_el_worker(_ignorado=None):
    """Corre DENTRO de un worker del pool: devuelve qué le pidió a la base al importarse."""
    return (list(_AL_IMPORTAR), S._es_proceso_principal())


def _fuente(nombre):
    with open(os.path.join(_AQUI, nombre), encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    FALLOS = []

    def ok(cond, msg):
        if not cond:
            FALLOS.append(msg)
        print(("  OK    " if cond else "  FALLA ") + msg)

    print("1) Importar `servidor` no toca la base")
    ok(not _AL_IMPORTAR, f"al importar no se le pide NADA a la base (pidio: {_AL_IMPORTAR})")
    ok(S._es_proceso_principal() is True,
       "el proceso que arranca el servidor se reconoce como principal")

    print("\n2) Un worker del pool (spawn) tampoco")
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=1) as ex:
        pedidos_hijo, principal_hijo = ex.submit(_lo_que_pidio_el_worker, 1).result(timeout=300)
    ok(not pedidos_hijo, f"el worker no le pide NADA a la base al importar (pidio: {pedidos_hijo})")
    ok(principal_hijo is False, "el worker se reconoce a si mismo como worker, no como servidor")

    print("\n3) La sincronizacion sigue existiendo, pero solo desde el arranque real")
    _srv = _fuente("servidor.py")
    ok("_poner_base_al_dia_al_arrancar()" in _srv,
       "`__main__` llama a `_poner_base_al_dia_al_arrancar()`")
    ok(_srv.count("sincronizar_permisos()") == 1,
       "`sincronizar_permisos()` se llama en UN solo lugar (dentro de esa funcion)")
    ok(hasattr(S, "_poner_base_al_dia_al_arrancar"), "la funcion existe")
    # Sin `_USUARIOS_ON` no hace nada aunque la llamen: el sandbox lo apaga a propósito.
    _antes, S._USUARIOS_ON = S._USUARIOS_ON, False
    _PEDIDOS.clear()
    S._poner_base_al_dia_al_arrancar()
    S._USUARIOS_ON = _antes
    ok(not _PEDIDOS, "sin sistema de usuarios registrado, no toca la base")

    print("\n4) El sandbox de solo lectura ata sus procesos de dibujo")
    ok("_atar_hijos_a_este_proceso()" in _fuente("srv_visor.py"),
       "`srv_visor.py` ata los procesos de dibujo a si mismo antes de servir")

    print("\n5) El ayudante de actualizacion pide salirse del Job")
    _act = _fuente("actualizaciones.py")
    ok("0x01000000" in _act, "`actualizaciones.py` lanza el ayudante con CREATE_BREAKAWAY_FROM_JOB")
    ok("& ~0x01000000" in _act,
       "y si Windows no lo deja, reintenta sin el flag (no se queda sin actualizar)")
    ok("0x01000000" in _fuente("actualizador.py"),
       "`actualizador.py` arranca el servidor del plan B fuera de su propio grupo")

    if os.name == "nt":
        print("\n6) Windows de verdad: el Job permite salirse y el hijo se sale")
        import ctypes
        from ctypes import wintypes
        import subprocess
        atado = S._atar_hijos_a_este_proceso()
        if not atado:
            print("  (aviso: no se pudo crear el Job en esta maquina; no se puede comprobar)")
        else:
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)

            class _LIM(ctypes.Structure):
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
                _fields_ = [("BasicLimitInformation", _LIM), ("IoInfo", _IO),
                            ("ProcessMemoryLimit", ctypes.c_size_t),
                            ("JobMemoryLimit", ctypes.c_size_t),
                            ("PeakProcessMemoryUsed", ctypes.c_size_t),
                            ("PeakJobMemoryUsed", ctypes.c_size_t)]

            k32.QueryInformationJobObject.restype = wintypes.BOOL
            k32.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                                      wintypes.LPVOID, wintypes.DWORD,
                                                      wintypes.LPVOID]
            k32.IsProcessInJob.restype = wintypes.BOOL
            k32.IsProcessInJob.argtypes = [wintypes.HANDLE, wintypes.HANDLE,
                                           ctypes.POINTER(wintypes.BOOL)]
            k32.OpenProcess.restype = wintypes.HANDLE
            k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]

            info = _EXT()
            got = k32.QueryInformationJobObject(S._JOB_WIN, 9, ctypes.byref(info),
                                                ctypes.sizeof(info), None)
            flags = info.BasicLimitInformation.LimitFlags if got else 0
            ok(bool(flags & 0x2000),
               "el Job mata a los hijos cuando muere el servidor (KILL_ON_JOB_CLOSE)")
            ok(bool(flags & 0x0800), "el Job DEJA salirse al que lo pida (BREAKAWAY_OK)")

            # Un hijo real que pide salirse: no puede quedar adentro de NUESTRO Job.
            hijo = None
            try:
                hijo = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(25)"],
                                        creationflags=0x00000008 | 0x00000200 | 0x01000000,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                h = k32.OpenProcess(0x1000, False, hijo.pid)   # QUERY_LIMITED_INFORMATION
                dentro = wintypes.BOOL()
                k32.IsProcessInJob(h, S._JOB_WIN, ctypes.byref(dentro))
                ok(not dentro.value,
                   "un hijo con CREATE_BREAKAWAY_FROM_JOB queda FUERA del Job del servidor")
            except OSError as e:
                print(f"  (aviso: esta maquina no dejo lanzar el hijo de prueba: {e})")
            finally:
                if hijo is not None:
                    try:
                        hijo.kill()          # por PID, sólo el que lanzó esta prueba
                    except Exception:
                        pass

    print()
    if FALLOS:
        print(f"FALLARON {len(FALLOS)}:")
        for f in FALLOS:
            print("  -", f)
        sys.exit(1)
    print("TODO OK")
