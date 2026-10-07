# -*- coding: utf-8 -*-
"""
CONTRATO: PLANILLA SIN TALLES — `py verificar_planilla_sin_talles.py` (MAPA 622).

Pedido del usuario (2026-10-06): «el talle depende de la planilla: creamos una planilla sin columna
de talle; nuestro sistema tiene que dejar crearla y la tizada tiene que entenderlo» (banderas,
moldes a medida: un solo tamaño).

Lo que se defiende:
  1. Una fila sin talle de una planilla SIN columna de talle sale con EL talle del molde (si tiene
     uno solo). Antes salía con talle vacío y el motor salteaba todas sus piezas SIN AVISAR.
  2. Con un molde de VARIOS talles no se adivina: queda anotado y el plan frena con el porqué.
  3. Una planilla CON talle sigue igual (la fila sin talle no se fabrica).
  4. Se puede guardar una planilla sin talle, salvo que la use un molde de varios talles; y no se
     le puede asignar a un molde de varios talles.
  5. La API del otro sistema publica `columna_talle: null` y no pide talle en esas filas.
  6. La ficha llama a la tabla «PLANILLA DEL PEDIDO» (gemelos py/js).

⚠️ No toca nada del usuario: `db` es un doble que explota ([[test-no-toca-mssql]]), DATOS a un tmp.
"""
import io
import os
import subprocess
import sys
import tempfile
import types

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_TMP = tempfile.mkdtemp(prefix="verif_sin_talles_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"

_falso_db = types.ModuleType("db")
_falso_db.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(
    AssertionError(f"LA PRUEBA INTENTO TOCAR MSSQL (db.{n}) — revisar el aislamiento")))
import copy as _cp
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
import ficha_tecnica as FT         # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK   " if cond else "  FALLA") + " " + msg)


# Los registros de los moldes de la prueba (lo que en el sistema vive en la base)
REGS = {
    "bandera": {"Bandera": {"Único": {"mesa": 1, "w_cm": 150, "h_cm": 90}}},
    "camiseta": {"Frente": {t: {"mesa": 1, "w_cm": 50, "h_cm": 70} for t in ("S", "M", "L")}},
}
_cargar_real = S._cargar
S._cargar = lambda nombre, pid=None, *a, **k: (_cp.deepcopy(REGS.get(pid, {})) if nombre == "registro_producto.json"
                                              else _cargar_real(nombre, pid, *a, **k))

COLS_SIN = [{"id": "nombre", "label": "Nombre", "role": "nombre"},
            {"id": "numero", "label": "Número", "role": "numero"}]
COLS_CON = [{"id": "talle", "label": "Talle", "role": "talle"}] + COLS_SIN


def catalogo():
    return {"productos": [
        {"id": "bandera", "nombre": "Bandera", "planilla_template_id": "sin",
         "mapeo_columnas": {"talle": "talle", "nombre": "nombre", "numero": "numero"}},
        {"id": "camiseta", "nombre": "Camiseta", "planilla_template_id": "con",
         "mapeo_columnas": {"talle": "talle", "nombre": "nombre", "numero": "numero"}},
    ], "plantillas_planillas": [
        {"id": "sin", "nombre": "Banderas", "columnas": COLS_SIN},
        {"id": "con", "nombre": "Estándar", "columnas": COLS_CON},
    ]}


def prod_de(cat, pid):
    return next(p for p in cat["productos"] if p["id"] == pid)


print("\n1 · 🔴 PLANILLA SIN TALLES + MOLDE DE UN SOLO TALLE: la fila va con ese talle")
cat = catalogo()
filas = [{"nombre": "PEÑAROL", "numero": "1"}, {"nombre": "NACIONAL", "numero": ""}]
out = S._traducir_prendas(filas, prod_de(cat, "bandera"), cat, reg=REGS["bandera"])
ok(len(out) == 2, f"no se descarta ninguna fila ({len(out)} de 2)")
ok(all(p.get("talle") == "Único" for p in out), "cada prenda sale con el talle del molde («Único»)")
ok(S._TP.talles_sin_columna == 0, "y no queda anotado ningún problema de talle")
ok(S._TP.obligatorias == [], "sin columna de talle no se exige talle")

print("\n2 · 🔴 PLANILLA SIN TALLES + MOLDE DE VARIOS TALLES: no se adivina")
cat = catalogo()
cam = dict(prod_de(cat, "camiseta"), planilla_template_id="sin")
out = S._traducir_prendas([{"nombre": "JUAN"}], cam, cat, reg=REGS["camiseta"])
ok(all(not p.get("talle") for p in out), "la fila queda sin talle (no se elige uno cualquiera)")
ok(S._TP.talles_sin_columna == 3, f"y queda anotado cuántos talles tiene el molde ({S._TP.talles_sin_columna})")
src = io.open(os.path.join(_AQUI, "servidor.py"), encoding="utf-8").read()
ok('"falta la columna de talle"' in src and "talles_sin_columna" in src.split("def _plan_del_pedido")[1][:20000],
   "el plan del pedido frena con «falta la columna de talle» (409)")

