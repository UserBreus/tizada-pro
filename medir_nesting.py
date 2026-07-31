"""¿Cuánta tela se deja sin aprovechar por el «pruning» del nesting?

Con >15 piezas, `anidar_contorno` prueba UN solo orden (área desc.) y UNA sola estrategia (bl).
Acá se prueban todas las combinaciones con las MISMAS piezas reales y se compara contra eso.
Todo con el giro configurado por el usuario (180°).
"""
import os
import shutil
import sys
import tempfile
import time
import types

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RAIZ = r"C:\Users\user2\Documents\tincho\codigos\TIZADA PRO"
PID, DISENO, VAR = "prod_20260729_163651_4d0d", "jugador", "v_7bu24xr"
N_PRENDAS = int(os.environ.get("N_PRENDAS", "6"))
GIRO = os.environ.get("GIRO", "180")

_TMP = tempfile.mkdtemp(prefix="esf_nest_")
os.environ.update({"TIZADA_DATOS": os.path.join(_TMP, "datos"),
                   "TIZADA_ENTRADA": os.path.join(_TMP, "entrada"),
                   "TIZADA_TRABAJOS": os.path.join(_TMP, "trabajos"),
                   "TIZADA_FUENTES": os.path.join(RAIZ, "catalogo_fuentes"),
                   "TIZADA_DB_SERVER": r"localhost\NO_EXISTE"})
_f = types.ModuleType("db")
_f.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(AssertionError("tocó MSSQL")))
sys.modules["db"] = _f
os.makedirs(os.path.join(_TMP, "datos", "productos"), exist_ok=True)
for f in os.listdir(os.path.join(RAIZ, "datos")):
    o = os.path.join(RAIZ, "datos", f)
    if os.path.isfile(o):
        shutil.copy2(o, os.path.join(_TMP, "datos", f))
shutil.copytree(os.path.join(RAIZ, "datos", "productos", PID), os.path.join(_TMP, "datos", "productos", PID))
shutil.copytree(os.path.join(RAIZ, "entrada", PID), os.path.join(_TMP, "entrada", PID))

sys.path.insert(0, RAIZ)
import motor_pedido as MP                                        # noqa: E402
import servidor as S                                             # noqa: E402
import nesting_contorno as NC                                    # noqa: E402
from nesting_contorno import _preparar, _anidar_estrategia, CM   # noqa: E402

cat = S._cargar_catalogo()
prod = next(p for p in cat["productos"] if p["id"] == PID)
reg = S._cargar("registro_producto.json", PID)
cfg_n, rot, telas, asig = S._config_produccion(PID)
sub = S._diseno_sub(DISENO)
_b, _pv = S._mapeo_estructura(PID, sub=sub)
mapeo = {"mapeo": _b or {}, "por_variable": _pv} if (_b or _pv) else None
talles = sorted({t for v in reg.values() for t in (v or {}).keys()})
filas = [{"talle": talles[i % len(talles)], "dise_o": "Jugador", "__variante": VAR, "manga": "corta"}
         for i in range(N_PRENDAS)]
prendas = S._traducir_prendas(filas, prod, cat, DISENO, reg=reg)
tmp = tempfile.mkdtemp()
ppt = MP.generar_pedido(S._ruta_entrada("plantilla.ai", PID), S._ruta_entrada("arte.ai", PID, sub=sub),
                        reg, MP.extraer_personalizacion(S._ruta_entrada("arte.ai", PID, sub=sub)),
                        prendas, S.FUENTES, tmp, mapeo_arte=mapeo, solo_piezas=True,
                        asignacion_tela=asig, telas_cfg=telas,
                        borde_corte=prod.get("borde_corte"), etiqueta=prod.get("etiqueta"))
piezas = [pz for lst in ppt.values() for pz in lst]
for pz in piezas:
    pz["rotacion"] = GIRO
ANCHO = float(list(telas.values())[0]["ancho_cm"]) if telas else 180.0
M = cfg_n["margenes_cm"]

print(f"{len(piezas)} piezas reales · tela {ANCHO:.0f} cm · giro {GIRO} · separación {cfg_n['espaciado_cm']*10:.0f} mm\n")


def medir(res_mm, ordenes_todos, estrategias):
    cfg = {"ancho_cm": ANCHO, "altura_max_cm": 5000.0, "espaciado_cm": cfg_n["espaciado_cm"],
           "margenes_cm": M, "resolucion_mm": res_mm, "estrategias": estrategias}
    prep = _preparar(piezas, cfg)
    idx = list(range(len(piezas)))
    A = [int(piezas[i]["_mask"].sum()) for i in idx]
    Hh = [piezas[i]["_mask"].shape[0] for i in idx]
    Ww = [piezas[i]["_mask"].shape[1] for i in idx]
    if ordenes_todos:
        cands = [sorted(idx, key=lambda i: A[i], reverse=True),
                 sorted(idx, key=lambda i: Hh[i], reverse=True),
                 sorted(idx, key=lambda i: Ww[i], reverse=True),
                 sorted(idx, key=lambda i: max(Hh[i], Ww[i]), reverse=True)]
        ordenes, vistos = [], set()
        for o in cands:
            if tuple(o) not in vistos:
                vistos.add(tuple(o)); ordenes.append(o)
    else:
        ordenes = [sorted(idx, key=lambda i: A[i], reverse=True)]
    t0 = time.time()
    mejor = None
    for orden in ordenes:
        for est in estrategias:
            coloc, area = _anidar_estrategia(piezas, cfg, est, orden, prep)
            consumo = sum(max(c["cy"] + c["bh"] / 2 for c in h) for h in coloc if h)
            if mejor is None or consumo < mejor[0]:
                mejor = (consumo, coloc, area)
    alto_cm = max((c["cy"] + c["bh"] / 2) / CM for h in mejor[1] for c in h) + M["sup"] + M["inf"]
    aprov = (mejor[2] / 10000.0) / (ANCHO / 100 * alto_cm / 100) * 100
    return alto_cm, aprov, time.time() - t0, len(ordenes) * len(estrategias)


print(f"{'cómo se busca':<44}{'largo':>9}{'aprov.':>9}{'intentos':>10}{'tardó':>9}")
print("-" * 82)
ref = None
for nombre, res, todos, ests in [
        ("HOY (1 orden + bottom-left) — lo que corre", 4, False, ["bl"]),
        ("+ estrategia por bandas", 4, False, ["bl", "bandas"]),
        ("+ 4 órdenes de inserción", 4, True, ["bl"]),
        ("todo: 4 órdenes x 2 estrategias", 4, True, ["bl", "bandas"]),
        ("todo + grilla más fina (2 mm)", 2, True, ["bl", "bandas"])]:
    alto, aprov, tardo, n = medir(res, todos, ests)
    if ref is None:
        ref, dif = alto, ""
    else:
        dif = f"  ({(alto/ref-1)*100:+.1f}%)"
    print(f"{nombre:<44}{alto/100:>6.2f} m{dif:<9}{aprov:>7.1f} %{n:>8}{tardo:>8.1f}s")
shutil.rmtree(tmp, ignore_errors=True)
shutil.rmtree(_TMP, ignore_errors=True)
