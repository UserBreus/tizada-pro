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


def _elegir_molde():
    """Elige solo con qué molde verificar, leyendo el catálogo de disco.

    ⚠️ Antes el molde estaba **fijo** en el código (`prod_...4d0d`, «Manga pegada») y el contrato
    se rompió con un `FileNotFoundError` el día que el usuario lo borró y creó otro: un contrato no
    puede depender de datos que el usuario puede cambiar cuando quiera. Se prefiere el molde con
    posiciones en DOS variables (permite verificar la cascada vieja); si no hay, cualquiera con
    registro y piezas — las secciones que no se puedan verificar se saltean avisando.
    """
    try:
        cat = json.load(open(os.path.join(RAIZ, "datos", "productos_catalogo.json"), encoding="utf-8"))
    except Exception as e:
        print(f"no se pudo leer el catálogo: {e}")
        sys.exit(1)
    cands = []
    for p in (cat.get("productos") or []):
        pid = p.get("id")
        dreg = os.path.join(RAIZ, "datos", "productos", pid, "registro_producto.json")
        if not (pid and os.path.exists(os.path.join(RAIZ, "entrada", pid, "plantilla.ai")) and os.path.exists(dreg)):
            continue
        try:
            reg = json.load(open(dreg, encoding="utf-8"))
        except Exception:
            continue
        if not reg:
            continue
        pos = ((p.get("etiqueta") or {}).get("posiciones") or {})
        nvars = len({k.split("§")[0] for k in pos if "§" in k})
        # ¿tiene dos piezas con el mismo nombre? (para «cada pieza lleva su etiqueta»)
        gen = {}
        for n in reg:
            gen.setdefault(re.sub(r"\s+\d+\s*$", "", str(n)).strip().lower(), []).append(n)
        homon = max((len(v) for v in gen.values()), default=0)
        # un diseño con arte, si hay
        dis = None
        for d in (p.get("disenos") or []):
            nom = d.get("nombre") if isinstance(d, dict) else d
            slug = re.sub(r"[^a-z0-9]+", "-", str(nom or "").lower()).strip("-")[:48] or "principal"
            if os.path.exists(os.path.join(RAIZ, "entrada", pid, "disenos", slug, "arte.ai")):
                dis = nom
                break
        cands.append({"pid": pid, "nombre": p.get("nombre"), "reg": reg, "pos": pos,
                      "nvars": nvars, "homon": homon, "diseno": dis})
    if not cands:
        print("No hay ningún molde con plantilla + registro: no se puede verificar.")
        sys.exit(1)
    cands.sort(key=lambda c: (c["nvars"] >= 2, c["homon"] >= 2, len(c["pos"]), len(c["reg"])), reverse=True)
    return cands[0]


import re            # noqa: E402  (lo usa _elegir_molde)
_M = _elegir_molde()
PID = _M["pid"]
DISENO = _M["diseno"] or "principal"
# Una pieza que exista de verdad en este molde (la que tenga posición configurada, si hay).
PIEZA = next((k.split("§", 1)[-1] for k in _M["pos"] if k.split("§", 1)[-1] in _M["reg"]),
             sorted(_M["reg"])[0] if _M["reg"] else "Frente")

_TMP = tempfile.mkdtemp(prefix="verif_etq_")
_DATOS, _ENTRADA = os.path.join(_TMP, "datos"), os.path.join(_TMP, "entrada")
os.environ.update({"TIZADA_DATOS": _DATOS, "TIZADA_ENTRADA": _ENTRADA,
                   "TIZADA_TRABAJOS": os.path.join(_TMP, "trabajos"),
                   "TIZADA_FUENTES": os.path.join(RAIZ, "catalogo_fuentes"),
                   "TIZADA_DB_SERVER": r"localhost\NO_EXISTE_ES_UNA_PRUEBA"})
_falso_db = types.ModuleType("db")
_falso_db.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(
    AssertionError(f"LA PRUEBA INTENTO TOCAR MSSQL (db.{n}) — revisar el aislamiento")))

