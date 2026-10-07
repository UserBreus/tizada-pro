# -*- coding: utf-8 -*-
"""
CONTRATO: CANTIDAD Y PIEZAS (REPO) POR PLANILLA — `py verificar_planilla_cantidad_repo.py` (MAPA 624).

Pedido del usuario (2026-10-06): «la columna cantidad tenemos que tener la opción de ponerla o no en
las planillas y ponerla en mostrar siempre o mostrar cuando presionan el botón; lo mismo en la
columna de piezas que aparece en la repo».

Lo que se defiende:
  1. La columna Cantidad acepta `mostrar: 'no'` (además de 'boton' y 'siempre') y no se pisa.
  2. Con Cantidad «no va», la fila es UNA prenda aunque llegue un número; con 'boton' repite.
  3. Con Piezas (Repo) «no va» (`repo: 'no'` en la planilla), ninguna fila elige piezas aunque
     llegue `__repo`; con 'boton' la fila hace sólo las que eligió.
  4. Guardar la planilla guarda su `repo` (y un valor raro queda en 'boton').
  5. La API del otro sistema no publica una Cantidad «no va» y la toma como columna desconocida.
  6. La pantalla: los dos selectores en el editor de planillas y el pedido respeta el modo.

⚠️ No toca nada del usuario: `db` es un doble que explota ([[test-no-toca-mssql]]), DATOS a un tmp.
"""
import copy as _cp
import io
import os
import sys
import tempfile
import types

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_TMP = tempfile.mkdtemp(prefix="verif_cant_repo_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"

_falso_db = types.ModuleType("db")
_falso_db.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(
    AssertionError(f"LA PRUEBA INTENTO TOCAR MSSQL (db.{n}) — revisar el aislamiento")))
_DOCS = {}
_falso_db.set_doc = lambda c, o: _DOCS.__setitem__(c, _cp.deepcopy(o))
_falso_db.get_doc = lambda c, default=None: _cp.deepcopy(_DOCS.get(c, default))
_falso_db.proyectar_catalogo = lambda cat: None
sys.modules["db"] = _falso_db
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
import tempfile as _tmp_log, registro as _LOG_PRUEBA   # noqa: E402
_LOG_PRUEBA.usar_carpeta(_tmp_log.mkdtemp(prefix="verif_logs_"))
import servidor as S               # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK   " if cond else "  FALLA") + " " + msg)


REG = {"Frente": {t: {"mesa": 1, "w_cm": 50, "h_cm": 70} for t in ("S", "M")},
       "Espalda": {t: {"mesa": 2, "w_cm": 50, "h_cm": 70} for t in ("S", "M")}}
_cargar_real = S._cargar
S._cargar = lambda nombre, pid=None, *a, **k: (_cp.deepcopy(REG) if nombre == "registro_producto.json"
                                              else _cargar_real(nombre, pid, *a, **k))


def catalogo(mostrar="boton", repo="boton"):
    cols = [{"id": "talle", "label": "Talle", "role": "talle"},
            {"id": "nombre", "label": "Texto", "role": "nombre"},
            {"id": "cantidad", "label": "Cantidad", "role": "cantidad", "tipo": "numero", "mostrar": mostrar}]
    return {"productos": [{"id": "cam", "nombre": "Camiseta", "planilla_template_id": "p",
                           "mapeo_columnas": {"talle": "talle", "nombre": "nombre"}}],
            "plantillas_planillas": [{"id": "p", "nombre": "Estándar", "columnas": cols, "repo": repo}]}


print("\n1 · LA COLUMNA CANTIDAD ACEPTA «NO VA»")
for m in ("no", "boton", "siempre"):
    c = S._con_cantidad([{"id": "cantidad", "role": "cantidad", "mostrar": m}])
    ok(c[0]["mostrar"] == m, f"«{m}» se respeta")
ok(S._con_cantidad([{"id": "cantidad", "role": "cantidad", "mostrar": "x"}])[0]["mostrar"] == "boton", "un valor raro queda «con botón»")

