# -*- coding: utf-8 -*-
"""
CONTRATO: LAS COLUMNAS OBLIGATORIAS DECIDEN QUÉ FILA SE FABRICA — `py verificar_columnas_obligatorias.py`.

El caso (2026-08-31): «cargué 1 solo talle pero hay 4 filas más con el dato de la manga y el
diseño y me las creó del mismo talle». `_traducir_prendas` hacía `"talle": … or "M"`: la fila a
medio llenar salía impresa como talle M. NO FALLA: sale de más, bien impreso — la peor familia de
errores del sistema (ver [[traba-antes-de-fabricar]]).

Y la forma definitiva que pidió el usuario: **cuáles son las columnas obligatorias se configura en
la plantilla** (Configuración → Planillas), porque «puede ser 1 o varias; este molde debe ser
talle y diseño». Si la plantilla no marca ninguna, vale el talle — así ninguna planilla vieja
cambia de comportamiento sola.

⚠️ No toca nada del usuario: `db` es un doble que explota ([[test-no-toca-mssql]]), DATOS a un tmp.
"""
import os
import sys
import tempfile
import types

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_TMP = tempfile.mkdtemp(prefix="verif_oblig_")
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
# 🔴 El registro de la prueba va a un temporal, y se engancha ANTES de importar `servidor`
# (que espeja la consola al importarse): un test no puede ensuciar el registro del sistema
# de verdad — si no, mañana alguien investiga una falla que provocó una prueba.
import tempfile as _tmp_log, registro as _LOG_PRUEBA   # noqa: E402
_LOG_PRUEBA.usar_carpeta(_tmp_log.mkdtemp(prefix="verif_logs_"))
import servidor as S               # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK   " if cond else "  FALLA") + " " + msg)


COLS = [
    {"id": "talle", "label": "Talle", "role": "talle"},
    {"id": "nombre", "label": "Nombre", "role": "nombre"},
    {"id": "numero", "label": "Número", "role": "numero"},
    {"id": "manga", "label": "Manga", "role": "manga"},
    {"id": "diseno", "label": "Diseño", "role": "none"},
]


def catalogo(obligatorias=()):
    """Un catálogo con una plantilla cuyas columnas `obligatorias` están marcadas."""
    cols = [dict(c, **({"obligatoria": True} if c["id"] in obligatorias else {})) for c in COLS]
    prod = {"id": "p1", "nombre": "Camiseta", "columnas": COLS, "planilla_template_id": "tpl1"}
    return prod, {"productos": [prod],
                  "plantillas_planillas": [{"id": "tpl1", "nombre": "Estándar", "columnas": cols}]}


# La planilla del reporte: 1 fila cargada + 4 a medio llenar (manga y diseño puestos solos)
FILAS = [
    {"talle": "M", "nombre": "JUAN", "numero": "10", "manga": "corta", "diseno": "JUGADOR"},
    {"talle": "", "nombre": "", "numero": "", "manga": "corta", "diseno": "JUGADOR"},
    {"talle": "", "nombre": "", "numero": "", "manga": "corta", "diseno": "JUGADOR"},
    {"talle": "", "nombre": "", "numero": "", "manga": "larga", "diseno": "JUGADOR"},
    {"talle": "   ", "nombre": "", "numero": "", "manga": "corta", "diseno": "JUGADOR"},
]

print("\n1 · Sin nada configurado: vale el TALLE (el mínimo para poder cortar)")
prod, cat = catalogo()
out = S._traducir_prendas(FILAS, prod, cat)
ok(len(out) == 1, f"🔴 de 5 filas se fabrica 1, la que tiene talle (salieron {len(out)})")
ok(out and out[0]["talle"] == "M", "y es la del talle cargado")
ok(getattr(S._traducir_prendas, "sin_talle", 0) == 4, "se cuentan las 4 que quedaron afuera")
ok(not any(p["talle"] == "M" for p in out[1:]), "no se rellena con «M» por defecto (era el bug)")

print("\n2 · Con TALLE y DISEÑO obligatorios (el caso que pidió el usuario)")
prod2, cat2 = catalogo(("talle", "diseno"))
filas2 = [
    {"talle": "M", "diseno": "JUGADOR", "manga": "corta"},     # completa
    {"talle": "L", "diseno": "", "manga": "corta"},            # sin diseño → afuera
    {"talle": "", "diseno": "GOLERO", "manga": "corta"},       # sin talle → afuera
]
out2 = S._traducir_prendas(filas2, prod2, cat2)
ok(len(out2) == 1, f"🔴 sólo la fila COMPLETA se fabrica (salieron {len(out2)})")
ok(out2 and out2[0]["talle"] == "M", "y es la que tiene las dos columnas")
_f = getattr(S._traducir_prendas, "faltantes", {})
ok(_f.get("Diseño") == 1 and _f.get("Talle") == 1,
   f"se dice QUÉ columna faltó en cada fila: {_f}")
ok(sorted(getattr(S._traducir_prendas, "obligatorias", [])) == ["Diseño", "Talle"],
   "y cuáles eran las obligatorias, para poder explicarlo")

print("\n3 · UNA COLUMNA QUE ESTE MOLDE NO USA NO SE PIDE (si no, no se fabricaría nada)")
# 🔴 Pregunta del usuario (2026-08-31): «¿y si pongo "Talle short" obligatoria pero la variante que
# elijo no lleva esa columna y no aparece?». Esa columna estaría SIEMPRE vacía: exigirla dejaría el
# pedido sin ninguna fila. El criterio es el mismo que usa la pantalla para mostrarla: las columnas
# de rol mapeable valen sólo si ESTE molde las mapea por id.
COLS_2T = COLS + [{"id": "talle_short", "label": "Talle short", "role": "talle"}]
cols_marcadas = [dict(c, **({"obligatoria": True} if c["id"] in ("talle", "talle_short") else {}))
                 for c in COLS_2T]
