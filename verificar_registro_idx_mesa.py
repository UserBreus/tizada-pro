# -*- coding: utf-8 -*-
"""CONTRATO DEL `idx_mesa` EN LA BASE — `py verificar_registro_idx_mesa.py`

Un molde del CAMINO B (el que trae el diseño adentro) tiene VARIAS mesas, así que los dos índices
de una pieza dejan de coincidir:

  • `pieza_idx` = posición dentro del TALLE. Es la IDENTIDAD (invariante §8.9 del MAPA): con ella
    se resuelven las variables y el puente entre talles.
  • `idx_mesa`  = posición dentro de la MESA. Es la única que sirve para indexar lo que devuelve
    `extraer_piezas_mesa(mesa, talle)`, que son las piezas DE ESA MESA.

En el camino A coinciden (el molde tiene una sola mesa) y por eso nadie los había separado. Con 9
mesas no: si se guardara la posición dentro de la mesa, las 9 piezas tendrían `pieza_idx = 0` y el
mapa `pieza_idx → nombre` se quedaría con UNA — ocho piezas invisibles, sin error.

Lo que se verifica acá es el VIAJE POR LA BASE, que es donde se perdía: el registro no tiene espejo
en disco (`_cargar("registro_producto.json")` lee de MSSQL), así que un `idx_mesa` que no se
persiste se evapora en el primer round-trip y `_armar_base` vuelve a indexar por `pieza_idx` →
pieza equivocada, o `IndexError` en las mesas de una sola pieza.

🔴 ESTE CONTRATO ESCRIBE EN LA BASE REAL (es la misma que la del taller). Por eso:
  - trabaja SÓLO sobre un `legacy_pid` propio, único, creado por ESTA corrida;
  - lo borra al final por ESE id exacto, nunca «los que sobran» ni por nombre;
  - no toca ningún otro producto, y lo comprueba (cuenta los productos antes y después).
"""
import os
import sys
import uuid

sys.stdout.reconfigure(encoding="utf-8")
_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)

import db  # noqa: E402

FALLOS = []
PID = "test_idxmesa_" + uuid.uuid4().hex[:10]     # el id de ESTA corrida, el único que se borra


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)


def _piezas(n):
    return [{"id": i + 1, "clave": f"Pieza {i + 1}", "nombre_generico": "Pieza"} for i in range(n)]


def _reg(n_piezas, talles, con_idx_mesa):
    """Registro sintético: n piezas × talles. Camino B = una pieza por mesa, así que `pieza_idx`
    es el correlativo del talle (0..n-1) y `idx_mesa` es SIEMPRE 0 (única pieza de su mesa).
    Justamente ahí es donde se nota si se perdió: los dos números son distintos."""
    reg = {}
    for i in range(n_piezas):
        por_t = {}
        for t in talles:
            inf = {"mesa": i + 1, "pieza_idx": i, "w_cm": 30.0 + i, "h_cm": 40.0 + i,
                   "bbox_mu": [0, 0, 100, 200], "ancla": {"x": 1.0, "y": 2.0, "size": 3.0}}
            if con_idx_mesa:
                inf["idx_mesa"] = 0
            por_t[t] = inf
        reg[f"Pieza {i + 1}"] = por_t
    return reg


print("base:", db.DB_SERVER, "/", db.DB_NAME)
print("pid de prueba:", PID)

_prod_antes = db.valor("SELECT COUNT(*) FROM producto")
_col = db.valor("SELECT COL_LENGTH('dbo.pieza_talle','idx_mesa')")
print(f"  columna idx_mesa: {'SÍ' if _col else 'NO'} · productos en la base: {_prod_antes}")

