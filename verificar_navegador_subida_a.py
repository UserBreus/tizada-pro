# -*- coding: utf-8 -*-
"""
CONTRATO: EL MOLDE SIN DISEÑO Y EL DXF SE SUBEN YA PREPARADOS, Y EL SERVIDOR NO LEE EL MOLDE — `py verificar_navegador_subida_a.py`

PLAN_NAVEGADOR.md, pendiente 1b. Con un molde sin diseño adentro (camino A) o un DXF, la pantalla
(`prepararMolde.js` → `obrero.worker.js` `dxf_convertir` + `alta_a`) manda el archivo junto con el
paquete `alta_a` (alta, detecciones por talle, lienzo de todas, el DXF original). Acá se arma ese
paquete con el motor del navegador en Node (`pruebas/subida_a.mjs`) y se sube a `POST /api/plantilla`
con `con_diseno=0`, con el servidor saboteado: si intenta dar de alta, detectar piezas o convertir
el DXF, el contrato cae. Después se comprueba que quedó TODO en su lugar (archivo, DXF original,
registro en la base, correspondencia del DXF, cachés de detección con la fecha del archivo) y que
el visor (`/api/plantilla/deteccion`) contesta desde esas cachés.

⚠️ No toca nada del usuario: DATOS y ENTRADA van a un temporal y `db` es un doble.
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
_TMP = tempfile.mkdtemp(prefix="verif_subida_a_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"

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
_LG.usar_carpeta(tempfile.mkdtemp(prefix="verif_subida_a_logs_"))
import servidor as S                          # noqa: E402
import motor_pedido as MP                     # noqa: E402
import importar_dxf                           # noqa: E402

S._USUARIOS_ON = False
CLI = S.app.test_client()
FALLOS = []
NODE = os.path.join(_AQUI, "frontend", "src", "motor", "pruebas", "subida_a.mjs")


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK    " if cond else "  FALLA ") + msg)


# ── sabotajes: con el paquete, el servidor no lee el molde ni convierte el DXF ────────────────
_LLAMADAS = []


def _prohibido(nombre):
    def _f(*a, **k):
        _LLAMADAS.append(nombre)
        raise RuntimeError(f"el servidor intentó {nombre} con un paquete del navegador")
    return _f


MP.alta_plantilla = _prohibido("dar de alta el molde (alta_plantilla)")
MP.alta_plantilla_manual = _prohibido("el alta manual (alta_plantilla_manual)")
MP.detectar_piezas = _prohibido("detectar las piezas (detectar_piezas)")
MP.detectar_piezas_todas = _prohibido("el lienzo de todas (detectar_piezas_todas)")
importar_dxf.dxf_a_pdf = _prohibido("convertir el DXF (dxf_a_pdf)")


def subir(pid, archivo_pdf, nombre, paquete):
    _DOCS["catalogo"] = {"activo": pid, "productos": [{"id": pid, "nombre": nombre}]}
    os.makedirs(os.path.join(_TMP, "entrada", pid), exist_ok=True)
    os.makedirs(os.path.join(_TMP, "productos", pid), exist_ok=True)
    with open(archivo_pdf, "rb") as fa, open(paquete, "rb") as fp:
        r = CLI.post("/api/plantilla", data={"archivo": (fa, nombre), "pid": pid, "con_diseno": "0",
                                             "paquete": (fp, "paquete.zip")}, content_type="multipart/form-data")
    job = (r.get_json() or {}).get("job")
    for _ in range(3000):
        e = _TRAB.get(job) or {}
        if e.get("estado") in ("listo", "error"):
            return r.status_code, e
        time.sleep(0.1)
    return r.status_code, {"estado": "colgado"}


def caso(titulo, origen, pid):
    print(f"\n{titulo}")
    tmp = tempfile.mkdtemp(prefix="subida_a_", dir=_TMP)
    copia = os.path.join(tmp, os.path.basename(origen))
    shutil.copy2(origen, copia)
    pdf, zip_, res = (os.path.join(tmp, x) for x in ("archivo.pdf", "paquete.zip", "resumen.json"))
    t = time.time()
    r = subprocess.run(["node", NODE, copia, pdf, zip_, res], capture_output=True, text=True, encoding="utf-8", timeout=900)
    ok(r.returncode == 0, f"el navegador preparó el molde ({time.time() - t:.1f} s)" + ("" if r.returncode == 0 else ": " + r.stderr[-400:]))
    if r.returncode != 0:
        return
    nav = json.load(open(res, encoding="utf-8"))
    es_dxf = origen.lower().endswith(".dxf")
    nombre_subida = os.path.basename(origen)
    st, fin = subir(pid, pdf, nombre_subida, zip_)
    ok(st == 200 and fin.get("estado") == "listo", f"la subida termina bien (HTTP {st}, «{fin.get('estado')}» {str(fin.get('error') or '')[:200]})")
    ok(not _LLAMADAS, f"y el servidor no leyó el molde ni convirtió el DXF ({_LLAMADAS or 'nada'})")
    resu = fin.get("resultado") or {}
    ok(resu.get("origen") != "con_diseno", "el molde quedó como molde SIN diseño (camino A)")
    ok(resu.get("talles") == nav["talles"] and resu.get("mesas") == nav["mesas"],
       f"con los talles y las mesas del paquete ({len(nav['talles'])} talles, {nav['mesas']} mesa/s)")
    ok(len(_REG.get(pid) or {}) == nav["piezas"], f"el registro quedó en la base con las {nav['piezas']} piezas del paquete ({len(_REG.get(pid) or {})})")
    destino = S._ruta_entrada("plantilla.ai", pid=pid, original=True)
    ok(os.path.exists(destino) and open(destino, "rb").read(5) == b"%PDF-", "el archivo del molde (PDF) está en su lugar")
    if es_dxf:
        fuente = S._ruta_entrada("plantilla_fuente.dxf", pid=pid)
        ok(os.path.exists(fuente) and open(fuente, "rb").read() == open(origen, "rb").read(), "el DXF original quedó guardado byte a byte")
        ok(isinstance(resu.get("dxf"), dict) and resu["dxf"].get("piezas") == (nav["dxf"] or {}).get("piezas"),
           f"la respuesta trae el resumen del DXF ({(resu.get('dxf') or {}).get('piezas')} piezas)")
        corr = S._ruta_datos("correspondencia_piezas.json", pid)
        ok(os.path.exists(corr) and json.load(open(corr, encoding="utf-8")) == nav["dxf"]["indices"],
           "la correspondencia pieza↔talle del DXF se escribió con el archivo")
        ok("indices" not in (resu.get("dxf") or {}), "y no viaja en la respuesta")
    # las cachés de detección: con la fecha del archivo final, una por talle + auto + todas
    cdir = S._ruta_datos("deteccion_cache", pid)
    mt = int(os.path.getmtime(destino))
    archivos = sorted(os.listdir(cdir)) if os.path.isdir(cdir) else []
    ok(f"{mt}_dv3_auto.json" in archivos, "la detección automática del visor quedó como caché con la fecha del archivo")
    ok(f"{mt}_dv2_TODAS.json" in archivos, "y el lienzo de todas las piezas también")
    faltan = [t for t in nav["detecciones"] if not os.path.exists(os.path.join(cdir, __import__("re").sub(r"[^A-Za-z0-9_-]+", "_", f"{mt}_dv3_{t}") + ".json"))]
    ok(not faltan, f"y las {len(nav['detecciones'])} por talle ({faltan or 'todas'})")
    # el visor las usa sin calcular nada
    r = CLI.get(f"/api/plantilla/deteccion?pid={pid}")
    d = r.get_json() or {}
    ok(r.status_code == 200 and d.get("piezas"), f"el visor del molde contesta ({r.status_code}, {len(d.get('piezas') or [])} piezas)")
    r = CLI.get(f"/api/plantilla/deteccion?pid={pid}&talle={nav['talles'][-1]}")
    ok(r.status_code == 200 and (r.get_json() or {}).get("piezas") is not None, f"y por talle («{nav['talles'][-1]}»)")
    ok(not _LLAMADAS, f"sin leer el molde ({_LLAMADAS or 'nada'})")


_AI = os.path.join(_AQUI, "entrada", "prod_20260911_165624_1ed7", "plantilla.ai")
_DXF = os.path.join(_AQUI, "entrada", "prod_20260911_165624_1ed7", "plantilla_fuente.dxf")
if len(sys.argv) > 1:
    caso("1 · EL ARCHIVO PEDIDO", sys.argv[1], "pA")
else:
    if os.path.exists(_AI):
        caso("1 · UN MOLDE .AI SIN DISEÑO", _AI, "pA")
    if os.path.exists(_DXF):
        caso("2 · UN MOLDE EN DXF", _DXF, "pD")

print()
if FALLOS:
    print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
    for f in FALLOS:
        print("   · " + f)
    sys.exit(1)
print("✅ CONTRATO VERDE — el molde sin diseño y el DXF llegan preparados y el servidor sólo guarda")
