# -*- coding: utf-8 -*-
"""
CONTRATO: UNA TIZADA SE PUEDE PARAR, Y LOS TRABAJOS NO SE ACUMULAN — `py verificar_trabajos_ciclo.py`.

Cada generación queda anotada en memoria y la pantalla la sondea hasta que está lista. Eso traía
tres agujeros, los tres invisibles hasta que molestaban:

  1. **No se podía cancelar.** El usuario cerraba la pestaña o cambiaba de molde y el servidor
     seguía armando la tizada entera —minutos de CPU, el aplanado para el RIP, la ficha técnica—
     para un pedido que ya no le importaba a nadie. Y cada clic largaba una generación más.
  2. **No se podaba nada.** Cada resultado (con su lista de hojas y sus validaciones) se guardaba
     hasta reiniciar el servidor.
  3. **Un trabajo que ya no existe no se distinguía de uno lento.** La pantalla guarda el pedido en
     curso y lo retoma al recargar: si el servidor se reinició en el medio, el sondeo se quedaba
     dando vueltas para siempre o dejaba la tarjeta muda.

La cancelación se comprueba en el AVISO DE PROGRESO y no en cualquier lado: ahí la generación está
entre dos fases, con lo anterior ya escrito. Cortar a mitad de un `save` dejaría un PDF a medias.

⚠️ No toca datos del usuario ni la base (el módulo `db` se reemplaza antes de importar `servidor`).
"""
import os
import sys
import tempfile
import threading
import time
import types

_TMP = tempfile.mkdtemp(prefix="verif_trab_")
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
S._USUARIOS_ON = False          # el guardia de sesión no es lo que se está probando acá
C = S.app.test_client()
FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK    " if cond else "  FALLA ") + msg)


print("1) Un trabajo que ya no existe se DICE, no se sondea para siempre")
r = C.get("/api/trabajo/no-existe-este")
d = r.get_json()
ok(r.status_code == 404, "pedir un trabajo que no está da 404")
ok(d.get("estado") == "desconocido",
   f"y la respuesta trae un estado que la pantalla entiende (trajo: {d.get('estado')})")
ok(bool(d.get("motivo")), "con el motivo en castellano, para mostrarlo tal cual")

print("\n2) La poda saca los terminados viejos y NO toca lo que está corriendo")
S.trabajos.clear()
ahora = time.time()
S.trabajos["viejo_listo"] = {"estado": "listo", "creado": ahora - 7 * 3600, "cancelar": None}
S.trabajos["viejo_error"] = {"estado": "error", "creado": ahora - 9 * 3600, "cancelar": None}
S.trabajos["viejo_generando"] = {"estado": "generando", "creado": ahora - 9 * 3600, "cancelar": None}
S.trabajos["nuevo_listo"] = {"estado": "listo", "creado": ahora, "cancelar": None}
S._podar_trabajos()
ok("viejo_listo" not in S.trabajos, "un trabajo TERMINADO de hace 7 h se va")
ok("viejo_error" not in S.trabajos, "uno con error también")
ok("viejo_generando" in S.trabajos,
   "🔴 pero uno que TODAVÍA SE ESTÁ ARMANDO se queda (perderlo dejaría a la pantalla sondeando al vacío)")
ok("nuevo_listo" in S.trabajos, "y el recién terminado se queda (el usuario lo está mirando)")

S.trabajos.clear()
for i in range(S._TRABAJOS_VIVOS + 30):
    S.trabajos[f"t{i}"] = {"estado": "listo", "creado": ahora - (S._TRABAJOS_VIVOS + 30 - i),
                           "cancelar": None}
S._podar_trabajos()
ok(len(S.trabajos) == S._TRABAJOS_VIVOS,
   f"pasados {S._TRABAJOS_VIVOS} terminados se sacan los más viejos (quedaron {len(S.trabajos)})")
ok("t0" not in S.trabajos and f"t{S._TRABAJOS_VIVOS + 29}" in S.trabajos,
   "se van los más viejos, no los últimos")

print("\n3) Cancelar de verdad para la generación (en el aviso de progreso)")
S.trabajos.clear()
tid = "trabajo_de_prueba"
salida = os.path.join(_TMP, "trabajos", tid)
os.makedirs(salida, exist_ok=True)
with open(os.path.join(salida, "algo.pdf"), "wb") as f:
    f.write(b"%PDF-1.6\n")
S._nuevo_trabajo(tid, producto_id="pid", producto_nombre="Prueba")
S.trabajos[tid]["estado"] = "generando"
fases = {"n": 0}
termino = threading.Event()


def _generacion_larga():
    """Imita al motor: avisa el progreso una y otra vez. Es ahí donde tiene que enterarse."""
    try:
        for i in range(10000):
            S._cancelado(tid)
            S.trabajos[tid]["progreso"] = f"paso: {i}"
            fases["n"] = i
            time.sleep(0.01)
    except S._TrabajoCancelado:
        S._marcar_cancelado(tid, salida)
    finally:
        termino.set()


threading.Thread(target=_generacion_larga, daemon=True).start()
time.sleep(0.2)
ok(fases["n"] > 0, "la generación arrancó")
r = C.post(f"/api/trabajo/{tid}/cancelar")
ok(r.status_code == 200, f"cancelar contesta 200 (contestó {r.status_code})")
ok(termino.wait(5), "la generación se entera y larga (no sigue hasta el final)")
ok(S.trabajos[tid]["estado"] == "cancelado",
   f"el trabajo queda como «cancelado» (quedó: {S.trabajos[tid]['estado']})")
ok(not os.path.exists(salida), "y se borra lo que alcanzó a escribir (es salida del sistema)")

print("\n4) Cancelar dos veces, o algo ya terminado, no rompe nada")
r = C.post(f"/api/trabajo/{tid}/cancelar")
ok(r.status_code == 409, f"cancelar algo ya cancelado avisa 409 (contestó {r.status_code})")
ok(r.get_json().get("estado") == "cancelado", "y dice en qué estado está")
r = C.post("/api/trabajo/no-existe-este/cancelar")
ok(r.status_code == 404, "cancelar un trabajo que no existe da 404")

print("\n5) El estado del trabajo viaja completo (y sin lo que no puede viajar)")
r = C.get(f"/api/trabajo/{tid}")
d = r.get_json()
ok(r.status_code == 200 and d.get("estado") == "cancelado", "el estado se puede consultar")
ok("cancelar" not in d, "el aviso de cancelación (objeto de Python) NO viaja al navegador")
ok("creado" in d, "y sí viaja cuándo se creó")

print("\n6) La pantalla mira el resultado del pedido, no sólo el contenido")
_app = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "src", "App.jsx"),
            encoding="utf-8").read()
ok(_app.count("if (!res.ok)") >= 1 and "El trabajo ya no existe." in _app,
   "los sondeos cortan y explican cuando el trabajo dejó de existir")
ok("/cancelar`" in _app or "/cancelar'" in _app, "hay un botón que llama a cancelar")
ok("rutaApi(`/api/trabajo/" in _app,
   "🔴 y los sondeos pasan por `rutaApi` (sin eso fallan en el servidor publicado, que va bajo un prefijo)")

print()
if FALLOS:
    print(f"FALLARON {len(FALLOS)}:")
    for f in FALLOS:
        print("  -", f)
    sys.exit(1)
print("TODO OK: se puede parar, se poda, y un trabajo que no está se dice")
