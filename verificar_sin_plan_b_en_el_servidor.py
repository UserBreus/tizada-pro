# -*- coding: utf-8 -*-
"""
CONTRATO: NINGÚN «PLAN B» HACE EL TRABAJO PESADO ADENTRO DEL SERVIDOR — `py verificar_sin_plan_b_en_el_servidor.py`

Lo que pasó (16/09/2026 en el publicado, informe «plan-b-dentro-del-servidor.pdf»): los procesos
de dos camisetas no terminaron en 30 minutos (la máquina ahogada) y cinco lugares distintos
tenían el mismo reflejo —«el pool falló; sigo en serie acá»— que hizo el trabajo ADENTRO del
proceso web con el GIL tomado hasta las 18:02: 8 hilos trabados, 34 pedidos en cola, la base con
«Query timeout». Lo que no cabe en un proceso aparte tampoco cabe en el servidor.

Lo que protege, simulando ese día con topes de 5 segundos y procesos que NUNCA terminan:
  1. `decidir_etiqueta_archivo`         (búsqueda de etiquetas)
  2. `_armar_paginas`                    (páginas por talle de una mesa)
  3. `_desplegar_molde_sin_candado`      (una mesa por proceso)
  4. `hoja_pike.svgs_de_bases`           (SVG de las bases de la previa)
  5. `servidor._svgs_de_piezas`          (SVG de las piezas del Arte)
  6. `servidor._predibujar_mesas`        (los recortes de las mesas, pre-dibujados)
  Para cada uno: la llamada termina en segundos (no en 30 minutos), con un error claro o sin ese
  resultado; la tarea NO se ejecutó en el proceso que llama; y `GET /api/salud` siguió
  contestando al instante mientras tanto.
  7. Todos los pools de trabajo toman lugar de UN cupo global (`procesos.pool`) con REPARTO
     JUSTO: ninguno toma más de la mitad (dos moldes avanzan a la vez), nadie espera mientras
     haya un proceso libre, y con el cupo lleno el siguiente espera y falla con `SinLugar`.

⚠️ No toca nada del usuario: `DATOS` va a un temporal y el módulo `db` se reemplaza por un doble
(ver [[test-no-toca-mssql]]). No se lanza ningún proceso de verdad: los pools son de mentira.
"""
import os
import sys
import tempfile
import threading
import time
import types
from concurrent.futures import Future

sys.stdout.reconfigure(encoding="utf-8")
_TMP = tempfile.mkdtemp(prefix="verif_plan_b_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = "localhost\\NO_EXISTE_ES_UNA_PRUEBA"
for _v in ("TIZADA_TOPE_PROCESO_S", "TIZADA_TOPE_DESPLEGADO_S", "TIZADA_TOPE_ETIQUETAS_S",
           "TIZADA_TOPE_SVG_S", "TIZADA_ESPERA_LUGAR_S"):
    os.environ[_v] = "5"

_falso = types.ModuleType("db")
_falso.__getattr__ = lambda nombre: (lambda *a, **k: None)
_falso.get_doc = lambda c, default=None: default
_falso.tablas = lambda: []
sys.modules["db"] = _falso

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)

import registro as LOG          # noqa: E402
LOG.usar_carpeta(os.path.join(_TMP, "registro"))
import procesos as PR           # noqa: E402
import piezas_con_diseno as PD  # noqa: E402
import hoja_pike as HP          # noqa: E402
import servidor as S            # noqa: E402
import pymupdf as fitz          # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
        print(f"  ✗ {msg}")


class PoolQueNoTermina:
    """Un executor cuyos futuros NUNCA se resuelven: los procesos ahogados del 16/09."""
    creados = 0

    def __init__(self, *a, **k):
        PoolQueNoTermina.creados += 1
        self.enviadas = []

    def submit(self, fn, *args):
        self.enviadas.append(fn)
        return Future()

    def shutdown(self, wait=True, cancel_futures=False):
        pass


# ── /api/salud tiene que seguir contestando mientras cada lugar espera ───────────────────────
_SALUD = {"peor": 0.0, "n": 0, "parar": False, "errores": 0}


def _vigilar_salud():
    cli = S.app.test_client()
    while not _SALUD["parar"]:
        t0 = time.time()
        try:
            cli.get("/api/salud")
        except Exception:
            _SALUD["errores"] += 1
        _SALUD["peor"] = max(_SALUD["peor"], time.time() - t0)
        _SALUD["n"] += 1
        time.sleep(0.25)


def _medir(nombre, fn):
    """Corre `fn` con el vigilante de /api/salud andando; devuelve (segundos, excepción o None)."""
    _SALUD.update(peor=0.0, n=0, parar=False, errores=0)
    hilo = threading.Thread(target=_vigilar_salud, daemon=True)
    hilo.start()
    t0 = time.time()
    exc = None
    try:
        fn()
    except Exception as e:
        exc = e
    dt = time.time() - t0
    _SALUD["parar"] = True
    hilo.join(timeout=5)
    ok(dt < 25, f"{nombre}: tardó {dt:.0f} s (tope 5 s + un reintento: tendría que ser < 25 s)")
    ok(_SALUD["n"] >= 3 and _SALUD["peor"] < 2.0,
       f"{nombre}: /api/salud no siguió contestando ({_SALUD['n']} respuestas, la peor {_SALUD['peor']:.1f} s)")
    return dt, exc


