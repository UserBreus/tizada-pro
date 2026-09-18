# -*- coding: utf-8 -*-
"""
CONTRATO: EL MONITOR DICE QUÉ HIZO EL SERVIDOR, QUÉ HIZO EL NAVEGADOR Y CUÁNTO CUESTA — `py verificar_monitor.py`

Pedido del usuario (2026-09-18). `GET /api/monitor` (Configuración → Monitor) tiene que traer la
CPU y la RAM de la máquina y del proceso, los hilos y cupos, los trabajos en curso y los últimos
trabajos con QUIÉN los hizo. Acá se sube un molde preparado por el navegador (paquete `alta_a`) y
uno pelado que lee el servidor, y se exige que el monitor los liste con el rótulo correcto y su
duración. `monitor.py` se prueba también solo (CPU % contra la muestra anterior, RAM en MB).

⚠️ No toca nada del usuario: DATOS a un temporal y `db` es un doble.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_AQUI = os.path.dirname(os.path.abspath(__file__))
_TMP = tempfile.mkdtemp(prefix="verif_monitor_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"
os.environ.pop("TIZADA_SOLO_NAVEGADOR", None)

_DOCS, _TRAB, _REG = {}, {}, {}
_falso = types.ModuleType("db")
_falso.__getattr__ = lambda n: (lambda *a, **k: None)
_falso.get_doc = lambda c, default=None: _DOCS.get(c, default)
_falso.get_doc_ver = lambda c, default=None: (_DOCS.get(c, default), 0)
_falso.set_doc = lambda c, o, version_esperada=None: (_DOCS.__setitem__(c, o), 1)[-1]
_falso.guardar_catalogo = lambda cat, version_esperada=None: (_DOCS.__setitem__("catalogo", cat), 1)[-1]
_falso.registro_rev = lambda pid: (len(json.dumps(_REG[pid], default=str)) if pid in _REG else None)
_falso.leer_registro = lambda pid: _REG.get(pid)
_falso.guardar_registro = lambda pid, piezas, reg, **k: _REG.__setitem__(pid, reg)
_falso.trabajo_crear = lambda legacy_id, **k: _TRAB.__setitem__(legacy_id, {"estado": "en cola"})
_falso.trabajo_actualizar = lambda legacy_id, **k: (_TRAB.setdefault(legacy_id, {}).update(k), 1)[-1]
_falso.trabajo_leer = lambda tid: (dict(_TRAB[tid]) if tid in _TRAB else None)
_falso.trabajo_cancelado = lambda tid: False
_falso.trabajos_podar = lambda horas=6, vivos=200: 0
sys.modules["db"] = _falso
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")

sys.path.insert(0, _AQUI)
import registro as _LG                        # noqa: E402
_LG.usar_carpeta(tempfile.mkdtemp(prefix="verif_monitor_logs_"))
import monitor as MON                         # noqa: E402
import servidor as S                          # noqa: E402

S._USUARIOS_ON = False
CLI = S.app.test_client()
FALLOS = []
NODE = os.path.join(_AQUI, "frontend", "src", "motor", "pruebas", "subida_a.mjs")


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK    " if cond else "  FALLA ") + msg)


print("\n1 · LAS MEDIDAS DE LA MÁQUINA")
m0 = MON.muestra()
_t = time.time()
while time.time() - _t < 0.6:                  # un poco de CPU para que el % no sea cero
    sum(i * i for i in range(20000))
m1 = MON.muestra()
ok(m1["ram_total_mb"] and m1["ram_total_mb"] > 512, f"RAM total de la máquina: {m1['ram_total_mb']} MB")
ok(m1["ram_libre_mb"] and 0 < m1["ram_libre_mb"] <= m1["ram_total_mb"], f"RAM libre: {m1['ram_libre_mb']} MB")
ok(m1["proceso_mb"] and m1["proceso_mb"] > 10, f"RAM de este proceso: {m1['proceso_mb']} MB")
ok(m1["cpu_proceso_pct"] is not None and m1["cpu_proceso_pct"] > 0, f"CPU del proceso medida contra la muestra anterior: {m1['cpu_proceso_pct']} %")
ok(m1["cpu_maquina_pct"] is None or 0 <= m1["cpu_maquina_pct"] <= 100, f"CPU de la máquina: {m1['cpu_maquina_pct']} %")
ok(m1["nucleos"] >= 1 and m1["hilos"] >= 1 and m1["cupo_procesos"] >= 1, f"{m1['nucleos']} núcleos · {m1['hilos']} hilos · cupo {m1['cupo_procesos']}")

print("\n2 · EL MONITOR LISTA QUIÉN HIZO CADA TRABAJO")
_ORIG = os.path.join(_AQUI, "entrada", "prod_20260911_165624_1ed7", "plantilla_fuente.dxf")
if not os.path.exists(_ORIG):
    print("  (no está el DXF de prueba: se saltea)")
    sys.exit(0)
copia = os.path.join(_TMP, "molde.dxf")
shutil.copy2(_ORIG, copia)
pdf, zip_, res = (os.path.join(_TMP, x) for x in ("archivo.pdf", "paquete.zip", "resumen.json"))
r = subprocess.run(["node", NODE, copia, pdf, zip_, res], capture_output=True, text=True, encoding="utf-8", timeout=900)
ok(r.returncode == 0, "el navegador preparó el molde (Node)")


def subir(pid, archivo, nombre, paquete=None, con_diseno="0"):
    _DOCS["catalogo"] = {"activo": pid, "productos": [{"id": pid, "nombre": nombre}]}
    os.makedirs(os.path.join(_TMP, "entrada", pid), exist_ok=True)
    os.makedirs(os.path.join(_TMP, "productos", pid), exist_ok=True)
    datos = {"pid": pid, "con_diseno": con_diseno}
    fa = open(archivo, "rb"); datos["archivo"] = (fa, nombre)
    fp = open(paquete, "rb") if paquete else None
    if fp:
        datos["paquete"] = (fp, "paquete.zip")
    try:
        r = CLI.post("/api/plantilla", data=datos, content_type="multipart/form-data")
    finally:
        fa.close()
        if fp:
            fp.close()
    job = (r.get_json() or {}).get("job")
    for _ in range(3000):
        e = _TRAB.get(job) or {}
        if e.get("estado") in ("listo", "error"):
            return e
        time.sleep(0.1)
    return {"estado": "colgado"}


e1 = subir("pNav", pdf, "molde_nav.pdf", zip_)
ok(e1.get("estado") == "listo", f"un molde que llegó preparado se guardó ({e1.get('estado')} {str(e1.get('error') or '')[:80]})")
e2 = subir("pSrv", pdf, "molde_srv.pdf")
ok(e2.get("estado") == "listo", f"un molde pelado lo leyó el servidor ({e2.get('estado')} {str(e2.get('error') or '')[:80]})")
d = CLI.get("/api/monitor").get_json() or {}
ok("eventos" in d and "trabajos" in d and "ram_total_mb" in d and "navegador" in d, f"`/api/monitor` trae medidas, trabajos, eventos e interruptores ({sorted(k for k in d if k != 'eventos')[:8]}…)")
ev = d.get("eventos") or []
nav = [x for x in ev if x["quien"] == "navegador" and x["que"] == "molde" and "molde_nav" in x["detalle"]]
srv = [x for x in ev if x["quien"] == "servidor" and x["que"] == "molde" and "molde_srv" in x["detalle"]]
ok(len(nav) == 1 and nav[0]["seg"] is not None, f"el molde preparado figura como «navegador» con su duración ({nav[0]['seg'] if nav else '?'} s)")
ok(len(srv) == 1 and srv[0]["seg"] is not None, f"el molde pelado figura como «servidor» con su duración ({srv[0]['seg'] if srv else '?'} s)")
ok(ev and ev[0]["t"] >= ev[-1]["t"], "los eventos vienen del más nuevo al más viejo")
ok(d.get("trabajos") == [], "y no hay trabajos en curso (los dos terminaron)")

print(chr(10) + "3 · EL CAMINO DE LINUX (el publicado): /proc simulado")
# El servidor publicado es Linux y acá no hay Linux para correrlo: se simula lo que Linux le da al
# código (`/proc/stat`, `/proc/self/status`, `/proc/meminfo`, `sysconf`) con valores reales de un
# servidor, y se exige que las cuentas salgan bien. Si la lectura de esos archivos se rompe, esto lo ve.
import builtins
import procesos as _PR
_PROC = {
    "/proc/stat": "cpu  100000 200 50000 800000 1000 0 500 0 0 0" + chr(10) + "cpu0 1 2 3 4 5 6 7 0 0 0" + chr(10),
    "/proc/self/status": "Name:	python3" + chr(10) + "VmPeak:	 900000 kB" + chr(10) + "VmRSS:	  262144 kB" + chr(10),
    "/proc/meminfo": "MemTotal:        8000000 kB" + chr(10) + "MemFree:         1000000 kB" + chr(10) + "MemAvailable:    3000000 kB" + chr(10),
}
_open0 = builtins.open


def _open_sim(ruta, *a, **k):
    if isinstance(ruta, str) and ruta in _PROC:
        return io.StringIO(_PROC[ruta])
    return _open0(ruta, *a, **k)


_name0, _sysconf0 = MON.os.name, getattr(MON.os, "sysconf", None)
try:
    MON.os.name = "posix"
    _PR.os.name = "posix"
    MON.os.sysconf = lambda n: 100
    builtins.open = _open_sim
    MON._ULTIMA.update(t=None, proc=None, sis=None)
    ok(MON._memoria_total_mb() == 7812, f"RAM total desde /proc/meminfo: {MON._memoria_total_mb()} MB (esperado 7812)")
    ok(MON._memoria_proceso_mb() == 256, f"RAM del proceso desde /proc/self/status: {MON._memoria_proceso_mb()} MB (esperado 256)")
    ok(_PR.memoria_libre_mb() and round(_PR.memoria_libre_mb()) == 2930, f"RAM libre desde MemAvailable: {_PR.memoria_libre_mb()} MB (esperado 2930)")
    sis = MON._cpu_sistema_seg()
    ok(sis and abs(sis[1] - 9517.0) < 0.01 and abs(sis[0] - (9517.0 - 8010.0)) < 0.01, f"CPU de la máquina desde /proc/stat: ocupado {sis and sis[0]} s de {sis and sis[1]} s")
    m0 = MON.muestra()
    _PROC["/proc/stat"] = "cpu  100200 200 50100 800600 1000 0 500 0 0 0" + chr(10)
    time.sleep(0.3)
    m1 = MON.muestra()
    ok(m1["cpu_maquina_pct"] is not None and 30 <= m1["cpu_maquina_pct"] <= 40, f"CPU % de la máquina entre dos muestras: {m1['cpu_maquina_pct']} % (esperado ~33)")
    ok(m1["ram_total_mb"] == 7812 and m1["proceso_mb"] == 256, "y `muestra()` junta todo con los valores de Linux")
finally:
    builtins.open = _open0
    MON.os.name = _name0
    _PR.os.name = _name0
    if _sysconf0 is None:
        try: del MON.os.sysconf
        except Exception: pass
    else:
        MON.os.sysconf = _sysconf0

shutil.rmtree(_TMP, ignore_errors=True)
print()
if FALLOS:
    print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
    for f in FALLOS:
        print("   · " + f)
    sys.exit(1)
print("✅ CONTRATO VERDE — el monitor dice qué hizo el servidor, qué hizo el navegador y cuánto costó")