try:
    # ── 1. CAMINO B: el idx_mesa sobrevive al viaje ────────────────────────────────────
    TALLES = ["XS", "S", "M", "L", "XL"]
    db.guardar_registro(PID, _piezas(9), _reg(9, TALLES, con_idx_mesa=True))
    leido = db.leer_registro(PID)
    ok(leido is not None, "1. el registro no volvió de la base")
    if leido:
        ok(len(leido) == 9, f"1. volvieron {len(leido)} piezas, esperaba 9")
        _falta = [f"{nom}/{t}" for nom, por_t in leido.items() for t in por_t
                  if "idx_mesa" not in por_t[t]]
        ok(not _falta, f"1. {len(_falta)} entradas volvieron SIN idx_mesa (ej. {_falta[:3]})")
        _mal = [f"{nom}/{t}" for nom, por_t in leido.items() for t in por_t
                if por_t[t].get("idx_mesa") != 0]
        ok(not _mal, f"1. {len(_mal)} entradas con idx_mesa equivocado (ej. {_mal[:3]})")
        # El otro índice tiene que seguir siendo el del TALLE, no el de la mesa
        _pi = {por_t["M"]["pieza_idx"] for por_t in leido.values() if "M" in por_t}
        ok(_pi == set(range(9)), f"1. los pieza_idx del talle M son {sorted(_pi)}, esperaba 0..8")
        ok(all(len(por_t) == len(TALLES) for por_t in leido.values()),
           "1. alguna pieza perdió talles en el viaje")
        print(f"  1. OK — 9 piezas × {len(TALLES)} talles con su idx_mesa, y pieza_idx 0..8 intacto")

    # ── 2. CAMINO A: vuelve SIN LA CLAVE (no con None) ─────────────────────────────────
    # 🔴 El motor hace `_pm[info.get("idx_mesa", info["pieza_idx"])]`: `.get` cae al default sólo
    # si la clave NO ESTÁ. Un `"idx_mesa": None` haría `_pm[None]` → TypeError en TODOS los moldes
    # del camino A. Por eso no alcanza con que «sea falsy»: la clave tiene que faltar.
    db.guardar_registro(PID, _piezas(3), _reg(3, TALLES, con_idx_mesa=False))
    leido_a = db.leer_registro(PID) or {}
    _con = [f"{nom}/{t}" for nom, por_t in leido_a.items() for t in por_t if "idx_mesa" in por_t[t]]
    ok(not _con, f"2. un registro del camino A volvió CON la clave idx_mesa ({_con[:3]})")
    _inf = (leido_a.get("Pieza 1") or {}).get("M") or {}
    ok(_inf.get("idx_mesa", _inf.get("pieza_idx")) == 0,
       "2. el fallback `get(idx_mesa, pieza_idx)` no devuelve el pieza_idx en un molde del camino A")
    print("  2. OK — el camino A vuelve sin la clave y el fallback del motor sigue funcionando")

    # ── 3. Base SIN la columna: degrada, no revienta ───────────────────────────────────
    # Un servidor publicado puede correr con el esquema viejo (el arranque AVISA que faltan cosas,
    # no las aplica). Con la columna ausente el sistema tiene que seguir andando como hoy.
    _real = db._PT_IDX_MESA
    try:
        db._PT_IDX_MESA = False
        db.guardar_registro(PID, _piezas(2), _reg(2, ["M"], con_idx_mesa=True))
        _sin = db.leer_registro(PID) or {}
        ok(len(_sin) == 2, "3. sin la columna no se pudo guardar/leer el registro")
        ok(all("idx_mesa" not in inf for por_t in _sin.values() for inf in por_t.values()),
           "3. sin la columna igual apareció un idx_mesa")
        print("  3. OK — sin la columna guarda y lee igual, sólo que sin idx_mesa (camino A)")
    except Exception as e:
        FALLOS.append(f"3. sin la columna idx_mesa el guardado REVIENTA: {type(e).__name__}: {e}")
    finally:
        db._PT_IDX_MESA = _real

finally:
    # ── LIMPIEZA: sólo el pid de ESTA corrida, por su id exacto ────────────────────────
    _id = db.valor("SELECT id FROM producto WHERE legacy_id=?", PID)
    print(f"  limpieza: borrando SOLO el producto de prueba (legacy_id={PID}, id={_id})")
    if _id is not None:
        db.borrar_piezas_molde(PID)
        db.ejecutar("DELETE FROM producto WHERE id=? AND legacy_id=?", _id, PID)

_queda = db.valor("SELECT COUNT(*) FROM producto WHERE legacy_id=?", PID)
ok(_queda == 0, f"la limpieza dejó {_queda} producto(s) de prueba en la base")
_prod_despues = db.valor("SELECT COUNT(*) FROM producto")
ok(_prod_despues == _prod_antes,
   f"la corrida cambió la cantidad de productos: {_prod_antes} → {_prod_despues} (¡tocó algo ajeno!)")

print()
if FALLOS:
    print(f"❌ {len(FALLOS)} FALLO(S):")
    for f in FALLOS:
        print("   -", f)
    sys.exit(1)
print("✅ CONTRATO VERDE — el idx_mesa sobrevive a la base y el camino A no se entera")
