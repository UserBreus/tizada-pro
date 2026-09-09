# -*- coding: utf-8 -*-
"""
CONTRATO: CADA MOLDE LEE SU COLUMNA DE TALLE — `py verificar_talle_por_molde.py`.

El caso (2026-09-09): un pedido con UN diseño («JUGADOR») que lleva DOS moldes —camiseta y
short— y una planilla con DOS columnas de talle («Talle» y «Talle short»). Cada molde tiene que
tomar el talle de la suya. Equivocarse acá NO da error: da una prenda del tamaño que no es, ya
impresa y cortada — la peor familia de errores del sistema (ver [[traba-antes-de-fabricar]]).

Lo que candamos:
  1. cada molde lee la columna que dice su `mapeo_columnas.talle`;
  2. 🔴 la celda del short VACÍA no hereda el talle de la camiseta (era el fallback de
     `_traducir_prendas`: `pr.get(talle_col) or pr.get("talle")`);
  3. un talle que ninguno de los moldes tiene en esa columna frena el pedido con 409
     (`_talles_cruzados`), en vez de salir impreso del tamaño equivocado;
  4. COMPAT: con UNA sola columna de talle el fallback sigue exactamente como estaba, así que
     ninguna planilla vieja cambia de comportamiento;
  5. `config_mapeo` hace MERGE: mandar sólo la columna de talle no borra nombre/número/manga.

⚠️ No toca nada del usuario: `db` es un doble que explota ([[test-no-toca-mssql]]), DATOS a un tmp.
"""
import os
import sys
import tempfile
import types

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_TMP = tempfile.mkdtemp(prefix="verif_talle_col_")
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tempfile as _tmp_log, registro as _LOG_PRUEBA   # noqa: E402
_LOG_PRUEBA.usar_carpeta(_tmp_log.mkdtemp(prefix="verif_logs_"))
import servidor as S               # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK   " if cond else "  FALLA") + " " + msg)


# ── El pedido real: una planilla con DOS columnas de talle ────────────────────────────────────
COLS_2T = [
    {"id": "talle", "label": "Talle", "role": "talle"},
    {"id": "talle_short", "label": "Talle short", "role": "talle"},
    {"id": "nombre", "label": "Nombre", "role": "nombre"},
    {"id": "numero", "label": "Número", "role": "numero"},
]
TPL_2T = [{"id": "tpl2", "nombre": "Con short", "columnas": COLS_2T}]

# Los talles que tiene cada molde salen del REGISTRO de piezas: la camiseta va por letras y el
# short por números, que es como los tiene el usuario.
REG_CAMISETA = {"Frente": {"S": {}, "M": {}, "L": {}}, "Espalda": {"S": {}, "M": {}, "L": {}}}
REG_SHORT = {"Delantero": {"1": {}, "2": {}, "3": {}}, "Trasero": {"1": {}, "2": {}, "3": {}}}


def molde(pid, nombre, col):
    return {"id": pid, "nombre": nombre, "columnas": COLS_2T, "planilla_template_id": "tpl2",
            "mapeo_columnas": {"talle": col, "nombre": "nombre", "numero": "numero",
                               "manga": "manga"}}


CAMISETA = molde("p_cam", "CAMISETA JUGADOR", "talle")
SHORT = molde("p_sho", "SHORT JUGADOR", "talle_short")
CAT_2T = {"productos": [CAMISETA, SHORT], "plantillas_planillas": TPL_2T}

print("1 · CADA MOLDE LEE SU COLUMNA (la misma fila, dos talles distintos)")
FILA = [{"talle": "M", "talle_short": "2", "nombre": "JUAN", "numero": "10"}]
_cam = S._traducir_prendas(FILA, CAMISETA, CAT_2T, reg=REG_CAMISETA)
_sho = S._traducir_prendas(FILA, SHORT, CAT_2T, reg=REG_SHORT)
ok(len(_cam) == 1 and _cam[0]["talle"] == "M",
   f"la camiseta toma «Talle» → {_cam and _cam[0]['talle']!r}")
ok(len(_sho) == 1 and _sho[0]["talle"] == "2",
   f"el short toma «Talle short» → {_sho and _sho[0]['talle']!r}")