print("\n3 · EL MOLDE CON LA COLUMNA TALLE APAGADA cuenta como sin talle")
cat = catalogo()
b2 = dict(prod_de(cat, "bandera"), planilla_template_id="con", mapeo_columnas={"talle": "", "nombre": "nombre"})
out = S._traducir_prendas([{"nombre": "X", "talle": ""}], b2, cat, reg=REGS["bandera"])
ok(len(out) == 1 and out[0].get("talle") == "Único", "sale con el único talle (antes: 0 prendas, la obligatoria era la columna «»)")

print("\n4 · CON TALLE, COMO SIEMPRE")
cat = catalogo()
out = S._traducir_prendas([{"talle": "M", "nombre": "A"}, {"talle": "", "nombre": "B"}],
                          prod_de(cat, "camiseta"), cat, reg=REGS["camiseta"])
ok(len(out) == 1 and out[0]["talle"] == "M", "la fila sin talle no se fabrica; la otra sale con su talle")
ok(S._TP.talles_sin_columna == 0, "y no se anota nada de «sin columna»")

print("\n5 · GUARDAR Y ASIGNAR")
# el catálogo vive en la memoria de la prueba (como `verificar_talle_por_molde.py`)
_CAT = catalogo()
S._cargar_catalogo_para_editar = lambda *a, **k: _CAT
S._cargar_catalogo = lambda *a, **k: _CAT
S._guardar_catalogo = lambda *a, **k: None
_c = S.app.test_client()
r = _c.post("/api/plantillas_planillas/guardar", json={"id": "nueva_sin", "nombre": "Nueva", "columnas": COLS_SIN})
ok(r.status_code == 200, f"una planilla nueva sin columna de talle se guarda (HTTP {r.status_code})")
r = _c.post("/api/plantillas_planillas/guardar", json={"id": "con", "nombre": "Estándar", "columnas": COLS_SIN})
ok(r.status_code == 409 and "Camiseta" in (r.get_json() or {}).get("error", ""),
   f"sacarle el talle a la planilla de un molde de varios talles se frena y dice cuál (HTTP {r.status_code})")
ok(S._planilla_sin_talle_choca(S._cargar_catalogo(), "camiseta", "sin") is not None,
   "no se puede asignar una planilla sin talles a un molde de varios talles")
ok(S._planilla_sin_talle_choca(S._cargar_catalogo(), "bandera", "sin") is None,
   "…a uno de un solo talle, sí")
r = _c.post("/api/productos/asignar_planilla", json={"producto_id": "camiseta", "planilla_template_id": "sin"})
ok(r.status_code == 409, f"el endpoint de asignar lo frena (HTTP {r.status_code})")

print("\n6 · LA API DEL OTRO SISTEMA")
import integracion_externa as IE   # noqa: E402
ok(IE._columna_talle_que_lee({"mapeo_columnas": {"talle": "talle"}}, COLS_SIN) is None,
   "planilla sin talle → `columna_talle: null`")
ok(IE._columna_talle_que_lee({"mapeo_columnas": {"talle": "talle"}}, COLS_CON) == "talle", "con talle → su columna")
ok(IE._columna_talle_que_lee({"mapeo_columnas": {"talle": ""}}, COLS_CON) is None, "columna apagada en el molde → null")
ok("talle-sin-columna" in IE.ALARMAS, "existe la alarma `talle-sin-columna`")

print("\n7 · LA FICHA (gemelos py/js)")
ok(FT._titulo_tabla([{"id": "nombre", "role": "nombre"}]) == "PLANILLA DEL PEDIDO", "sin talle: «PLANILLA DEL PEDIDO»")
ok(FT._titulo_tabla([{"id": "talle", "role": "talle"}]) == "TABLA DE TALLES", "con talle: «TABLA DE TALLES»")
ok(FT._titulo_tabla([{"id": "nombre", "label": "Nombre"}]) == "TABLA DE TALLES", "columnas viejas sin `role`: como siempre")
_js = ("import('./frontend/src/motor/ficha/ficha.js').then(m => console.log(JSON.stringify(["
       "m.tituloTabla([{id:'nombre',role:'nombre'}]), m.tituloTabla([{id:'talle',role:'talle'}]),"
       "m.tituloTabla([{id:'nombre',label:'Nombre'}])])))")
try:
    _r = subprocess.run(["node", "--input-type=module", "-e", _js], cwd=_AQUI, capture_output=True, text=True, timeout=60)
    _v = _r.stdout.strip().splitlines()[-1] if _r.stdout.strip() else _r.stderr[-300:]
    ok(_v == '["PLANILLA DEL PEDIDO","TABLA DE TALLES","TABLA DE TALLES"]', f"el gemelo JS dice lo mismo ({_v})")
except Exception as e:
    ok(False, f"no se pudo correr el gemelo JS: {e}")

app = io.open(os.path.join(_AQUI, "frontend", "src", "App.jsx"), encoding="utf-8").read()
print("\n8 · LA PANTALLA")
ok('data-tour="col-sin-talles"' in app, "el editor de planillas tiene «Con talles / Sin talles»")
ok("Debe haber al menos una columna con el rol 'Talle'" not in app, "ya no exige la columna Talle al guardar")
ok("moldeSinTalle(pid)" in app and "role: c.role ||" in app,
   "la planilla del pedido usa el talle del molde y la ficha recibe el `role` de cada columna")

print()
if FALLOS:
    print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
    for f in FALLOS:
        print("   · " + f)
    sys.exit(1)
print("✓ CONTRATO VERDE — la planilla sin talles se crea, se entiende y no adivina")