# ── LA "BASE" DEL REGISTRO, SIMULADA (2026-08-19: el server lee el registro SOLO de la base;
#    el doble la imita en memoria, sembrada del JSON que este contrato dejó en su tmp). ──
import json as _rj, os as _ro
_REG_MEM, _REG_REV = {}, {}
def _reg_leer(pid):
    if pid not in _REG_MEM:
        try:
            _p = _ro.path.join(_ro.environ["TIZADA_DATOS"], "productos", pid, "registro_producto.json")
            _REG_MEM[pid] = _rj.load(open(_p, encoding="utf-8")); _REG_REV[pid] = 1
        except Exception:
            return None
    return _REG_MEM.get(pid)
_falso_db.leer_registro = _reg_leer
_falso_db.registro_rev = lambda pid: (_REG_REV.get(pid, 1) if _reg_leer(pid) is not None else None)
_falso_db.guardar_registro = lambda pid, piezas, reg: (_REG_MEM.__setitem__(pid, reg),
                                                  _REG_REV.__setitem__(pid, _REG_REV.get(pid, 1) + 1), 1)[-1]
_falso_db.borrar_piezas_molde = lambda pid: (_REG_MEM.pop(pid, None), _REG_REV.pop(pid, None), 0)[-1]
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


def _render(fila, etq, pieza=None):
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
                if pz["pieza"] == (pieza or PIEZA) and h is None:
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
    # Con los datos del usuario puede no haber DOS variables configuradas (o ninguna): eso no es
    # una falla del sistema, así que esas aserciones se saltean avisando en vez de cortar.
    HAY_2V = len(claves) >= 2
    HAY_POS = bool(etq.get("posiciones"))
    if not HAY_2V:
        print("  (este molde no tiene posiciones en DOS variables → se saltea la cascada por variable)")
    if not HAY_POS:
        print("  (este molde no tiene NINGUNA posición de etiqueta configurada → sólo se verifica lo que no la necesita)")
    V1 = claves[0] if claves else ""
    V2 = claves[1] if HAY_2V else V1

    h1, i1 = _render({"talle": "M", "__variante": V1}, etq)
    h2, i2 = _render({"talle": "M", "__variante": V2}, etq)
    h0, i0 = _render({"talle": "M"}, etq)                              # sin variable
    hL, iL = _render({"talle": "M", "__variante": "Cuello redondo"}, etq)   # label en vez de clave
    etq_def = {**etq, "posiciones": {}}
    hd, _ = _render({"talle": "M", "__variante": V1}, etq_def)         # sin posiciones = default
    print(f"  {V1}: {h1} (llega {i1[0]!r})\n  {V2}: {h2} (llega {i2[0]!r})")
    print(f"  sin variable: {h0} (llega {i0[0]!r})\n  por label:    {hL} (llega {iL[0]!r})\n  default:      {hd}")

    ok(all([h1, h2, h0, hd]), f"se generó la pieza «{PIEZA}» en los cuatro escenarios")
    if HAY_POS: ok(h1 != hd, "con la posición configurada la etiqueta NO queda donde el default (si no, no se prueba nada)")
    if HAY_2V: ok(h1 != h2, "cada variable usa SU posición (la propia gana sobre la de la otra)")
    if HAY_POS: ok(h0 != hd, "una fila SIN variable ya no manda la etiqueta al lugar por defecto")
    if HAY_POS: ok(h0 == h1, "sin variable cae en la posición configurada (la 1ª de la config), no en otro lado")
    if HAY_POS: ok(hL == h1, "si llega el LABEL en vez de la clave, tampoco se va al default")

    # ── MODELO POR PIEZA (2026-08-18) ───────────────────────────────────────────────────────
    # La pantalla dejó de trabajar por variable: la posición es de la PIEZA y vale para todo el
    # molde (clave = nombre genérico, sin `variable§`). Dos cosas que tienen que ser ciertas:
    #   · la migración NO mueve la etiqueta de donde el usuario ya la tenía (la del molde real);
    #   · con el modelo nuevo, la fila con variable y la fila sin variable dan LO MISMO — que es
    #     todo el punto de haber sacado la variable del medio.
    print("\n  modelo POR PIEZA (posición = de la pieza, sin variable):")
    _pos_pieza, _conf = S._etq_posiciones_por_pieza(etq.get("posiciones"))
    etq_pieza = {**etq, "posiciones": _pos_pieza}
    print(f"    claves migradas: {sorted(_pos_pieza)} · conflictos: {_conf or 'ninguno'}")
    hp1, _ = _render({"talle": "M", "__variante": V1}, etq_pieza)
    hp0, _ = _render({"talle": "M"}, etq_pieza)
    print(f"    con variable: {hp1} · sin variable: {hp0} · (antes {V1}: {h1})")
    ok(not any("§" in k for k in _pos_pieza), "tras migrar no queda ninguna clave con el namespace viejo")
    ok(hp1 and hp0, "se generó la pieza con el modelo por pieza")
    if HAY_POS: ok(hp1 != hd, "la etiqueta por pieza NO cae en el default")
    ok(hp1 == hp0, "con o sin variable, la etiqueta cae en el MISMO lugar (ya no depende de la variable)")
    if HAY_POS: ok(hp1 == h1, "la migración deja la etiqueta donde ya estaba (no se mueve lo que el usuario tenía)")

    # ── CADA PIEZA LLEVA SU ETIQUETA (regla del usuario, 2026-08-18) ─────────────────────────
    # «Frente 1» y «Frente 2» son piezas DISTINTAS: poner la etiqueta de una al costado NO mueve
    # la de la otra. Tiene que garantizarlo el MOTOR, no sólo la pantalla — si colapsara las
    # claves al nombre genérico («frente»), las dos saldrían con la misma y el usuario no podría
    # distinguirlas al cortar. Se usa una fila sin variable para que salgan todas las piezas.
    _reg_all = S._cargar("registro_producto.json", PID) or {}
    _porgen = {}
    for _n in _reg_all:
        _porgen.setdefault(MP._norm_generico(_n), []).append(_n)
    _hom = sorted(next((v for v in _porgen.values() if len(v) >= 2), []))
    print(f"\n  cada pieza lleva SU etiqueta — piezas con el mismo nombre: {_hom or 'ninguna en este molde'}")
    if len(_hom) >= 2:
        A, B = _hom[0], _hom[1]
        _pos_a = {"rx": 0.05, "ry": 0.50, "t": 0.10, "ang": 0}
        _pos_b = {"rx": 0.95, "ry": 0.50, "t": 0.60, "ang": 0}
        etq_ab = {**etq, "posiciones": {A: dict(_pos_a), B: dict(_pos_b)}}
        hA, _ = _render({"talle": "M"}, etq_ab, pieza=A)
        hB, _ = _render({"talle": "M"}, etq_ab, pieza=B)
        # se mueve SÓLO la de A (a otro tramo del borde); la de B no se toca
        etq_mov = {**etq, "posiciones": {A: {"rx": 0.50, "ry": 0.95, "t": 0.35, "ang": 0}, B: dict(_pos_b)}}
        hA2, _ = _render({"talle": "M"}, etq_mov, pieza=A)
        hB2, _ = _render({"talle": "M"}, etq_mov, pieza=B)
        print(f"    «{A}»: {hA} → {hA2}\n    «{B}»: {hB} → {hB2}")
        ok(all([hA, hB, hA2, hB2]), f"se generaron las dos piezas homónimas ({A} y {B})")
        ok(hA != hA2, f"mover la etiqueta de «{A}» sí la cambia (si no, no se prueba nada)")
        ok(hB == hB2, f"mover la de «{A}» NO mueve la de «{B}» — cada pieza lleva la suya")
    else:
        print("    (este molde no tiene dos piezas con el mismo nombre: no se puede verificar acá)")
    shutil.rmtree(_TMP, ignore_errors=True)
    print("\n" + ("TODO OK" if not FALLOS else f"{len(FALLOS)} FALLA(S):\n  - " + "\n  - ".join(FALLOS)))
    sys.exit(1 if FALLOS else 0)
