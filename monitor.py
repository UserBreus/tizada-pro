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
    return {
        "hora": ahora, "arranque": _ARRANQUE, "nucleos": n,
        "cpu_proceso_pct": cpu_proc, "cpu_maquina_pct": cpu_sis,
        "ram_total_mb": _memoria_total_mb(), "ram_libre_mb": (round(libre) if libre else None),
        "proceso_mb": _memoria_proceso_mb(), "hilos": threading.active_count(),
        "cupo_procesos": _PR.cupo_total(), "cupo_usado": _PR.cupo_usado(),
    }