# el molde usa «Talle» (no «Talle short»): su mapeo lo dice
prod4 = {"id": "p1", "nombre": "Camiseta", "columnas": COLS_2T, "planilla_template_id": "tpl1",
         "mapeo_columnas": {"talle": "talle", "nombre": "nombre", "numero": "numero", "manga": "manga"}}
cat4 = {"productos": [prod4],
        "plantillas_planillas": [{"id": "tpl1", "nombre": "Estándar", "columnas": cols_marcadas}]}
out4 = S._traducir_prendas([{"talle": "M", "manga": "corta", "diseno": "JUGADOR"}], prod4, cat4)
ok(len(out4) == 1,
   f"🔴 la fila SE FABRICA aunque «Talle short» esté marcada obligatoria: este molde no la usa (salieron {len(out4)})")
ok(getattr(S._traducir_prendas, "obligatorias", []) == ["Talle"],
   f"y sólo se exige la columna que el molde sí usa: {getattr(S._traducir_prendas, 'obligatorias', [])}")
# …y si el molde SÍ la usa, entonces sí se exige
prod5 = dict(prod4, mapeo_columnas={"talle": "talle_short", "nombre": "nombre",
                                    "numero": "numero", "manga": "manga"})
cat5 = {"productos": [prod5], "plantillas_planillas": cat4["plantillas_planillas"]}
out5 = S._traducir_prendas([{"talle_short": "", "manga": "corta"}], prod5, cat5)
ok(out5 == [], "pero en un molde que SÍ usa «Talle short», la fila sin ese dato no se fabrica")

print("\n4 · Lo que no se rompe")
prod3, cat3 = catalogo(("talle",))
solo = S._traducir_prendas([{"talle": "XL", "nombre": "", "numero": "", "manga": "corta"}], prod3, cat3)
ok(len(solo) == 1 and solo[0]["talle"] == "XL",
   "una fila con sólo lo obligatorio se fabrica (nombre y número son opcionales)")
ok(S._traducir_prendas([{"talle": "", "manga": "corta"}], prod3, cat3) == [],
   "una planilla sin ninguna fila completa no genera nada")

print("\n4b · LAS MUESTRAS INTERNAS NO PASAN POR EL FILTRO (la ficha, el visor, el preview)")
# 🔴 LA CAUSA REAL de «la ficha técnica no muestra lo que mostraba» (2026-08-31): el sistema arma
# filas SINTÉTICAS para dibujar —el molde guía de la ficha, el preview de las piezas del arte— con
# lo mínimo (talle, nombre, número, variable). Esas filas no tienen las columnas que el usuario
# marcó obligatorias, así que el filtro nuevo las descartaba: sin prendas, sin piezas, sin molde
# guía. Las obligatorias son una regla DEL PEDIDO, no de los dibujos internos.
prodM, catM = catalogo(("talle", "diseno"))
_muestra = [{"talle": "M", "nombre": "NOMBRE", "numero": "00", "manga": "corta"}]   # sin «Diseño»
ok(S._traducir_prendas(_muestra, prodM, catM) == [],
   "con el filtro puesto, esa fila de muestra se descarta (es lo que rompía la ficha)")
_okm = S._traducir_prendas(_muestra, prodM, catM, exigir_obligatorias=False)
ok(len(_okm) == 1,
   "🔴 pero como MUESTRA INTERNA sí sale, y la ficha vuelve a tener su molde guía")
ok(_okm and _okm[0]["talle"] == "M", "con su talle, para poder dibujar las piezas")
_src0 = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "servidor.py"), encoding="utf-8").read()
ok(_src0.count("exigir_obligatorias=False") >= 3,
   f"y las TRES muestras internas lo apagan (ficha, preview, visor): {_src0.count('exigir_obligatorias=False')}")

print("\n5 · LA FICHA TÉCNICA no se queda sin moldes por ignorar filas")
# 🔴 Reporte del usuario (2026-08-31): «¿por qué ahora en la ficha no se ve todo lo que se veía,
# información de los moldes?». Las guías de la ficha se arman recorriendo las PRENDAS: al ignorar
# filas incompletas se iban con ellas. La TABLA lista sólo lo fabricado (eso se pidió), pero los
# MOLDES GUÍA son la referencia del trabajo y tienen que estar igual.
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "servidor.py"), encoding="utf-8").read()
ok("LOS MOLDES DEL PEDIDO VAN SIEMPRE" in _src,
   "🔴 la ficha completa sus guías con los moldes del pedido, no sólo con los de las prendas")
ok("_specs = list(_guias_ficha)" in _src,
   "y arranca de las guías reales (las de las prendas, con su variable y sus toggles)")
ok('or {_slugify_diseno(default_diseno): None}' in _src,
   "un pedido sin variables por diseño igual trae su molde (con el diseño que se editó en el Arte)")
# …pero SÓLO en los diseños que son suyos: completar un molde en un diseño ajeno era lo que
# duplicaba la ficha (entrada 396).
ok('if _dl2 and str(_p) not in _dl2:' in _src,
   "y el completado respeta el mapa molde→diseño (no agrega el molde en un diseño que no es suyo)")

print()
if FALLOS:
    print(f"  {len(FALLOS)} FALLO(S)")
    sys.exit(1)
print("  OK: sólo se fabrica lo que tiene cargadas TODAS las columnas obligatorias")
