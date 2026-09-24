# -*- coding: utf-8 -*-
"""
EL MONITOR: QUÉ ESTÁ HACIENDO EL SERVIDOR Y CUÁNTO LE CUESTA — `servidor.py` lo expone en `GET /api/monitor`.

Pedido del usuario (2026-09-18): «algo para controlar y ver qué se está ejecutando en el servidor,
qué en el navegador, cuánta memoria, cuánta RAM, cuánto procesador». Acá va la parte del servidor:
  · `muestra()`   — CPU (del proceso y de la máquina), RAM (total, libre, la del proceso), hilos.
                    Sin psutil: en Windows con `ctypes` (GetProcessTimes, GetSystemTimes,
                    GetProcessMemoryInfo), en Linux con /proc.
  · `anotar()`    — un evento de trabajo: QUIÉN lo hizo (navegador / servidor), qué, cuánto tardó.
                    Queda en una cola en memoria (los últimos 300): es lo que la pantalla lista.
  · `eventos()`   — esa cola, del más nuevo al más viejo.
Todo es best-effort: si una medida no se puede tomar, va None; nunca frena nada.
"""
import collections
import os
import threading
import time

_EVENTOS = collections.deque(maxlen=300)
_LOCK = threading.Lock()
_ULTIMA = {"t": None, "proc": None, "sis": None}      # la muestra anterior, para el % de CPU
_ARRANQUE = time.time()


def anotar(quien, que, detalle="", seg=None, **extra):
    """`quien` = 'navegador' | 'servidor'. `que` = 'molde', 'arte', 'previa', 'tizada', 'vista'…"""
    with _LOCK:
        _EVENTOS.appendleft({"t": time.time(), "quien": str(quien), "que": str(que), "detalle": str(detalle or "")[:200],
                             "seg": (round(float(seg), 1) if seg is not None else None), **extra})


def eventos(n=60):
    with _LOCK:
        return list(_EVENTOS)[:n]


def _cpu_proceso_seg():
    """Segundos de CPU (usuario + sistema) que lleva consumidos ESTE proceso."""
    try:
        t = os.times()
        return t.user + t.system
    except Exception:
        return None


def _cpu_sistema_seg():
    """(ocupado, total) en segundos de CPU de TODA la máquina, sumando núcleos."""
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class FT(ctypes.Structure):
                _fields_ = [("lo", wintypes.DWORD), ("hi", wintypes.DWORD)]

            idle, kern, user = FT(), FT(), FT()
            k32 = ctypes.windll.kernel32
            k32.GetSystemTimes.restype = ctypes.c_int
            if not k32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(user)):
                return None
            f = lambda x: ((x.hi << 32) | x.lo) / 1e7          # noqa: E731 — 100 ns → s
            total = f(kern) + f(user)                          # kernel incluye idle
            return (total - f(idle), total)
        with open("/proc/stat", encoding="ascii") as fh:
            campos = [float(x) for x in fh.readline().split()[1:8]]
        idle = campos[3] + campos[4]
        total = sum(campos)
        return ((total - idle) / os.sysconf("SC_CLK_TCK"), total / os.sysconf("SC_CLK_TCK"))
    except Exception:
        return None


