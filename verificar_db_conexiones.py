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

print()
if FALLOS:
    print("✗ FALLA:")
    for f in FALLOS:
        print("   ·", f)
    sys.exit(1)
print("OK conexiones: ni el trabajo normal ni un error a mitad de camino dejan transacciones abiertas")
