"""
CONTRATO DE LA POSICIÓN DE LA ETIQUETA — se corre con `py verificar_etiqueta_posicion.py`.

La posición se guarda con la clave **`variante§NombrePieza`** (una por variable). El motor la
buscaba SÓLO por la variable de la fila: si la fila llegaba **sin variable** —el molde se pide
entero, o la variable elegida no resuelve piezas (`valores` sin `pieza_id` ni `pieza_idx`)— no
matcheaba ninguna clave y la etiqueta se iba al **lugar por defecto** (abajo al centro), aunque
estuviera configurada. Se ve bien en pantalla y sale movida en la tizada: otro error que sale
**bien impreso**. Reportado por el usuario: «en un molde funciona espectacular y en otro aparece
en el espacio predeterminado».

Lo que se verifica, con el molde REAL y el motor REAL (una pieza, sin generar la tizada entera):

  1. Cada variable usa **SU** posición (dos variables con posiciones distintas → renders distintos).
  2. Una fila **sin variable** cae en la posición configurada, no en el default.
  3. El default se ve distinto (si no, 1 y 2 no probarían nada).
  4. La cascada no pisa lo específico: con variable propia gana la suya.

⚠️ No toca nada del usuario: `DATOS`/`ENTRADA` son una COPIA en un temporal y el módulo `db` se
reemplaza por un doble que explota (ver [[test-no-toca-mssql]]).
"""
import hashlib
import json
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
PID = "prod_20260729_163651_4d0d"     # «Manga pegada»: 2 variables con posiciones distintas
PIEZA = "Dorso"                        # está en las dos variables, con posición distinta en cada una
DISENO = "jugador"

_TMP = tempfile.mkdtemp(prefix="verif_etq_")
_DATOS, _ENTRADA = os.path.join(_TMP, "datos"), os.path.join(_TMP, "entrada")
os.environ.update({"TIZADA_DATOS": _DATOS, "TIZADA_ENTRADA": _ENTRADA,
                   "TIZADA_TRABAJOS": os.path.join(_TMP, "trabajos"),
                   "TIZADA_FUENTES": os.path.join(RAIZ, "catalogo_fuentes"),
                   "TIZADA_DB_SERVER": r"localhost\NO_EXISTE_ES_UNA_PRUEBA"})
_falso_db = types.ModuleType("db")
_falso_db.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(
    AssertionError(f"LA PRUEBA INTENTO TOCAR MSSQL (db.{n}) — revisar el aislamiento")))
sys.modules["db"] = _falso_db

os.makedirs(os.path.join(_DATOS, "productos"), exist_ok=True)
for _f in os.listdir(os.path.join(RAIZ, "datos")):
    _o = os.path.join(RAIZ, "datos", _f)
    if os.path.isfile(_o):
        shutil.copy2(_o, os.path.join(_DATOS, _f))
shutil.copytree(os.path.join(RAIZ, "datos", "productos", PID), os.path.join(_DATOS, "productos", PID))
shutil.copytree(os.path.join(RAIZ, "entrada", PID), os.path.join(_ENTRADA, PID))

sys.path.insert(0, RAIZ)
import motor_pedido as MP      # noqa: E402
import servidor as S           # noqa: E402

FALLOS = []


def ok(cond, que):
    print(("  OK    " if cond else "  FALLA ") + que)
    if not cond:
        FALLOS.append(que)


def _render(fila, etq):
    """Genera la pieza con el motor REAL y devuelve el hash de su render (la etiqueta va estampada
    ahí adentro). Sólo la pieza, no la tizada: alcanza para ver dónde cae el texto."""
    import fitz
    cat = S._cargar_catalogo()
    prod = next(p for p in cat["productos"] if p["id"] == PID)
    reg = S._cargar("registro_producto.json", PID)
    sub = S._diseno_sub(DISENO)
    pl, arte = S._ruta_entrada("plantilla.ai", PID), S._ruta_entrada("arte.ai", PID, sub=sub)
    _b, _pv = S._mapeo_estructura(PID, sub=sub)
    mapeo = {"mapeo": _b or {}, "por_variable": _pv} if (_b or _pv) else None
    _cfg_n, _rot, telas, asig = S._config_produccion(PID)
    prendas = S._traducir_prendas([fila], prod, cat, DISENO, reg=reg)
    tmp = tempfile.mkdtemp()
    try:
        ppt = MP.generar_pedido(pl, arte, reg, MP.extraer_personalizacion(arte), prendas, S.FUENTES, tmp,
                                mapeo_arte=mapeo, solo_piezas=True, asignacion_tela=asig, telas_cfg=telas,
                                borde_corte=prod.get("borde_corte"), etiqueta=etq,
                                editables_cfg=S._editables_cfg(prod, DISENO),
                                editables_tamano=S._editables_tamano(prod),
                                editables_color=S._editables_color(prod, DISENO),
                                objetos_agregados=S._objetos_agregados_motor(PID, sub))
        h = None
        for _tela, pzs in (ppt or {}).items():
            for pz in pzs:
                if pz["pieza"] == PIEZA and h is None:
                    d = fitz.open("pdf", pz["doc"].tobytes())
                    h = hashlib.sha256(d[0].get_pixmap(dpi=42).tobytes("png")).hexdigest()[:16]
                    d.close()
                pz["doc"].close()
        return h, (prendas[0].get("variante_clave"), prendas[0].get("_grupo"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    cat = S._cargar_catalogo()
    prod = next(p for p in cat["productos"] if p["id"] == PID)
    etq = prod.get("etiqueta") or {}
    claves = sorted({k.split("§")[0] for k in (etq.get("posiciones") or {}) if "§" in k})
    print("molde:", prod.get("nombre"), "| variables con posiciones:", claves)
    if len(claves) < 2:
        print("Este contrato necesita un molde con posiciones en 2 variables — no se puede verificar.")
        sys.exit(1)
    V1, V2 = claves[0], claves[1]

    h1, i1 = _render({"talle": "M", "__variante": V1}, etq)
    h2, i2 = _render({"talle": "M", "__variante": V2}, etq)
    h0, i0 = _render({"talle": "M"}, etq)                              # sin variable
    hL, iL = _render({"talle": "M", "__variante": "Cuello redondo"}, etq)   # label en vez de clave
    etq_def = {**etq, "posiciones": {}}
    hd, _ = _render({"talle": "M", "__variante": V1}, etq_def)         # sin posiciones = default
    print(f"  {V1}: {h1} (llega {i1[0]!r})\n  {V2}: {h2} (llega {i2[0]!r})")
    print(f"  sin variable: {h0} (llega {i0[0]!r})\n  por label:    {hL} (llega {iL[0]!r})\n  default:      {hd}")

    ok(h1 and h2 and h0 and hd, f"se generó la pieza «{PIEZA}» en los cuatro escenarios")
    ok(h1 != hd, "con la posición configurada la etiqueta NO queda donde el default (si no, no se prueba nada)")
    ok(h1 != h2, "cada variable usa SU posición (la propia gana sobre la de la otra)")
    ok(h0 != hd, "una fila SIN variable ya no manda la etiqueta al lugar por defecto")
    ok(h0 == h1, "sin variable cae en la posición configurada (la 1ª de la config), no en otro lado")
    ok(hL == h1, "si llega el LABEL en vez de la clave, tampoco se va al default")
    shutil.rmtree(_TMP, ignore_errors=True)
    print("\n" + ("TODO OK" if not FALLOS else f"{len(FALLOS)} FALLA(S):\n  - " + "\n  - ".join(FALLOS)))
    sys.exit(1 if FALLOS else 0)