def _memoria_proceso_mb():
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class PMC(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

            pmc = PMC()
            pmc.cb = ctypes.sizeof(PMC)
            k32 = ctypes.windll.kernel32
            fn = getattr(k32, "K32GetProcessMemoryInfo", None) or ctypes.windll.psapi.GetProcessMemoryInfo
            fn.restype = ctypes.c_int
            fn.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
            k32.GetCurrentProcess.restype = wintypes.HANDLE
            if not fn(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
                return None
            return round(pmc.WorkingSetSize / (1024 * 1024))
        with open("/proc/self/status", encoding="ascii") as fh:
            for ln in fh:
                if ln.startswith("VmRSS:"):
                    return round(float(ln.split()[1]) / 1024)
    except Exception:
        return None
    return None


def _memoria_total_mb():
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
            return round(m.ullTotalPhys / (1024 * 1024))
        with open("/proc/meminfo", encoding="ascii", errors="replace") as fh:
            for ln in fh:
                if ln.startswith("MemTotal:"):
                    return round(float(ln.split()[1]) / 1024)
    except Exception:
        return None
    return None


# ── LO QUE CONSUME TIZADA ENTERA EN EL SERVIDOR (pedido del usuario 2026-09-24: «que me muestre lo
# que consume el sistema real, no la máquina completa») ─────────────────────────────────────────
# TIZADA no es un solo proceso: el trabajo pesado corre en procesos HIJOS (los pools, `procesos.py`).
# Medir sólo este proceso daba 35 MB aunque un pool estuviera usando gigas. Acá se suman el proceso
# y TODOS sus descendientes: memoria (RSS / working set) y segundos de CPU.

def _hijos_linux(raiz):
    """[(pid, mb, seg_cpu)] de los descendientes de `raiz`, leyendo /proc."""
    tick = os.sysconf("SC_CLK_TCK")
    padre = {}
    for p in os.listdir("/proc"):
        if not p.isdigit():
            continue
        try:
            with open(f"/proc/{p}/stat", "rb") as fh:
                s = fh.read().decode("ascii", "replace")
            resto = s[s.rindex(")") + 2:].split()      # el nombre puede traer espacios y paréntesis
            padre[int(p)] = (int(resto[1]), (int(resto[11]) + int(resto[12])) / tick)
        except Exception:
            continue
    desc, frontera = set(), [raiz]
    while frontera:
        x = frontera.pop()
        for p, (pp, _) in padre.items():
            if pp == x and p not in desc:
                desc.add(p)
                frontera.append(p)
    out = []
    for p in desc:
        mb = None
        try:
            with open(f"/proc/{p}/status", encoding="ascii", errors="replace") as fh:
                for ln in fh:
                    if ln.startswith("VmRSS:"):
                        mb = float(ln.split()[1]) / 1024
                        break
        except Exception:
            pass
        out.append((p, mb, padre[p][1]))
    return out


def _hijos_windows(raiz):
    """[(pid, mb, seg_cpu)] de los descendientes de `raiz` (Toolhelp32 + GetProcessTimes)."""
    import ctypes
    from ctypes import wintypes

    class PE32(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                    ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_char * 260)]

    class FT(ctypes.Structure):
        _fields_ = [("lo", wintypes.DWORD), ("hi", wintypes.DWORD)]

    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

    k32 = ctypes.windll.kernel32
    # tipos explícitos: sin ellos ctypes pasa los handles como int de 32 bits
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.Process32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(PE32)]
    k32.Process32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(PE32)]
    k32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(FT)] * 4
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    mem_info = getattr(k32, "K32GetProcessMemoryInfo", None) or ctypes.windll.psapi.GetProcessMemoryInfo
    mem_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
    f = lambda x: ((x.hi << 32) | x.lo)                  # noqa: E731

    def tiempos(h):
        c, e, k, u = FT(), FT(), FT(), FT()
        if not k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(k), ctypes.byref(u)):
            return None, None
        return f(c), (f(k) + f(u)) / 1e7                # (creación en 100 ns, segundos de CPU)

    snap = k32.CreateToolhelp32Snapshot(0x2, 0)          # TH32CS_SNAPPROCESS
    if not snap or snap == wintypes.HANDLE(-1).value:
        return []
    padre = {}
    try:
        pe = PE32()
        pe.dwSize = ctypes.sizeof(PE32)
        ok = k32.Process32First(snap, ctypes.byref(pe))
        while ok:
            padre[pe.th32ProcessID] = pe.th32ParentProcessID
            ok = k32.Process32Next(snap, ctypes.byref(pe))
    finally:
        k32.CloseHandle(snap)
    # un pid «padre» puede ser de un proceso ya muerto cuyo número se reusó: se exige que el hijo
    # haya nacido después que TIZADA
    creado_raiz, _ = tiempos(k32.GetCurrentProcess())
    desc, frontera = set(), [raiz]
    while frontera:
        x = frontera.pop()
        for p, pp in padre.items():
            if pp == x and p not in desc and p != x:
                desc.add(p)
                frontera.append(p)
    out = []
    for p in desc:
        h = k32.OpenProcess(0x1000 | 0x0010, False, p)    # QUERY_LIMITED_INFORMATION | VM_READ
        if not h:
            continue
        try:
            creado, seg = tiempos(h)
            if creado_raiz and creado and creado < creado_raiz:
                continue
            pmc = PMC()
            pmc.cb = ctypes.sizeof(PMC)
            mb = pmc.WorkingSetSize / (1024 * 1024) if mem_info(h, ctypes.byref(pmc), pmc.cb) else None
            out.append((p, mb, seg))
        finally:
            k32.CloseHandle(h)
    return out


_HIJOS_ANT = {}                                          # pid → segundos de CPU en la muestra anterior

# ── LO QUE OCUPA TIZADA EN EL DISCO DEL SERVIDOR (pedido del usuario 2026-09-24: «cuánta RAM, memoria y
# procesador me usa TIZADA») ─ recorrer gigas de archivos tarda: se mide en un hilo aparte cada 10
# minutos y la pantalla muestra la última medida (con su hora). Se saltean `.git`, `node_modules` y
# `__pycache__` (no son del sistema en marcha). ────────────────────────────────────────────────
_DISCO = {"t": 0.0, "midiendo": False, "total_mb": None, "partes": {}}
_DISCO_CADA = 600
_NO_CONTAR = {".git", "node_modules", "__pycache__"}