# ── un molde de mentira: 3 páginas vacías, 6 «talles» ────────────────────────────────────────
_MOLDE = os.path.join(_TMP, "molde_de_prueba.pdf")
_d = fitz.open()
for _ in range(3):
    _d.new_page(width=500, height=500)
_d.save(_MOLDE)
_d.close()
_TALLES = ["XS", "S", "M", "L", "XL", "XXL"]
_EN_PROCESO = []

PD._POOL_FACTORY = lambda max_workers: PoolQueNoTermina()
PD._MESA_EN_SERIE = lambda *a, **k: (_EN_PROCESO.append("mesa"), [{"mesa": 1}])[1]
PD.buscar_candidatos_mesa = lambda *a, **k: (_EN_PROCESO.append("etiquetas"), (a[1], []))[1]
PD._paginas_de_talles = lambda *a, **k: (_EN_PROCESO.append("paginas"), ({}, {}, {}))[1]

# 1. etiquetas
print("1. la búsqueda de etiquetas")
dt, exc = _medir("etiquetas", lambda: PD.decidir_etiqueta_archivo(_MOLDE, _TALLES, procesos=4))
ok(isinstance(exc, PD.ProcesoNoTermino), f"etiquetas: tendría que fallar con ProcesoNoTermino, dio {type(exc).__name__}: {exc}")
ok("etiquetas" not in _EN_PROCESO, "etiquetas: se buscaron EN ESTE PROCESO (plan B)")
ok(exc is not None and "Volvé a intentarlo" in str(exc), f"etiquetas: el mensaje no es para la pantalla: {exc}")
print(f"  · {dt:.1f} s · {exc}")

# 2. páginas por talle
print("2. las páginas por talle de una mesa")
dt, exc = _medir("páginas", lambda: PD._armar_paginas(_MOLDE, 1, _TALLES, {}, None, 1.0, {}, os.path.join(_TMP, "m1.pdf"), 4, None))
ok(isinstance(exc, PD.ProcesoNoTermino), f"páginas: tendría que fallar con ProcesoNoTermino, dio {type(exc).__name__}: {exc}")
ok("paginas" not in _EN_PROCESO, "páginas: la mesa se armó entera EN ESTE PROCESO (plan B)")
ok(not [f for f in os.listdir(_TMP) if f.startswith("m1.pdf.p")], "páginas: quedaron trozos a medias en el disco")
print(f"  · {dt:.1f} s · {exc}")

# 3. una mesa por proceso
print("3. el desplegado, una mesa por proceso")
dt, exc = _medir("desplegado", lambda: PD._desplegar_molde_sin_candado(_MOLDE, _TALLES, None, 4, True, True, 3, [1, 2, 3], {}))
ok(isinstance(exc, PD.ProcesoNoTermino), f"desplegado: tendría que fallar con ProcesoNoTermino, dio {type(exc).__name__}: {exc}")
ok("mesa" not in _EN_PROCESO, "desplegado: alguna mesa se armó EN ESTE PROCESO (plan B)")
print(f"  · {dt:.1f} s · {exc}")


# 4. los SVG de las bases de la previa
class _DocFalso:
    def tobytes(self):
        return b"%PDF-1.4"

    def __getitem__(self, i):
        _EN_PROCESO.append("svg_base")
        return self

    def get_svg_image(self):
        return "<svg/>"


print("4. los SVG de las bases (previa)")
_bases = [{"id": 1}, {"id": 2}, {"id": 3}]
_res = {}
dt, exc = _medir("svg bases", lambda: _res.update(HP.svgs_de_bases(_bases, lambda b: _DocFalso(), procesos=PoolQueNoTermina())))
ok(exc is None, f"svg bases: la previa es best-effort, no tendría que reventar: {type(exc).__name__}: {exc}")
ok(len(_res) == 3 and all(v is None for v in _res.values()), f"svg bases: tendría que devolver None por base, dio {_res}")
ok("svg_base" not in _EN_PROCESO, "svg bases: alguna base se convirtió EN ESTE PROCESO (plan B)")
print(f"  · {dt:.1f} s · {len(_res)} bases sin SVG, ninguna convertida acá")

# 5. los SVG de las piezas del Arte
print("5. los SVG de las piezas (servidor)")
_pool_falso = PoolQueNoTermina()
S._get_render_pool = lambda: _pool_falso
_descartes = []
S._descartar_render_pool = lambda: _descartes.append(1)
_res5 = []
dt, exc = _medir("svg piezas", lambda: _res5.extend(S._svgs_de_piezas([{"doc": _DocFalso()}, {"doc": _DocFalso()}])))
ok(exc is None, f"svg piezas: no tendría que reventar: {type(exc).__name__}: {exc}")
ok(_res5 == [None, None], f"svg piezas: tendría que dar [None, None], dio {_res5}")
ok("svg_base" not in _EN_PROCESO, "svg piezas: alguna se convirtió EN ESTE PROCESO (plan B)")
ok(bool(_descartes), "svg piezas: el pool que no contesta tendría que descartarse")
print(f"  · {dt:.1f} s · sin SVG, pool descartado")

