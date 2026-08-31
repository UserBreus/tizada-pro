# -*- coding: utf-8 -*-
"""CONTRATO DE LA COLUMNA «CANTIDAD» — `py verificar_cantidad.py`

La regla (pedido del usuario 2026-08-26): la columna **multiplica la fila**. Si una fila dice
«M · pepe · 12 · cantidad 5», la tizada tiene que armar **5 prendas iguales**.

Lo que se verifica, con la función REAL que traduce la planilla a prendas (`_traducir_prendas`):

  1. Cantidad 5 → 5 prendas, y las 5 con los MISMOS datos (talle, nombre, número).
  2. Sin la columna, o vacía, o basura → **1** (exactamente como antes de que existiera).
  3. **Sin tope**: 250 → 250 prendas (decisión del usuario; el sistema no lo frena).
  4. La cantidad **no se estampa**: no aparece en la personalización de la prenda.
  5. Las prendas repetidas son copias INDEPENDIENTES (tocar una no toca a las otras).
  6. Un template viejo —sin la columna guardada— igual la tiene (`_con_cantidad`).

⚠️ Sólo usa objetos en memoria: no toca la base, ni el catálogo, ni los datos del usuario.
"""
import os
import sys
import types

sys.stdout.reconfigure(encoding="utf-8")
_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")   # sin usuarios: import limpio

import servidor as S   # noqa: E402

FALLOS = []


def ok(cond, msg):
    print(("  OK    " if cond else "  FALLA ") + msg)
    if not cond:
        FALLOS.append(msg)


COLS = [
    {"id": "talle", "label": "Talle", "role": "talle"},
    {"id": "nombre", "label": "Nombre", "role": "nombre"},
    {"id": "numero", "label": "Número", "role": "numero"},
    {"id": "cantidad", "label": "Cantidad", "role": "cantidad", "tipo": "numero", "mostrar": "boton"},
]
CAT = {"plantillas_planillas": [{"id": "tpl_prueba", "columnas": COLS}], "productos": []}
PROD = {"id": "prod_prueba", "planilla_template_id": "tpl_prueba"}


def prendas(filas, cols=COLS):
    cat = {"plantillas_planillas": [{"id": "tpl_prueba", "columnas": cols}], "productos": []}
    return S._traducir_prendas(filas, PROD, cat)


# ── 1. La fila se repite ────────────────────────────────────────────────────────────────────
fila = {"talle": "M", "nombre": "pepe", "numero": "12", "cantidad": "5"}
out = prendas([fila])
ok(len(out) == 5, f"cantidad 5 → 5 prendas (salieron {len(out)})")
ok(all(p.get("talle") == "M" for p in out), "las 5 con el mismo talle")
ok(all(str(p.get("nombre")) == "pepe" for p in out), "las 5 con el mismo nombre")
ok(all(str(p.get("numero")) == "12" for p in out), "las 5 con el mismo número")
print(f"    → {[ (p.get('talle'), p.get('nombre'), p.get('numero')) for p in out[:2] ]} …")

# ── 2. Sin cantidad = 1 (nada cambia respecto de antes) ─────────────────────────────────────
for etiqueta, f in [("sin la clave", {"talle": "M", "nombre": "a", "numero": "1"}),
                    ("vacía", {"talle": "M", "cantidad": ""}),
                    ("basura", {"talle": "M", "cantidad": "abc"}),
                    ("cero", {"talle": "M", "cantidad": "0"}),
                    ("negativa", {"talle": "M", "cantidad": "-3"})]:
    n = len(prendas([f]))
    ok(n == 1, f"cantidad {etiqueta} → 1 prenda (salieron {n})")

# …y una planilla SIN la columna se comporta igual que siempre
_sin = [c for c in COLS if c.get("role") != "cantidad"]
n = len(prendas([{"talle": "M", "nombre": "a", "cantidad": "9"}], cols=_sin))
ok(n == 9, f"la columna se agrega sola aunque el template no la tenga guardada (salieron {n})")

# ── 3. SIN TOPE (decisión del usuario) ──────────────────────────────────────────────────────
n = len(prendas([{"talle": "M", "cantidad": "250"}]))
ok(n == 250, f"250 → 250 prendas, sin tope (salieron {n})")

# ── 4. La cantidad NO se estampa ────────────────────────────────────────────────────────────
p0 = prendas([fila])[0]
_pers = p0.get("personalizacion") or {}
ok("Cantidad" not in _pers and "cantidad" not in _pers,
   f"la cantidad no viaja en la personalización ({sorted(_pers)})")
ok(str(_pers.get("Nombre", _pers.get("nombre", ""))) == "pepe", "el nombre sí viaja")

# ── 5. Copias INDEPENDIENTES ────────────────────────────────────────────────────────────────
out = prendas([fila])
out[0]["personalizacion"]["Nombre"] = "OTRO"
out[0]["talle"] = "XXL"
ok(out[1].get("talle") == "M", "cambiar una prenda no cambia a las otras (talle)")
ok(out[1]["personalizacion"].get("Nombre", out[1]["personalizacion"].get("nombre")) != "OTRO",
   "cambiar una prenda no cambia a las otras (personalización)")

# ── 6. Varias filas conviven ────────────────────────────────────────────────────────────────
out = prendas([{"talle": "S", "nombre": "ana", "cantidad": "2"},
               {"talle": "L", "nombre": "juan", "cantidad": "3"},
               {"talle": "M", "nombre": "solo"}])
ok(len(out) == 6, f"2 + 3 + 1 = 6 prendas (salieron {len(out)})")
ok([p["talle"] for p in out] == ["S", "S", "L", "L", "L", "M"],
   f"salen en orden y agrupadas por fila ({[p['talle'] for p in out]})")

# ── 7. `_con_cantidad` no duplica ni pisa lo configurado ────────────────────────────────────
c1 = S._con_cantidad([{"id": "talle", "role": "talle"}])
ok(sum(1 for c in c1 if c.get("role") == "cantidad") == 1, "se agrega UNA sola columna cantidad")
c2 = S._con_cantidad(c1)
ok(sum(1 for c in c2 if c.get("role") == "cantidad") == 1, "aplicarla dos veces no la duplica")
_conf = S._con_cantidad([{"id": "cantidad", "role": "cantidad", "label": "Cant.", "mostrar": "siempre"}])
ok(_conf[0].get("mostrar") == "siempre" and _conf[0].get("label") == "Cant.",
   "respeta la configuración guardada (posición, nombre y modo de mostrar)")

print()
if FALLOS:
    print("✗ FALLA:")
    for f in FALLOS:
        print("   ·", f)
    sys.exit(1)
print("OK cantidad: la fila se multiplica, sin tope, y sin la columna todo sigue igual")
