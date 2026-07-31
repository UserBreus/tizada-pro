"""
CONTRATO: LA FICHA MUESTRA LAS PIEZAS EXACTAS DEL PEDIDO — `py verificar_ficha_piezas_pedido.py`.

Los TOGGLES (manga corta/larga, con/sin capucha…) cambian QUÉ PIEZAS lleva la prenda. La ficha
armaba su molde guía con una prenda de muestra **sin toggles**, así que salía siempre con la opción
por defecto: un pedido entero de manga LARGA mostraba las mangas CORTAS. El taller corta mirando
eso.

Lo que se verifica, con el molde y el motor REALES:
  1. Pedido de manga CORTA  → la guía trae las mangas cortas y NINGUNA larga.
  2. Pedido de manga LARGA  → al revés.
  3. Pedido MEZCLADO (una fila corta y otra larga, mismo diseño) → **las dos**, y el resto de las
     piezas UNA sola vez (el Frente no se repite).
  4. El rótulo dice qué opciones incluye («Manga: corta + larga»).

⚠️ No toca nada del usuario: `DATOS`/`ENTRADA` son una COPIA y `db` explota si alguien lo llama.
"""
import os
import shutil
import sys
import tempfile
import types

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = os.path.dirname(os.path.abspath(__file__))
PID = "prod_20260729_163651_4d0d"     # «Manga pegada»: tiene mangas cortas Y largas
DISENO = "jugador"

_TMP = tempfile.mkdtemp(prefix="verif_fpz_")
os.environ.update({"TIZADA_DATOS": os.path.join(_TMP, "datos"),
                   "TIZADA_ENTRADA": os.path.join(_TMP, "entrada"),
                   "TIZADA_TRABAJOS": os.path.join(_TMP, "trabajos"),
                   "TIZADA_FUENTES": os.path.join(RAIZ, "catalogo_fuentes"),
                   "TIZADA_DB_SERVER": r"localhost\NO_EXISTE_ES_UNA_PRUEBA"})
_falso_db = types.ModuleType("db")
_falso_db.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(
    AssertionError(f"LA PRUEBA INTENTO TOCAR MSSQL (db.{n})")))
sys.modules["db"] = _falso_db

os.makedirs(os.path.join(_TMP, "datos", "productos"), exist_ok=True)
for _f in os.listdir(os.path.join(RAIZ, "datos")):
    _o = os.path.join(RAIZ, "datos", _f)
    if os.path.isfile(_o):
        shutil.copy2(_o, os.path.join(_TMP, "datos", _f))
shutil.copytree(os.path.join(RAIZ, "datos", "productos", PID), os.path.join(_TMP, "datos", "productos", PID))
shutil.copytree(os.path.join(RAIZ, "entrada", PID), os.path.join(_TMP, "entrada", PID))

sys.path.insert(0, RAIZ)
import servidor as S     # noqa: E402

FALLOS = []


def ok(cond, que):
    print(("  OK    " if cond else "  FALLA ") + que)
    if not cond:
        FALLOS.append(que)


def guia_de(opciones_manga):
    """Arma la guía como lo hace el pedido: una combinación de toggles por opción usada."""
    cat = S._cargar_catalogo()
    prod = next(p for p in cat["productos"] if p["id"] == PID)
    reg = S._cargar("registro_producto.json", PID)
    _cfg = S._config_produccion(PID)
    filas = [{"talle": "M", "dise_o": "Jugador", "__variante": "v_7bu24xr", "manga": op}
             for op in opciones_manga]
    tr = S._traducir_prendas(filas, prod, cat, DISENO, reg=reg)
    combos, vistos = [], set()
    for p in tr:
        c = S._combo_toggles(p)
        if c not in vistos:
            vistos.add(c)
            combos.append(p.get("toggles") or [])
    var = {"clave": "v_7bu24xr", "piezas": tr[0].get("variante_piezas"),
           "asig": _cfg[3], "telas": _cfg[2], "diseno": DISENO, "combos": combos}
    return S._molde_guia_ficha(PID, prod, reg, DISENO, var), combos


def _mangas(g):
    cortas = sorted(p["nombre"] for p in g["piezas"] if "corta" in p["nombre"].lower())
    largas = sorted(p["nombre"] for p in g["piezas"] if "larga" in p["nombre"].lower())
    return cortas, largas


if __name__ == "__main__":
    try:
        print("\n[1] pedido de MANGA CORTA")
        g1, c1 = guia_de(["corta"])
        co1, la1 = _mangas(g1)
        print(f"    {len(g1['piezas'])} piezas · cortas={co1} · largas={la1} · rótulo: {g1.get('opciones')}")
        ok(len(co1) == 2 and not la1, "trae las mangas CORTAS y ninguna larga")

        print("\n[2] pedido de MANGA LARGA")
        g2, c2 = guia_de(["larga"])
        co2, la2 = _mangas(g2)
        print(f"    {len(g2['piezas'])} piezas · cortas={co2} · largas={la2} · rótulo: {g2.get('opciones')}")
        ok(len(la2) == 2 and not co2, "trae las mangas LARGAS y ninguna corta (antes salían las cortas)")

        print("\n[3] pedido MEZCLADO (una fila corta y otra larga)")
        g3, c3 = guia_de(["corta", "larga"])
        co3, la3 = _mangas(g3)
        nombres = [p["nombre"] for p in g3["piezas"]]
        print(f"    {len(g3['piezas'])} piezas · cortas={co3} · largas={la3}")
        print(f"    rótulo: {g3.get('opciones')}")
        ok(len(c3) == 2, "el pedido aporta DOS combinaciones distintas de toggle")
        ok(len(co3) == 2 and len(la3) == 2, "salen LAS DOS mangas (2 cortas + 2 largas)")
        ok(len(nombres) == len(set(nombres)), "sin piezas repetidas (el Frente aparece una sola vez)")
        ok(len(g3["piezas"]) == len(g1["piezas"]) + 2,
           f"son las de manga corta + las 2 largas ({len(g1['piezas'])} + 2 = {len(g3['piezas'])})")
        ok("corta" in (g3.get("opciones") or "").lower() and "larga" in (g3.get("opciones") or "").lower(),
           f"el rótulo dice que están las dos opciones: «{g3.get('opciones')}»")
    finally:
        shutil.rmtree(_TMP, ignore_errors=True)
    print("\n" + ("TODO OK" if not FALLOS else f"{len(FALLOS)} FALLA(S):\n  - " + "\n  - ".join(FALLOS)))
    sys.exit(1 if FALLOS else 0)