print("\n2 · 🔴 LA CELDA DEL SHORT VACÍA **NO** HEREDA EL TALLE DE LA CAMISETA")
# Era el fallback `pr.get(talle_col) or pr.get("talle")`: con «Talle short» en blanco, el short
# salía con la M de la camiseta — impreso y cortado del tamaño equivocado.
FILA_SIN = [{"talle": "M", "talle_short": "", "nombre": "JUAN", "numero": "10"}]
_sho2 = S._traducir_prendas(FILA_SIN, SHORT, CAT_2T, reg=REG_SHORT)
ok(_sho2 == [], f"esa fila NO fabrica el short (salieron {len(_sho2)})")
ok(getattr(S._traducir_prendas, "faltantes", {}).get("Talle short") == 1,
   f"y se dice qué columna faltó: {getattr(S._traducir_prendas, 'faltantes', {})}")
_cam2 = S._traducir_prendas(FILA_SIN, CAMISETA, CAT_2T, reg=REG_CAMISETA)
ok(len(_cam2) == 1 and _cam2[0]["talle"] == "M",
   "la camiseta de esa misma fila sí sale (cada molde se resuelve por su lado)")

print("\n3 · UN TALLE QUE ESE MOLDE NO TIENE QUEDA ANOTADO (lo frena `generar_multi`)")
# Escribir en la columna del short un talle que sólo tiene la camiseta no da error: da una prenda
# del tamaño equivocado. Se anota por valor y por cantidad de filas para poder decirlo.
FILA_MAL = [{"talle": "M", "talle_short": "L", "nombre": "", "numero": ""},
            {"talle": "M", "talle_short": "L", "nombre": "", "numero": ""},
            {"talle": "M", "talle_short": "2", "nombre": "", "numero": ""}]
S._traducir_prendas(FILA_MAL, SHORT, CAT_2T, reg=REG_SHORT)
_aj = getattr(S._traducir_prendas, "talle_ajeno", {})
ok(_aj == {"L": 2}, f"el short avisa que «L» no es suyo, en 2 filas → {_aj}")
ok(getattr(S._traducir_prendas, "col_talle", "") == "Talle short",
   f"y de qué columna lo leyó, para poder explicarlo: {getattr(S._traducir_prendas, 'col_talle', '')!r}")
S._traducir_prendas(FILA_MAL, CAMISETA, CAT_2T, reg=REG_CAMISETA)
ok(getattr(S._traducir_prendas, "talle_ajeno", {}) == {},
   "la camiseta, que sí tiene «M», no dispara nada")
# Sin registro no se puede saber qué talles tiene: no se inventa una traba.
S._traducir_prendas(FILA_MAL, SHORT, CAT_2T)
ok(getattr(S._traducir_prendas, "talle_ajeno", {}) == {},
   "sin registro del molde no se traba nada (no se sabe qué talles tiene)")

print("\n3b · LA TRABA MIRA LA COLUMNA, NO EL MOLDE (un diseño vale si lo tiene UNO de sus moldes)")
# Preguntar molde por molde frenaría pedidos buenos: la regla del usuario es que el talle valga si
# lo tiene al menos UNO de los moldes del diseño. Por eso `_talles_cruzados` junta, POR COLUMNA,
# los talles de todos los moldes que la leen — y ahí sí, lo que no está es la columna equivocada.
_REGS = {"p_cam": REG_CAMISETA, "p_sho": REG_SHORT}
_reg_de = lambda pid: _REGS.get(str(pid), {})
_e = S._talles_cruzados(["p_cam", "p_sho"], FILA_MAL, CAT_2T, reg_de=_reg_de)
ok(bool(_e) and _e.get("error") == "un talle no es de ese molde",
   f"🔴 «L» en la columna del short frena el pedido: {(_e or {}).get('error')!r}")
ok(bool(_e) and "Talle short" in (_e.get("detalle") or ""),
   f"y el mensaje dice QUÉ columna hay que mirar: {(_e or {}).get('detalle')}")
ok(S._talles_cruzados(["p_cam", "p_sho"], FILA, CAT_2T, reg_de=_reg_de) is None,
   "una fila bien cargada pasa sin ruido")
