# -*- coding: utf-8 -*-
"""
CONTRATO: SUBIR UN MOLDE NO TRABA EL SITIO — `py verificar_subida_no_traba.py`.

Leer un molde subido corría DENTRO del hilo que atiende la llamada web, así que quien sube se
quedaba con un atendedor del servidor todo ese rato y los demás hacían fila.

⚠️ Cuánto es «ese rato», medido bien el 2026-09-10 (ver changelog 420, que corrige al 419): un
molde del camino B de 118 MB son **4,4 s** (`alta_molde_con_diseno`, 6 mesas a la vez) y uno del
camino A de 1 MB son **2 s**. El número de 297 s que motivó este contrato era `alta_plantilla`
sobre un archivo que NO pasa por ahí: mal medido. Igual conviene que no bloquee — un molde grande
por el camino A sí cuesta minutos, y recibir 118 MB por la red ya ocupa el hilo un buen rato.

En el sistema de PEDIDO eso es lo primero que hace cualquiera: era el techo real de cuánta gente
puede entrar a la vez. El pedido tiene que aguantar a todo el mundo al mismo tiempo (pedido del
usuario 2026-09-10); la configuración es la que se reserva de a uno ([[reservas-quien-edita]]).

Lo que candamos:
  1. la llamada CONTESTA ENSEGUIDA, con un trabajo para seguir;
  2. la lectura pesada corre aparte y termina bien, con el mismo resumen de siempre;
  3. mientras uno lee su molde, el sitio le sigue contestando a los demás;
  4. 🔴 la lectura NO usa `request`: si lo hiciera, fuera del hilo web caería al molde ACTIVO
     GLOBAL — o sea, escribiría en el molde de otra persona;
  5. hay un cupo de lecturas a la vez, y al que espera se le dice.

⚠️ No toca nada del usuario: DATOS a un temporal, `db` es un doble, y el .ai de prueba es una COPIA
del molde más chico del catálogo (se lee, nunca se escribe encima).
"""
import os
import shutil
import sys
import tempfile
import time
import types

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_AQUI = os.path.dirname(os.path.abspath(__file__))
_TMP = tempfile.mkdtemp(prefix="verif_subida_")
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
import tempfile as _tl, registro as _LG      # noqa: E402
_LG.usar_carpeta(_tl.mkdtemp(prefix="verif_subida_logs_"))
import servidor as S                          # noqa: E402

S._USUARIOS_ON = False
CLI = S.app.test_client()
FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK    " if cond else "  FALLA ") + msg)


# ── El .ai de prueba: una COPIA del molde más chico que haya en el catálogo real ──────────────
def _molde_chico():
    base = os.path.join(_AQUI, "entrada")
    cands = []
    for d in os.listdir(base) if os.path.isdir(base) else []:
        f = os.path.join(base, d, "plantilla.ai")
        if os.path.exists(f):
            cands.append((os.path.getsize(f), f))
    return sorted(cands)[0][1] if cands else None


_ORIG = _molde_chico()
if not _ORIG:
    print("  (no hay ningún molde para copiar: esta prueba necesita uno)")
    sys.exit(0)
_COPIA = os.path.join(_TMP, "molde_de_prueba.ai")
shutil.copy2(_ORIG, _COPIA)
print(f"molde de prueba: copia de {os.path.basename(os.path.dirname(_ORIG))} "
      f"({os.path.getsize(_COPIA) / 1048576:.1f} MB)")

_DOCS["catalogo"] = {"activo": "pX", "productos": [{"id": "pX", "nombre": "Molde de prueba"}]}
# Las carpetas del molde las hace `crear_producto` en el sistema de verdad; acá se arma a mano.
os.makedirs(os.path.join(_TMP, "entrada", "pX"), exist_ok=True)
os.makedirs(os.path.join(_TMP, "productos", "pX"), exist_ok=True)

