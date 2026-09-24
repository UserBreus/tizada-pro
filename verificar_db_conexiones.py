# -*- coding: utf-8 -*-
"""CONTRATO DE LAS CONEXIONES A LA BASE — `py verificar_db_conexiones.py`

Lo que se prueba es que **no queden transacciones abiertas «fantasma»**: una sesión dormida con
una transacción sin cerrar deja bloqueos tomados y hace esperar (o fallar) al resto.

Se prueba con la base REAL pero **sin escribir nada**: sólo SELECTs y una operación que FALLA a
propósito dentro de una transacción, para ver que el rollback y el cierre ocurren igual.
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)

import db  # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)


def _sesiones():
    """{sesiones_de_usuario, dormidas_con_transaccion} — None si la base no deja mirar las DMVs."""
    try:
        r = db.filas("""
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN s.open_transaction_count > 0 AND s.status = 'sleeping' THEN 1 ELSE 0 END) AS fantasmas
            FROM sys.dm_exec_sessions s WHERE s.is_user_process = 1""")
        return (r[0]["total"], r[0]["fantasmas"] or 0)
    except Exception as e:
        print("  (sin permiso para ver las sesiones:", str(e)[:80], ")")
        return None


print("base:", db.DB_SERVER, "/", db.DB_NAME)
_ini = _sesiones()
if _ini:
    print(f"  al empezar: {_ini[0]} sesión/es de usuario · {_ini[1]} dormida/s con transacción abierta")
    ok(_ini[1] == 0, f"YA hay {_ini[1]} transacción/es fantasma antes de empezar")

# ── 1. Trabajo normal: muchas operaciones seguidas no dejan sesiones colgadas ────────────────
for _ in range(30):
    db.filas("SELECT TOP 1 name FROM sys.tables")
_desp = _sesiones()
if _ini and _desp:
    ok(_desp[1] == 0, f"tras 30 consultas quedaron {_desp[1]} transacción/es fantasma")
    # +1 tolerancia: la propia sesión de esta prueba
    ok(_desp[0] <= _ini[0] + 1, f"las sesiones crecieron de {_ini[0]} a {_desp[0]}: hay conexiones que no se cierran")
    print(f"  tras 30 consultas: {_desp[0]} sesión/es · {_desp[1]} fantasma/s")

# ── 2. 🔴 LO QUE IMPORTA: una operación que FALLA no puede dejar la transacción abierta ──────
try:
    with db.cursor() as cur:                      # commit=True: abre transacción de escritura
        cur.execute("SELECT 1")
        raise RuntimeError("falla a propósito, en medio de la transacción")
except RuntimeError:
    pass
except Exception as e:                            # el rollback protegido no debe tapar el error
    FALLOS.append(f"la excepción original se perdió: {type(e).__name__}: {e}")
_tras_error = _sesiones()
if _tras_error:
    ok(_tras_error[1] == 0, f"una operación que falla dejó {_tras_error[1]} transacción/es abierta/s")
    print(f"  tras un error en medio de una transacción: {_tras_error[1]} fantasma/s")

# ── 3. El error REAL llega arriba (no lo tapa el rollback) ───────────────────────────────────
_msg = None
try:
    with db.cursor() as cur:
        cur.execute("SELECT * FROM una_tabla_que_no_existe_zzz")
except Exception as e:
    _msg = str(e)
ok(_msg and ("una_tabla_que_no_existe_zzz" in _msg or "Invalid object name" in _msg),
   f"el error real no llegó arriba: {(_msg or '')[:90]}")
print("  el error de SQL llega tal cual a quien llamó ✓")

# ── 4. Nadie bloqueado ──────────────────────────────────────────────────────────────────────
try:
    _bl = db.filas("SELECT COUNT(*) AS n FROM sys.dm_exec_requests WHERE blocking_session_id <> 0")
    ok(_bl[0]["n"] == 0, f"hay {_bl[0]['n']} petición/es bloqueada/s por otra sesión")
    print(f"  peticiones bloqueadas: {_bl[0]['n']}")
except Exception:
    pass

# ── 5. UNA CONSULTA QUE NO VUELVE TIENE TECHO (y al cortar no deja nada abierto) ────────────
# 🔴 Lo que faltaba (2026-09-09): `timeout=10` en `pyodbc.connect` es sólo para CONECTAR. Una vez
# conectado, la consulta esperaba PARA SIEMPRE y el motor tampoco corta la espera por un candado
# (`LOCK_TIMEOUT = -1`). Dos operaciones que se pisan no daban error: dejaban la petición colgada
# con su transacción y su conexión abiertas, tomando candados. No falla, no avisa: se nota porque
# el sistema deja de responder.
import time as _t                                                              # noqa: E402
ok(getattr(db, "TIMEOUT_CONSULTA", 0) > 0,
   "no hay techo de espera para las consultas (`db.TIMEOUT_CONSULTA`)")
_cn = db.conectar()
try:
    ok(getattr(_cn, "timeout", 0) == db.TIMEOUT_CONSULTA,
       f"la conexión no trae el techo puesto (timeout={getattr(_cn, 'timeout', None)})")
finally:
    _cn.close()
# Y que de verdad corte: se baja el techo a 2 s y se pide una espera de 10.
_previo = db.TIMEOUT_CONSULTA
db.TIMEOUT_CONSULTA = 2
_t0, _corto = _t.time(), False
try:
    with db.cursor() as cur:
        cur.execute("WAITFOR DELAY '00:00:10'")     # sólo esperar: no toca ningún dato
except Exception:
    _corto = True
_tardo = _t.time() - _t0
db.TIMEOUT_CONSULTA = _previo
ok(_corto and _tardo < 6, f"una consulta trabada NO se cortó (esperó {_tardo:.1f} s)")
print(f"  una consulta que no vuelve se corta sola a los {_tardo:.1f} s ✓")
_fin = _sesiones()
if _fin:
    ok(_fin[1] == 0, f"tras cortar por techo quedaron {_fin[1]} transacción/es abierta/s")
    print(f"  y al cortar no queda nada abierto: {_fin[1]} fantasma/s")

# ── 6. 🔴 LEER NO DEJA UNA TRANSACCIÓN VIVA EN LAS CONEXIONES QUE QUEDAN EN EL POOL ──────────
# Lo que se vio en el servidor publicado (2026-09-22): sesiones dormidas con una transacción abierta
# de horas, todas con un SELECT. Con `autocommit=False` el primer SELECT abre la transacción; como
# la lectura no confirmaba, la conexión volvía al pool del driver con ella abierta. Las pruebas de
# arriba NO lo veían: `_sesiones()` toma del pool justo esa conexión (el driver la resetea antes de
# usarla) y la fantasma desaparece antes de medirla. Acá se dejan VARIAS conexiones en el pool a la
# vez (4 lecturas simultáneas) y se mide con una conexión aparte, sólo las de ESTE proceso.
import contextlib as _cl                                                       # noqa: E402
import threading as _th                                                        # noqa: E402
_barrera = _th.Barrier(4)


def _leer_a_la_vez():
    try:
        with db.cursor(commit=False) as cur:          # el camino de `filas()` / `valor()`
            cur.execute("SELECT TOP 1 name FROM sys.tables")
            cur.fetchall()
            _barrera.wait(timeout=20)                 # las 4 conexiones abiertas al mismo tiempo
    except Exception as e:
        FALLOS.append(f"lectura simultánea: {type(e).__name__}: {e}")


_hs = [_th.Thread(target=_leer_a_la_vez) for _ in range(4)]
for _h in _hs:
    _h.start()
for _h in _hs:
    _h.join()
try:
    with _cl.closing(db.conectar(autocommit=True)) as _cm:
        _n = _cm.execute(
            "SELECT COUNT(*) FROM sys.dm_exec_sessions WHERE host_process_id = ? AND session_id <> @@SPID "
            "AND status = 'sleeping' AND open_transaction_count > 0", os.getpid()).fetchone()[0]
    ok(_n == 0, f"tras 4 lecturas quedaron {_n} conexión/es de este proceso dormidas CON transacción abierta")
    print(f"  lecturas en paralelo: {_n} conexión/es dormida/s con transacción (tiene que ser 0)")
except Exception as e:
    print("  (sin permiso para ver las sesiones:", str(e)[:80], ")")

print()
if FALLOS:
    print("✗ FALLA:")
    for f in FALLOS:
        print("   ·", f)
    sys.exit(1)
print("OK conexiones: ni el trabajo normal ni un error a mitad de camino dejan transacciones abiertas")
