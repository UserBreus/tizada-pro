# -*- coding: utf-8 -*-
"""CONTRATO: LA MESA DE TRABAJO ES LA TELA MENOS UN MARGEN — `py verificar_telas_margen.py`

Regla del usuario (2026-09-11): «que la mesa de trabajo tenga siempre 3 cm menos que el ancho
que tiene la tela, a no ser que le cambien a mano el valor a alguna o algunas telas en
específico; esos 3 cm deben ser configurables».

Lo que se prueba, sobre un catálogo DE MENTIRA (nunca el del usuario):
  1. sin nada configurado, mesa = medida − 3;
  2. el margen configurado manda sobre el 3 (y 0 = la tela entera);
  3. una tela con valor a mano lo usa TAL CUAL, no importa el margen — y queda marcada `manual`;
  4. quitar el valor a mano (None) la devuelve al automático;
  5. cambiar el margen recalcula las telas automáticas y NO toca las puestas a mano;
  6. sin medida del sistema se parte de 180 y también se resta el margen;
  7. la tizada lee `ancho_cm` de `cat['telas']` (`_config_produccion`): lo que sale de acá es
     lo que nestea — no hay otro camino.

⚠️ Sólo LEE el código; no escribe nada en `datos/` ni en la base.
"""
import os
import sys
import types

sys.stdout.reconfigure(encoding="utf-8")
_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")   # sin usuarios: import limpio

import tempfile as _tmp_log, registro as _LOG_PRUEBA   # noqa: E402
_LOG_PRUEBA.usar_carpeta(_tmp_log.mkdtemp(prefix="verif_logs_"))
import servidor as S          # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)


def _mesa(cat, tid):
    return next(t for t in cat["telas"] if str(t["id"]) == str(tid))


API = [{"id": "44", "nombre": "Bandera 1,60", "medida_cm": 160.0},
       {"id": "45", "nombre": "Parisien 1,50", "medida_cm": 150.0},
       {"id": "46", "nombre": "Sin medida", "medida_cm": None}]

# ── 1. sin configurar: medida − 3 ────────────────────────────────────────────────────────────
cat = {}
cat["telas"] = S._telas_merge(cat, API)
ok(S._telas_margen(cat) == 3.0, "el margen por defecto no es 3 cm")
ok(_mesa(cat, 44)["ancho_cm"] == 157.0, f"160 sin configurar tendría que dar 157, dio {_mesa(cat, 44)['ancho_cm']}")
ok(_mesa(cat, 45)["ancho_cm"] == 147.0, "150 sin configurar tendría que dar 147")
ok(not _mesa(cat, 44)["manual"], "una tela sin valor a mano figura como manual")
print(f"  · sin configurar: 160 → {_mesa(cat, 44)['ancho_cm']} · 150 → {_mesa(cat, 45)['ancho_cm']} (margen {S._telas_margen(cat)})")

# ── 2. el margen configurado manda ───────────────────────────────────────────────────────────
S._telas_aplicar_margen(cat, 2)
ok(_mesa(cat, 44)["ancho_cm"] == 158.0, "con margen 2, 160 tendría que dar 158")
S._telas_aplicar_margen(cat, 0)
ok(_mesa(cat, 44)["ancho_cm"] == 160.0, "con margen 0 la mesa tendría que ser la tela entera")
ok(S._telas_aplicar_margen(cat, -5) == 0.0, "un margen negativo tendría que quedar en 0")
print("  · margen 2 → 158 · margen 0 → 160 · negativo → 0")

# ── 3. el valor a mano manda tal cual y queda marcado ────────────────────────────────────────
S._telas_aplicar_margen(cat, 3)
t = S._telas_aplicar_ancho(cat, "44", 152)
ok(t and t["ancho_cm"] == 152.0 and t["manual"], f"el valor a mano no manda: {t}")
S._telas_aplicar_margen(cat, 10)
ok(_mesa(cat, 44)["ancho_cm"] == 152.0, "cambiar el margen pisó un valor puesto a mano")
ok(_mesa(cat, 45)["ancho_cm"] == 140.0, "cambiar el margen no recalculó la tela automática (150 − 10)")
print("  · a mano 152 se mantiene con margen 10; la automática pasa a 140")

# ── 4. quitar el valor a mano = volver al automático ─────────────────────────────────────────
t = S._telas_aplicar_ancho(cat, "44", None)
ok(t and t["ancho_cm"] == 150.0 and not t["manual"], f"quitar el valor a mano no volvió al automático (160 − 10): {t}")
ok("44" not in (cat.get("telas_ancho") or {}), "el valor a mano sigue guardado después de quitarlo")
print("  · quitado el valor a mano → 150 (160 − 10), sin marca")

# ── 5. cambiar el margen no toca lo puesto a mano, y el mínimo es 1 ──────────────────────────
S._telas_aplicar_ancho(cat, "45", 0.2)
ok(_mesa(cat, 45)["ancho_cm"] == 1.0, "una mesa a mano por debajo de 1 cm tendría que quedar en 1")
S._telas_aplicar_ancho(cat, "45", None)

# ── 6. sin medida del sistema: 180 − margen ──────────────────────────────────────────────────
S._telas_aplicar_margen(cat, 3)
ok(_mesa(cat, 46)["ancho_cm"] == 177.0, f"sin medida tendría que partir de 180 − 3 = 177, dio {_mesa(cat, 46)['ancho_cm']}")
print(f"  · sin medida del sistema → {_mesa(cat, 46)['ancho_cm']}")

# ── 7. la tizada lee exactamente esto ────────────────────────────────────────────────────────
import inspect  # noqa: E402
_src = inspect.getsource(S._config_produccion)
ok('cat.get("telas")' in _src and 'ancho_cm' in _src, "`_config_produccion` ya no arma las telas desde `cat['telas'].ancho_cm`")
ok("medida_cm" not in _src, "`_config_produccion` mira `medida_cm`: la tizada usaría la tela entera, no la mesa")
_src_e = inspect.getsource(S.set_tela_ancho)
ok("_telas_aplicar_ancho" in _src_e and 'in (None, "")' in _src_e, "el endpoint del ancho no acepta null para volver al automático")
_src_m = inspect.getsource(S.set_telas_margen)
ok("_telas_aplicar_margen" in _src_m and "_guardar_catalogo" in _src_m, "el endpoint del margen no recalcula y guarda")
print("  · la tizada nestea con `ancho_cm` (la mesa), nunca con la medida")

print()
if FALLOS:
    print("✗ FALLA:")
    for f in FALLOS:
        print("   ·", f)
    sys.exit(1)
print("OK mesa: tela − margen (3 cm configurable); el valor a mano manda y se puede quitar")