print("\n1 · LA LLAMADA CONTESTA ENSEGUIDA")
with open(_COPIA, "rb") as fh:
    _t0 = time.time()
    _r = CLI.post("/api/plantilla", data={"archivo": (fh, "molde_de_prueba.ai"), "pid": "pX"},
                  content_type="multipart/form-data")
    _tarda = time.time() - _t0
_d = _r.get_json() or {}
ok(_r.status_code == 200 and _d.get("job"),
   f"devuelve un trabajo para seguir (HTTP {_r.status_code}, job={_d.get('job')})")
ok(_d.get("procesando") is True, "y avisa que lo está procesando")
print(f"    el hilo web quedó libre en {_tarda:.2f} s (antes se quedaba con él toda la lectura)")

print("\n2 · MIENTRAS LEE, EL SITIO LE CONTESTA A LOS DEMÁS")
# 🔴 Es LO QUE SE ESTÁ ARREGLANDO. Se golpea una ruta liviana mientras la lectura corre.
_libres, _t1 = 0, time.time()
while time.time() - _t1 < 2.0:
    if CLI.get("/api/salud").status_code in (200, 503):
        _libres += 1
ok(_libres > 20, f"contestó {_libres} llamadas en 2 s con la lectura en curso")

print("\n3 · LA LECTURA TERMINA BIEN, CON EL RESUMEN DE SIEMPRE")
_job = _d.get("job")
_fin = None
for _ in range(600):                      # hasta 60 s: el molde de prueba es el más chico
    _e = _TRAB.get(_job) or {}
    if _e.get("estado") in ("listo", "error"):
        _fin = _e
        break
    time.sleep(0.1)
ok(_fin is not None, "la lectura termina (no se queda colgada)")
if _fin and _fin.get("estado") == "error":
    print("    error:", str(_fin.get("error"))[:160])
ok((_fin or {}).get("estado") == "listo", f"y termina bien (quedó «{(_fin or {}).get('estado')}»)")
_res = (_fin or {}).get("resultado") or {}
for _k in ("archivo", "mesas", "piezas", "talles", "completitud", "origen"):
    ok(_k in _res, f"el resumen trae «{_k}» (es lo que la pantalla ya sabe leer)")
ok(_res.get("archivo") == "molde_de_prueba.ai",
   f"y el nombre del archivo es el que se subió ({_res.get('archivo')!r})")
ok(os.path.exists(os.path.join(_TMP, "entrada", "pX", "plantilla.ai")),
   "el molde quedó guardado en su lugar")

print("\n4 · 🔴 LA PARTE PESADA NO MIRA `request`")
# Si lo hiciera, fuera del hilo web `_ruta_datos` y compañía caerían al molde ACTIVO GLOBAL: el
# molde de una persona se escribiría encima del de otra, y nadie se enteraría.
_src = open(os.path.join(_AQUI, "servidor.py"), encoding="utf-8").read()
_i = _src.index("def _procesar_molde_subido(")
_cuerpo = _src[_i:_src.index("@app.post(\"/api/plantilla\")", _i)]
ok("request." not in _cuerpo, "no usa `request` en ningún lado")
ok("_get_active_producto_id()" not in _cuerpo, "ni el molde activo global")
ok(_cuerpo.count("_PID") >= 5, f"todo va contra el molde que le pasaron ({_cuerpo.count('_PID')} usos)")

print("\n5 · HAY UN CUPO, Y AL QUE ESPERA SE LE DICE")
ok(S._ALTAS_A_LA_VEZ >= 1, f"hay un cupo de lecturas a la vez ({S._ALTAS_A_LA_VEZ})")
ok("esperando lugar" in _src, "y al que queda esperando se le dice, con cuántos tiene adelante")

print()
if FALLOS:
    print(f"  {len(FALLOS)} FALLO(S)")
    for f in FALLOS:
        print("   ·", f)
    sys.exit(1)
print("  OK: subir un molde ya no se queda con el servidor")