def _tam_carpeta(raiz):
    total = 0
    for base, dirs, archivos in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in _NO_CONTAR]
        for a in archivos:
            try:
                total += os.path.getsize(os.path.join(base, a))
            except OSError:
                pass
    return total


def disco(carpetas):
    """`carpetas` = {nombre: ruta}; «todo» = la carpeta de TIZADA entera. Devuelve la última medida
    y, si es vieja, arranca otra en un hilo aparte (nunca frena al que pregunta)."""
    with _LOCK:
        viejo = time.time() - _DISCO["t"] > _DISCO_CADA
        arrancar = viejo and not _DISCO["midiendo"]
        if arrancar:
            _DISCO["midiendo"] = True
        foto = {"total_mb": _DISCO["total_mb"], "partes": dict(_DISCO["partes"]),
                "medido": _DISCO["t"] or None, "midiendo": _DISCO["midiendo"]}

    def medir():
        try:
            partes = {}
            for nombre, ruta in (carpetas or {}).items():
                if ruta and os.path.isdir(ruta):
                    partes[nombre] = round(_tam_carpeta(ruta) / 1048576)
            with _LOCK:
                _DISCO["total_mb"] = partes.pop("todo", None)
                _DISCO["partes"] = partes
                _DISCO["t"] = time.time()
        finally:
            with _LOCK:
                _DISCO["midiendo"] = False

    if arrancar:
        threading.Thread(target=medir, name="monitor-disco", daemon=True).start()
    return foto


def _tizada_entera(proc_mb, proc_seg, t0, ahora):
    """(mb, % de CPU de la máquina, cuántos procesos) de TIZADA con sus hijos. None si no se puede."""
    try:
        hijos = _hijos_windows(os.getpid()) if os.name == "nt" else _hijos_linux(os.getpid())
    except Exception:
        return None, None, None
    mb = (proc_mb or 0) + sum(h[1] or 0 for h in hijos)
    cpu = None
    n = os.cpu_count() or 1
    with _LOCK:
        ant = dict(_HIJOS_ANT)
        _HIJOS_ANT.clear()
        _HIJOS_ANT.update({p: s for p, _, s in hijos if s is not None})
    if t0 and ahora - t0 > 0.2 and proc_seg is not None:
        # un hijo que no estaba en la muestra anterior no suma (no se sabe desde cuándo corre)
        delta = sum(max(0.0, s - ant[p]) for p, _, s in hijos if s is not None and p in ant)
        cpu = round(100.0 * (proc_seg + delta) / (ahora - t0) / n, 1)
    return round(mb), cpu, 1 + len(hijos)


def muestra():
    """La foto de ahora: CPU % (proceso y máquina, medidos contra la muestra anterior), RAM."""
    import procesos as _PR
    ahora = time.time()
    proc, sis = _cpu_proceso_seg(), _cpu_sistema_seg()
    cpu_proc = cpu_sis = None
    with _LOCK:
        t0, p0, s0 = _ULTIMA["t"], _ULTIMA["proc"], _ULTIMA["sis"]
        _ULTIMA.update(t=ahora, proc=proc, sis=sis)
    n = os.cpu_count() or 1
    if t0 and ahora - t0 > 0.2:
        if proc is not None and p0 is not None:
            cpu_proc = round(100.0 * (proc - p0) / (ahora - t0) / n, 1)
        if sis and s0 and sis[1] > s0[1]:
            cpu_sis = round(100.0 * (sis[0] - s0[0]) / (sis[1] - s0[1]), 1)
    libre = _PR.memoria_libre_mb()
    mem_proc = _memoria_proceso_mb()
    proc_delta = (proc - p0) if (proc is not None and p0 is not None) else None
    tz_mb, tz_cpu, tz_n = _tizada_entera(mem_proc, proc_delta, t0, ahora)
    return {
        "hora": ahora, "arranque": _ARRANQUE, "nucleos": n,
        "cpu_proceso_pct": cpu_proc, "cpu_maquina_pct": cpu_sis,
        "ram_total_mb": _memoria_total_mb(), "ram_libre_mb": (round(libre) if libre else None),
        "proceso_mb": mem_proc, "hilos": threading.active_count(),
        # TIZADA ENTERA: el proceso + sus procesos de trabajo (lo que de verdad gasta el sistema)
        "tizada_mb": tz_mb, "tizada_cpu_pct": tz_cpu, "tizada_procesos": tz_n,
        "cupo_procesos": _PR.cupo_total(), "cupo_usado": _PR.cupo_usado(),
    }