# Dos moldes leyendo la MISMA columna: alcanza con que UNO tenga el talle (las medias no lo tienen).
_MEDIAS = molde("p_med", "MEDIAS", "talle")
_CAT_MED = {"productos": [CAMISETA, _MEDIAS], "plantillas_planillas": TPL_2T}
_reg2 = lambda pid: {"p_cam": REG_CAMISETA, "p_med": {"Media": {"S": {}}}}.get(str(pid), {})
ok(S._talles_cruzados(["p_cam", "p_med"], [{"talle": "L"}], _CAT_MED, reg_de=_reg2) is None,
   "🔴 un talle que sólo tiene UNO de los moldes de esa columna NO frena nada")

print("\n4 · COMPAT: con UNA sola columna de talle, todo sigue igual")
# El fallback por NOMBRE de campo existe para las planillas viejas y para las filas sintéticas
# (ficha, preview) que traen la clave «talle» a secas. Ahí tiene que seguir funcionando.
COLS_1T = [{"id": "variante", "label": "Talle", "role": "talle"},
           {"id": "nombre", "label": "Nombre", "role": "nombre"}]
P1 = {"id": "p1", "nombre": "Camiseta", "columnas": COLS_1T, "planilla_template_id": "tpl1",
      "mapeo_columnas": {"talle": "variante", "nombre": "nombre"}}
CAT_1T = {"productos": [P1],
          "plantillas_planillas": [{"id": "tpl1", "nombre": "Vieja", "columnas": COLS_1T}]}
_v = S._traducir_prendas([{"talle": "M", "nombre": "ANA"}], P1, CAT_1T,
                         reg=REG_CAMISETA, exigir_obligatorias=False)
ok(len(_v) == 1 and _v[0]["talle"] == "M",
   f"una fila con la clave «talle» a secas se resuelve igual que antes → {_v and _v[0]['talle']!r}")
# …y con DOS columnas ese mismo atajo ya no vale (es el que rellenaba el short)
_v2 = S._traducir_prendas([{"talle": "M", "nombre": "ANA"}], SHORT, CAT_2T,
                          reg=REG_SHORT, exigir_obligatorias=False)
ok(S._talles_cruzados(["p1"], [{"talle": "XXXL"}], CAT_1T, reg_de=lambda _p: REG_CAMISETA) is None,
   "y con una sola columna tampoco se traba por un talle que el molde no tiene "
   "(cada talle carga lo que tiene)")
ok(_v2 and _v2[0]["talle"] == "",
   f"🔴 con dos columnas, vacío es VACÍO: no se rellena con la de al lado → {_v2 and _v2[0]['talle']!r}")

print("\n5 · `config_mapeo` HACE MERGE (cambiar la columna de talle no borra el resto)")
# La pantalla del pedido sólo sabe de la columna de talle: si el endpoint pisara el dict entero,
# le borraría al molde el mapeo de nombre/número/manga sin que nadie lo note.
_CAT = {"productos": [dict(CAMISETA)], "plantillas_planillas": TPL_2T}
S._cargar_catalogo_para_editar = lambda *a, **k: _CAT
S._guardar_catalogo = lambda *a, **k: None
S._guard_id = lambda *a, **k: None
with S.app.test_client() as _cli:
    _r = _cli.post("/api/productos/config_mapeo",
                   json={"id": "p_cam", "planilla_template_id": "tpl2",
                         "mapeo_columnas": {"talle": "talle_short"}})
_m = _CAT["productos"][0]["mapeo_columnas"]
ok(_r.status_code == 200 and _m.get("talle") == "talle_short",
   f"la columna de talle cambia (HTTP {_r.status_code}, talle={_m.get('talle')!r})")
ok(_m.get("nombre") == "nombre" and _m.get("numero") == "numero" and _m.get("manga") == "manga",
   f"y el resto del mapeo queda intacto: {sorted(_m)}")

print()
if FALLOS:
    print(f"  {len(FALLOS)} FALLO(S)")
    sys.exit(1)
print("  OK: cada molde toma el talle de SU columna, y lo que no es suyo no se fabrica")
