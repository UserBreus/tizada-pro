# -*- coding: utf-8 -*-
"""
CONTRATO: EL USUARIO NO ESPERA DETRÁS DE LA PRECARGA — `py verificar_prioridad_visor.py`.

Al armar las piezas del visor hay UN candado (`_PIEZAS_BASE_LOCK`): dibujar dos veces lo mismo en
paralelo sería trabajo al pedo. Pero la PRECARGA (bg) no puede quedarse con ese turno cuando el
usuario (fg) está esperando su dibujo. Eso lo arbitra `_PrioridadVisor`.

Lo que se prueba, y por qué:
  1. El bg **espera** mientras hay un fg, y arranca **apenas** el fg suelta (no hasta 50 ms
     después: antes era un sondeo cada 50 ms, que además gastaba CPU sin hacer nada).
  2. Un fg que **revienta** deja el contador en cero igual. Antes el `+= 1` y el `-= 1` estaban
     separados por un `acquire` bloqueante, sin `try/finally`: si ese hilo moría en el medio, el
     contador quedaba en >0 y **toda** precarga esperaba para siempre a un fg que ya no existía.
  3. Aun con el contador desincronizado a mano, `ceder_bg` **vuelve** al vencer su tope: perder la
     prioridad es aceptable, quedarse clavado no.

⚠️ 🔴 Esto NO toca la generación de la tizada: la tizada nunca puede quedar detrás de un candado
   (changelog 169). Este candado es sólo del armado de piezas del visor.
⚠️ No toca datos del usuario ni la base (el módulo `db` se reemplaza antes de importar).
"""
import os
import sys
import tempfile
import threading
import time
import types

_TMP = tempfile.mkdtemp(prefix="verif_prio_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = "localhost\\NO_EXISTE_ES_UNA_PRUEBA"

_falso = types.ModuleType("db")
_falso.__getattr__ = lambda n: (lambda *a, **k: None)
_falso.get_doc = lambda c, default=None: default
sys.modules["db"] = _falso

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tempfile as _tmp_log, registro as _LOG_PRUEBA   # noqa: E402
_LOG_PRUEBA.usar_carpeta(_tmp_log.mkdtemp(prefix="verif_logs_"))
import servidor as S   # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK    " if cond else "  FALLA ") + msg)


P = S._PrioridadVisor()

print("1) El bg cede el paso mientras hay un usuario esperando")
paso = {"cuando": None}
fg_adentro = threading.Event()
soltar_fg = threading.Event()


def _bg():
    P.ceder_bg(timeout=10)
    paso["cuando"] = time.time()


def _fg():
    with P.fg():
        fg_adentro.set()
        soltar_fg.wait(10)


t_fg = threading.Thread(target=_fg, daemon=True)
t_fg.start()
ok(fg_adentro.wait(5), "el usuario entra y queda contado como «esperando»")
t_bg = threading.Thread(target=_bg, daemon=True)
t_bg.start()
time.sleep(0.3)
ok(paso["cuando"] is None, "la precarga NO pasa mientras el usuario espera")
t0 = time.time()
soltar_fg.set()
t_bg.join(10)
demora = (paso["cuando"] or time.time()) - t0
ok(paso["cuando"] is not None, "la precarga pasa en cuanto el usuario suelta")
ok(demora < 0.05, f"y pasa AL INSTANTE, no en el próximo sondeo ({demora*1000:.0f} ms)")
ok(P.esperando() == 0, "el contador vuelve a cero")

print("\n2) Un usuario cuyo pedido REVIENTA no deja el contador colgado")
try:
    with P.fg():
        raise RuntimeError("falla a propósito, con el turno tomado")
except RuntimeError:
    pass
ok(P.esperando() == 0, "el contador vuelve a cero aunque el pedido falle")
ok(P.ceder_bg(timeout=2) is True, "y la precarga puede pasar (antes esperaba para siempre)")

print("\n3) Red de seguridad: si el contador quedara mal, el bg no se cuelga")
P2 = S._PrioridadVisor()
with P2._cv:
    P2._fg = 1                      # se desincroniza a mano, a propósito
t0 = time.time()
res = P2.ceder_bg(timeout=0.5)
tardo = time.time() - t0
ok(res is False, "avisa que venció el tope (no miente diciendo que pasó)")
ok(0.4 < tardo < 2.0, f"y vuelve en el tiempo del tope, no nunca ({tardo:.2f} s)")

print("\n4) El servidor usa esta prioridad y no el sondeo viejo")
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "servidor.py"),
            encoding="utf-8").read()
ok("_PB_FG_ESPERANDO" not in _src, "no queda nada del contador global viejo")
ok("_PRIO_VISOR.ceder_bg()" in _src, "la precarga cede el paso con la prioridad nueva")
ok("with _PRIO_VISOR.fg():" in _src, "y el usuario se cuenta con el `with` (que baja siempre)")
ok(S._PIEZAS_BASE_LOCK.acquire(timeout=2),
   "el candado del visor queda LIBRE después de todo esto")
S._PIEZAS_BASE_LOCK.release()

print("\n5) 🔴 Si el dibujo REVIENTA, el candado del visor se suelta igual")
# El candado ya no se toma con `with` (hay que contarlo como fg antes de pedirlo), así que
# soltarlo depende de un `finally` escrito a mano: si ese finally faltara, un solo error al
# dibujar dejaría el visor congelado para TODO el mundo hasta reiniciar el servidor.
_archivo = os.path.join(_TMP, "cualquiera.ai")      # `_piezas_base` corta si no existen molde/arte
open(_archivo, "wb").close()
S._ruta_entrada = lambda nombre, pid=None, sub=None: _archivo
S._piezas_base_clave = lambda *a, **k: "clave_que_nunca_esta_en_cache"
S._ruta_datos = lambda nombre, pid=None, sub=None: os.path.join(_TMP, "cache_inexistente")
S._cargar_catalogo = lambda *a, **k: {"productos": [], "plantillas_planillas": [], "reglas_planilla": []}
# `_traducir_prendas` se llama YA con el candado tomado: es el punto donde importa el `finally`.
S._traducir_prendas = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("revienta a propósito"))
_falla = None
try:
    S._piezas_base("pid", "d", "v", "M", {}, {"id": "pid"}, {"Pieza 1": {"M": {}}})
except Exception as e:
    _falla = str(e)
# Que la falla sea LA QUE PLANTAMOS es parte de la prueba: si reventara antes de tomar el
# candado, esta sección no estaría probando nada.
ok(_falla == "revienta a propósito",
   f"el dibujo falla DONDE queríamos, ya con el candado tomado (falló: {_falla})")
ok(S._PIEZAS_BASE_LOCK.acquire(timeout=2),
   "un dibujo que falla NO deja el candado del visor tomado")
S._PIEZAS_BASE_LOCK.release()

print()
if FALLOS:
    print(f"FALLARON {len(FALLOS)}:")
    for f in FALLOS:
        print("  -", f)
    sys.exit(1)
print("TODO OK: el usuario pasa primero y nadie se queda clavado")
