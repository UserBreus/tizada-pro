# -*- coding: utf-8 -*-
"""CONTRATO: UNA MESA QUE FALLA NO TIRA EL POOL DEL DESPLEGADO — `py verificar_desplegado_pool.py`

Lo que pasó (2026-09-11, medido en el registro): el motor tenía abierta la página de la mesa 3
mientras un worker del pool la reescribía → «Acceso denegado» → el `except` envolvía al pool
ENTERO → las mesas que faltaban se armaron en serie DENTRO del servidor, 3 minutos con el GIL
tomado, justo cuando el paso Tizada pedía las vistas previas (que salieron a cuentagotas: «algunas
se ven y otras no, o demora mucho»).

Se prueba con un pool DE MENTIRA (sin procesos, sin archivos):
  1. una mesa que falla una vez se reintenta en el pool y NADA va en serie;
  2. una mesa que falla dos veces hace FALLAR el desplegado con mensaje claro (nada en serie);
  3. si el pool no arranca, todo va en serie (como siempre);
  4. `_reemplazar` aguanta lo que dura un render (más de 30 s de reintento).

⚠️ No toca `entrada/` ni `datos/`: el molde es un nombre inventado y nadie lo abre.
"""
import os
import sys
from concurrent.futures import Future

sys.stdout.reconfigure(encoding="utf-8")
_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)

import piezas_con_diseno as PD   # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)


class PoolDeMentira:
    """Un executor que resuelve en el acto: la mesa `falla` revienta las primeras `veces`."""
    def __init__(self, falla, veces):
        self.falla, self.veces, self.enviadas = falla, veces, []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def submit(self, fn, args):
        mesa = args[1]
        self.enviadas.append(mesa)
        f = Future()
        if mesa == self.falla and self.enviadas.count(mesa) <= self.veces:
            f.set_exception(PermissionError("Acceso denegado: m3.pdf.tmp -> m3.pdf"))
        else:
            f.set_result((mesa, [{"mesa": mesa}]))
        return f


def correr(falla, veces, procesos=4):
    en_serie = []

    def serie(path, mesa, talles, contornos=True, paginas=True):
        en_serie.append(mesa)
        return [{"mesa": mesa, "serie": True}]

    pool = PoolDeMentira(falla, veces)
    PD._POOL_FACTORY = lambda max_workers: pool
    PD._MESA_EN_SERIE = serie
    por_mesa = {}
    try:
        PD._desplegar_molde_sin_candado("molde_inventado.ai", ["M", "L"], None, procesos, True, True,
                                        9, list(range(1, 10)), por_mesa)
    finally:
        PD._POOL_FACTORY = PD._pool_por_defecto
        PD._MESA_EN_SERIE = PD.desplegar_mesa
    return por_mesa, en_serie, pool.enviadas


# ── 1. falla una vez → se reintenta en el pool, nada en serie ─────────────────────────────────
por_mesa, en_serie, enviadas = correr(falla=3, veces=1)
ok(sorted(por_mesa) == list(range(1, 10)), f"faltan mesas: {sorted(por_mesa)}")
ok(en_serie == [], f"con UNA falla algo fue en serie: {en_serie}")
ok(enviadas.count(3) == 2, f"la mesa 3 no se reintentó en el pool (enviadas: {enviadas})")
print(f"  · falla una vez: 9/9 del pool, reintentada 1 vez, en serie: {en_serie}")

# ── 2. falla dos veces → el desplegado FALLA con mensaje claro; nada en serie ────────────────
# (2026-09-17: antes «sólo ESA mesa va en serie al final»; el plan B en el servidor se eliminó,
#  ver `_repartir` y `verificar_sin_plan_b_en_el_servidor.py`)
try:
    por_mesa, en_serie, enviadas = correr(falla=3, veces=2)
    ok(False, "con una mesa que falla dos veces tendría que saltar ProcesoNoTermino")
except PD.ProcesoNoTermino as e:
    ok("tarea 3" in str(e) and "dos veces" in str(e), f"el mensaje tendría que nombrar la mesa 3: {e}")
    print(f"  · falla dos veces: ProcesoNoTermino ({e})")
finally:
    PD._POOL_FACTORY = PD._pool_por_defecto
    PD._MESA_EN_SERIE = PD.desplegar_mesa

# ── 3. el pool no arranca → error claro, nada en serie ───────────────────────────────────────
en_serie = []


def serie3(path, mesa, talles, contornos=True, paginas=True):
    en_serie.append(mesa)
    return [{"mesa": mesa}]


def _no_arranca(max_workers):
    raise OSError("sin procesos")


PD._POOL_FACTORY = _no_arranca
PD._MESA_EN_SERIE = serie3
try:
    por_mesa = {}
    PD._desplegar_molde_sin_candado("molde_inventado.ai", ["M"], None, 4, True, True, 3, [1, 2, 3], por_mesa)
    ok(False, "sin pool tendría que saltar ProcesoNoTermino")
except PD.ProcesoNoTermino as e:
    ok("procesos libres" in str(e), f"el mensaje tendría que decir que no hubo procesos: {e}")
finally:
    PD._POOL_FACTORY = PD._pool_por_defecto
    PD._MESA_EN_SERIE = PD.desplegar_mesa
ok(en_serie == [], f"sin pool NADA va en serie en este proceso, fue: {en_serie}")
print("  · sin pool: ProcesoNoTermino, ninguna mesa en serie")

# ── 4. `_reemplazar` espera lo que dura un render ───────────────────────────────────────────
import inspect  # noqa: E402
_sig = inspect.signature(PD._reemplazar)
_intentos = _sig.parameters["intentos"].default
_espera = sum(min(1.0, 0.25 * (i + 1)) for i in range(_intentos - 1))
ok(_espera >= 30, f"`_reemplazar` espera {_espera:.0f} s: menos que un render (15 s de piezas + ficha)")
print(f"  · `_reemplazar`: {_intentos} intentos, ~{_espera:.0f} s de espera")

print()
if FALLOS:
    print("✗ FALLA:")
    for f in FALLOS:
        print("   ·", f)
    sys.exit(1)
print("OK pool: una mesa que falla se reintenta en el pool; si insiste, error claro; nada se arma en este proceso")