print("\n2 · 🔴 CANTIDAD «NO VA»: cada fila es UNA prenda")
fila = [{"talle": "M", "nombre": "PEPE", "cantidad": "3"}]
cat = catalogo("boton")
ok(len(S._traducir_prendas(fila, cat["productos"][0], cat, reg=REG)) == 3, "con botón, cantidad 3 = 3 prendas")
cat = catalogo("no")
ok(len(S._traducir_prendas(fila, cat["productos"][0], cat, reg=REG)) == 1, "«no va»: aunque llegue 3, es 1 prenda")

print("\n3 · 🔴 PIEZAS (REPO) «NO VA»: ninguna fila elige piezas")
fila = [{"talle": "M", "nombre": "PEPE", "__repo": {"cam": ["Frente"]}}]
cat = catalogo(repo="boton")
out = S._traducir_prendas(fila, cat["productos"][0], cat, reg=REG)
ok(out and out[0].get("piezas_solo") == ["Frente"], f"con botón, la fila hace sólo «Frente» ({out and out[0].get('piezas_solo')})")
cat = catalogo(repo="no")
out = S._traducir_prendas(fila, cat["productos"][0], cat, reg=REG)
ok(out and not out[0].get("piezas_solo"), "«no va»: la fila hace todas sus piezas aunque llegue la elección")

print("\n4 · GUARDAR LA PLANILLA GUARDA SU REPO")
_CAT = catalogo()
S._cargar_catalogo_para_editar = lambda *a, **k: _CAT
S._cargar_catalogo = lambda *a, **k: _CAT
S._guardar_catalogo = lambda *a, **k: None
for v, esperado in (("siempre", "siempre"), ("no", "no"), ("cualquiera", "boton")):
    with S.app.test_request_context("/api/plantillas_planillas/guardar", method="POST",
                                    json={"id": "p", "nombre": "Estándar", "columnas": _CAT["plantillas_planillas"][0]["columnas"], "repo": v}):
        r = S.guardar_plantilla_planilla()
    r = r[0] if isinstance(r, tuple) else r
    ok(_CAT["plantillas_planillas"][0].get("repo") == esperado and (r.get_json() or {}).get("repo") == esperado,
       f"«{v}» se guarda como «{esperado}»")

print("\n5 · LA API DEL OTRO SISTEMA")
ie = io.open(os.path.join(_AQUI, "integracion_externa.py"), encoding="utf-8").read()
ok('if c.get("role") == "cantidad" and c.get("mostrar") == "no":\n            continue' in ie,
   "no publica una Cantidad «no va» en las columnas del molde")
ok('not (c.get("role") == "cantidad" and c.get("mostrar") == "no")' in ie,
   "y una cantidad mandada igual es `columna-desconocida` (como cualquier columna que no existe)")

print("\n6 · LA PANTALLA")
app = io.open(os.path.join(_AQUI, "frontend", "src", "App.jsx"), encoding="utf-8").read()
for ancla, que in (("col-cantidad-modo", "el selector de Cantidad en el editor de planillas"),
                   ("col-repo-modo", "el selector de Piezas (Repo)")):
    ok(f'data-tour="{ancla}"' in app, que)
ok("if (cfg && cfg.mostrar === 'no') return (_colsProd || []).filter(c => c.role !== 'cantidad');" in app,
   "el pedido saca la columna Cantidad cuando la planilla dice «no va»")
ok("const repoOn = repoModo === 'siempre' ? true : repoModo === 'no' ? false : repoBoton;" in app
   and "{repoModo === 'boton' && (<>" in app,
   "el pedido prende/apaga Piezas según la planilla y el botón «Repo» sólo aparece con «Con botón»")
ok("repo: planillaEditando.repo || 'boton'" in app, "guardar la planilla manda su modo de Repo")

print()
if FALLOS:
    print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
    for f in FALLOS:
        print("   · " + f)
    sys.exit(1)
print("✓ CONTRATO VERDE — cada planilla elige si lleva Cantidad y Piezas, y cuándo se ven")