# 6. el pre-dibujo de las mesas
print("6. el pre-dibujo de los recortes de las mesas")
S._dibujar_una_mesa = lambda t: (_EN_PROCESO.append("mesa_img"), (t[1], t[2], None))[1]
os.makedirs(os.path.join(os.environ["TIZADA_TRABAJOS"], "t1"), exist_ok=True)
_res6 = []
dt, exc = _medir("pre-dibujo", lambda: _res6.extend(S._predibujar_mesas("t1", [{"archivo": "a.pdf", "paginas": 2}], None, 800, "x")))
ok(exc is None, f"pre-dibujo: no tendría que reventar: {type(exc).__name__}: {exc}")
ok("mesa_img" not in _EN_PROCESO, "pre-dibujo: alguna mesa se dibujó EN ESTE PROCESO (plan B)")
ok(_res6 and len(_res6[1]) == 2 and all("sin pre-dibujar" in e for e in _res6[1]),
   f"pre-dibujo: las 2 tendrían que quedar anotadas como «sin pre-dibujar», dio {_res6}")
print(f"  · {dt:.1f} s · {_res6}")

# 7. el cupo global
print("7. el cupo global de procesos")
PR._CUPO.update(total=2, usado=0, quien={})
_p1 = PR.pool(3, que="molde A")
ok(getattr(_p1, "_lugares", 0) == 1, f"con cupo 2 el primer molde toma la MITAD (1), tomó {getattr(_p1, '_lugares', 0)}")
_t0 = time.time()
_p2 = PR.pool(3, que="molde B")
ok(getattr(_p2, "_lugares", 0) == 1 and time.time() - _t0 < 1, "el segundo molde tendría que arrancar AL INSTANTE con el otro lugar")
ok(PR.cupo_usado() == 2, f"dos moldes a la vez ocupan los 2 lugares, ocupan {PR.cupo_usado()}")
_esperas = []
_t0 = time.time()
try:
    PR.pool(1, que="molde C", al_esperar=lambda: _esperas.append(1))
    ok(False, "con el cupo LLENO el tercero tendría que fallar con SinLugar")
except PR.SinLugar as e:
    ok(4 <= time.time() - _t0 < 15, f"SinLugar tendría que llegar a los ~5 s, llegó a los {time.time() - _t0:.0f} s")
    ok("molde A" in str(e) and "molde B" in str(e), f"el mensaje tendría que decir quién ocupa el cupo: {e}")
ok(_esperas == [1], "el que espera tendría que avisar (al_esperar) una vez")
_p1.shutdown(wait=False)
ok(PR.cupo_usado() == 1, f"al apagar un pool vuelve su lugar, quedó {PR.cupo_usado()}")
PR.descartar(_p2)
ok(PR.cupo_usado() == 0, f"`descartar` también devuelve el lugar, quedó {PR.cupo_usado()}")
PR._CUPO.update(total=11, usado=0, quien={})
_p3 = PR.pool(11, que="molde D")
ok(getattr(_p3, "_lugares", 0) == 6, f"con cupo 11 un molde toma a lo sumo 6, tomó {getattr(_p3, '_lugares', 0)}")
_p4 = PR.pool(11, que="molde E")
ok(getattr(_p4, "_lugares", 0) == 5, f"y el segundo se lleva los otros 5, se llevó {getattr(_p4, '_lugares', 0)}")
_p3.shutdown(wait=False); _p4.shutdown(wait=False)
print("  · cupo 2: dos moldes a la vez con 1 proceso cada uno; el tercero espera y avisa; cupo 11: 6 + 5")

# ── el texto: no vuelve el reflejo ──────────────────────────────────────────────────────────
import re  # noqa: E402
_reflejos = []
for _f in ("piezas_con_diseno.py", "hoja_pike.py", "servidor.py", "aplanar_rip.py", "motor_pedido.py"):
    _en_doc = False
    with open(os.path.join(_AQUI, _f), encoding="utf-8") as fh:
        for i, ln in enumerate(fh, 1):
            if ln.count('"""') % 2 == 1:          # entra o sale de un docstring
                _en_doc = not _en_doc
                continue
            if _en_doc or ln.lstrip().startswith("#"):
                continue
            if re.search(r"sigo en serie|las hago en serie|dibujo en el server|leo en el server|entera acá", ln):
                _reflejos.append(f"{_f}:{i}")
ok(not _reflejos, f"volvió el reflejo «sigo en serie» en el código: {_reflejos}")

print()
if FALLOS:
    print(f"FALLÓ: {len(FALLOS)}")
    for f in FALLOS:
        print(" -", f)
    sys.exit(1)
print("OK: ningún plan B hace el trabajo adentro del servidor; /api/salud contestó siempre")
