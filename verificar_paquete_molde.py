# -*- coding: utf-8 -*-
"""
CONTRATO: EL SERVIDOR GUARDA EL MOLDE QUE PREPARÓ EL NAVEGADOR SIN VOLVER A CALCULARLO — `py verificar_paquete_molde.py [molde.ai]`

PLAN_NAVEGADOR.md, etapa 1. La persona carga el molde en SU computadora (`frontend/src/motor`), el
navegador lo prepara entero y manda el archivo + un paquete (`frontend/src/motor/paquete/armar.js`).
Lo que se candado acá:
  1. con el paquete, la subida termina bien y el servidor NO despliega nada: `alta_molde_con_diseno`
     y el pool de procesos están saboteados — si alguien los llama, el contrato corta;
  2. queda todo en su lugar: el desplegado vigente (páginas por talle con la regla y la decisión de
     la etiqueta actuales), el resumen de siempre, y lo de segundo plano tampoco lanza procesos;
  3. un paquete que NO sirve se rechaza con un mensaje y el molde anterior queda intacto: de otro
     archivo (SHA-1), de otra versión de las reglas, con un archivo de más en el ZIP, sin una mesa.

⚠️ No toca nada del usuario: DATOS a un temporal, `db` es un doble, y el .ai es una COPIA.
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
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_AQUI = os.path.dirname(os.path.abspath(__file__))
_TMP = tempfile.mkdtemp(prefix="verif_paquete_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"

_DOCS, _TRAB = {}, {}
_falso = types.ModuleType("db")
_falso.__getattr__ = lambda n: (lambda *a, **k: None)
_falso.get_doc = lambda c, default=None: _DOCS.get(c, default)
_falso.get_doc_ver = lambda c, default=None: (_DOCS.get(c, default), 0)
_falso.set_doc = lambda c, o, version_esperada=None: (_DOCS.__setitem__(c, o), 1)[-1]
_falso.guardar_catalogo = lambda cat, version_esperada=None: (_DOCS.__setitem__("catalogo", cat), 1)[-1]
_falso.leer_registro = lambda pid: None
_falso.trabajo_crear = lambda legacy_id, **k: _TRAB.__setitem__(legacy_id, {"estado": "en cola"})
_falso.trabajo_actualizar = lambda legacy_id, **k: (_TRAB.setdefault(legacy_id, {}).update(k), 1)[-1]
_falso.trabajo_leer = lambda tid: (dict(_TRAB[tid]) if tid in _TRAB else None)
_falso.trabajo_cancelado = lambda tid: False
_falso.trabajos_podar = lambda horas=6, vivos=200: 0
sys.modules["db"] = _falso
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")

sys.path.insert(0, _AQUI)
import registro as _LG                        # noqa: E402
_LG.usar_carpeta(tempfile.mkdtemp(prefix="verif_paquete_logs_"))
import servidor as S                          # noqa: E402
import piezas_con_diseno as PD                # noqa: E402

S._USUARIOS_ON = False
CLI = S.app.test_client()
FALLOS = []
NODE = os.path.join(_AQUI, "frontend", "src", "motor", "pruebas", "paquete.mjs")


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK    " if cond else "  FALLA ") + msg)


# ── sabotajes: el servidor no puede calcular nada ────────────────────────────────────────────
_LLAMADAS = []


def _prohibido(nombre):
    def _f(*a, **k):
        _LLAMADAS.append(nombre)
        raise RuntimeError(f"el servidor intentó {nombre} con un paquete del navegador")
    return _f


PD.alta_molde_con_diseno = _prohibido("desplegar el molde (alta_molde_con_diseno)")
PD._POOL_FACTORY = _prohibido("lanzar procesos (_POOL_FACTORY)")
PD._MESA_EN_SERIE = _prohibido("armar una mesa en serie")
PD.decidir_etiqueta_archivo = _prohibido("decidir la etiqueta")

# ── el molde: una COPIA (por defecto, el del camino B más chico de entrada/) ─────────────────
if len(sys.argv) > 1:
    _ORIG = sys.argv[1]
else:
    _c = [os.path.join(_AQUI, "entrada", d, "plantilla.ai") for d in os.listdir(os.path.join(_AQUI, "entrada"))]
    _c = [p for p in _c if os.path.exists(p) and os.path.isdir(os.path.join(os.path.dirname(p), "desplegado"))]
    _ORIG = min(_c, key=os.path.getsize) if _c else None
if not _ORIG:
    print("  (no hay un molde del camino B para copiar)")
    sys.exit(0)
_COPIA = os.path.join(_TMP, "molde_de_prueba.ai")
shutil.copy2(_ORIG, _COPIA)
print(f"molde de prueba: copia de {os.path.basename(_ORIG)} ({os.path.getsize(_COPIA) / 1048576:.1f} MB)")

_DOCS["catalogo"] = {"activo": "pX", "productos": [{"id": "pX", "nombre": "Molde de prueba"}]}
os.makedirs(os.path.join(_TMP, "entrada", "pX"), exist_ok=True)
os.makedirs(os.path.join(_TMP, "productos", "pX"), exist_ok=True)
_DESTINO = os.path.join(_TMP, "entrada", "pX", "plantilla.ai")

print("\n0 · EL NAVEGADOR PREPARA EL MOLDE Y ARMA EL PAQUETE")
_ZIP = os.path.join(_TMP, "paquete.zip")
_t = time.time()
_r = subprocess.run(["node", "--max-old-space-size=8192", NODE, _COPIA, _ZIP], capture_output=True, text=True, timeout=3600)
ok(_r.returncode == 0, f"el motor del navegador armó el paquete ({time.time() - _t:.1f} s)")
if _r.returncode != 0:
    print(_r.stderr[-800:])
    sys.exit(1)
print(f"    paquete: {os.path.getsize(_ZIP) / 1048576:.1f} MB")


def subir(archivo, paquete_bytes):
    with open(archivo, "rb") as fa:
        datos = {"archivo": (fa, "molde_de_prueba.ai"), "pid": "pX", "con_diseno": "1"}
        if paquete_bytes is not None:
            datos["paquete"] = (io.BytesIO(paquete_bytes), "paquete.zip")
        r = CLI.post("/api/plantilla", data=datos, content_type="multipart/form-data")
    job = (r.get_json() or {}).get("job")
    for _ in range(3000):
        e = _TRAB.get(job) or {}
        if e.get("estado") in ("listo", "error"):
            return r.status_code, e
        time.sleep(0.1)
    return r.status_code, {"estado": "colgado"}


print("\n1 · CON EL PAQUETE, EL SERVIDOR SÓLO GUARDA")
_paq = open(_ZIP, "rb").read()
_t = time.time()
_st, _fin = subir(_COPIA, _paq)
_tarda = time.time() - _t
ok(_st == 200 and _fin.get("estado") == "listo", f"la subida termina bien (HTTP {_st}, «{_fin.get('estado')}» {str(_fin.get('error') or '')[:160]})")
ok(not _LLAMADAS, f"y no calculó nada ({_LLAMADAS or 'ni desplegado, ni procesos, ni etiqueta'})")
_res = _fin.get("resultado") or {}
ok(_res.get("origen") == "con_diseno" and "navegador" in str(_res.get("motivo_origen")),
   f"el resumen dice que es un molde con diseño preparado por el navegador ({_res.get('motivo_origen')!r})")
_alta = json.loads(zipfile.ZipFile(_ZIP).read("alta.json"))
ok(_res.get("talles") == _alta["talles"] and _res.get("piezas") == _alta["piezas"] and _res.get("mesas") == _alta["mesas"],
   f"con los talles, las piezas y las mesas del paquete ({len(_alta['talles'])} talles, {len(_alta['piezas'])} piezas)")
print(f"    guardado en {_tarda:.1f} s")

print("\n2 · TODO QUEDA EN SU LUGAR")
ok(os.path.exists(_DESTINO), "el archivo del molde está en su lugar")
ok(PD.es_camino_b(_DESTINO), "marcado como molde con diseño")
ok(PD.desplegado_listo(_DESTINO), "el desplegado está listo")
ok(PD.paginas_vigentes(_DESTINO), "las páginas por talle son de este archivo, con la regla y la decisión vigentes")
time.sleep(3)                                          # lo de segundo plano (`_prewarm_desplegado`)
ok(not _LLAMADAS, f"lo de segundo plano tampoco calculó nada ({_LLAMADAS or 'nada'})")
_pl = PD.placeholders_desplegados(_DESTINO, armar=False) if hasattr(PD, "placeholders_desplegados") else None
if _pl is not None:
    ok(isinstance(_pl, dict), "los NOMBRE/00 del desplegado se leen sin armar nada")
_d1 = PD._leer_desplegado(_DESTINO, 1)
ok(_d1 is not None and _d1["pdf"] is not None, "la mesa 1 se lee del desplegado con su PDF")


def _rearmar(cambiar):
    """Copia del paquete bueno con un cambio."""
    src = zipfile.ZipFile(io.BytesIO(_paq))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for i in src.infolist():
            datos = src.read(i.filename)
            nuevo = cambiar(i.filename, datos)
            if nuevo is None:
                continue
            for nombre, contenido in (nuevo if isinstance(nuevo, list) else [(i.filename, nuevo)]):
                z.writestr(nombre, contenido)
    return out.getvalue()


print("\n3 · UN PAQUETE QUE NO SIRVE SE RECHAZA Y EL MOLDE ANTERIOR QUEDA INTACTO")
_antes = {f: os.path.getsize(os.path.join(os.path.dirname(_DESTINO), "desplegado", f))
          for f in os.listdir(os.path.join(os.path.dirname(_DESTINO), "desplegado"))}


def _intacto():
    carpeta = os.path.join(os.path.dirname(_DESTINO), "desplegado")
    ahora = {f: os.path.getsize(os.path.join(carpeta, f)) for f in os.listdir(carpeta)}
    return ahora == _antes and PD.paginas_vigentes(_DESTINO)


_otro = os.path.join(_TMP, "otro.ai")
shutil.copy2(_COPIA, _otro)
with open(_otro, "ab") as fh:
    fh.write(b"\n% otro archivo\n")
_casos = [
    ("de OTRO archivo", _otro, _paq, "no corresponde a este archivo"),
    ("de otra versión de las reglas", _COPIA, _rearmar(lambda n, d: json.dumps({**json.loads(d), "v_paginas": 999}).encode() if n == "manifest.json" else d), "otra versión"),
    ("con un archivo de más", _COPIA, _rearmar(lambda n, d: [(n, d), ("../../pisar.txt", b"x")] if n == "alta.json" else d), "no corresponde"),
    ("sin el PDF de una mesa", _COPIA, _rearmar(lambda n, d: None if n == "desplegado/m1.pdf" else d), "le falta"),
    ("dañado", _COPIA, _paq[: len(_paq) // 2], "dañado"),
]
for titulo, archivo, paquete, esperado in _casos:
    _st, _fin = subir(archivo, paquete)
    ok(_fin.get("estado") == "error" and esperado in str(_fin.get("error")),
       f"{titulo}: se rechaza ({str(_fin.get('error'))[:110]!r})")
    ok(_intacto(), f"{titulo}: el molde anterior queda intacto")
ok(not _LLAMADAS, f"y ninguno terminó calculando en el servidor ({_LLAMADAS or 'nada'})")
ok(not os.path.exists(os.path.join(_TMP, "pisar.txt")) and not os.path.exists(os.path.join(_TMP, "entrada", "pisar.txt")),
   "el archivo con ruta «../» no se escribió en ningún lado")

print()
shutil.rmtree(_TMP, ignore_errors=True)
if FALLOS:
    print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
    for f in FALLOS:
        print("   ·", f)
    sys.exit(1)
print("✅ CONTRATO VERDE — el servidor guarda el molde que preparó el navegador sin recalcularlo, y rechaza lo que no sirve")
