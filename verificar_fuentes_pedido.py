# -*- coding: utf-8 -*-
"""CONTRATO DE LAS FUENTES DEL PEDIDO — `py verificar_fuentes_pedido.py`

Lo que se prueba es la regla del usuario (2026-08-21):

  · Si el arte trae una tipografía que **está** en el catálogo, se usa **ESA**. Punto.
  · Si eligió un reemplazo, vale **para ese pedido** y viaja en el request — **nunca** sale del
    molde. Un molde con `fuentes_reemplazo` guardado (los que quedaron de antes) **se ignora**.
  · Si la tipografía no está en ningún lado, se estampa con la predeterminada (Anton Regular) y se
    avisa; no se elige "cualquiera".

El caso real que lo motivó: el molde «Camiseta de futbol» tenía guardado
`{'ClubAmerica2021-2022': 'Hawken Personal Use Only'}` y la ClubAmerica **estaba instalada**: el
arte se estampaba con Hawken y no había forma de volver.

⚠️ Sólo LEE (catálogo de fuentes del sistema); no escribe nada.
"""
import os
import sys
import types

sys.stdout.reconfigure(encoding="utf-8")
_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")   # sin usuarios: import limpio

# 🔴 El registro de la prueba va a un temporal, y se engancha ANTES de importar `servidor`
# (que espeja la consola al importarse): un test no puede ensuciar el registro del sistema
# de verdad — si no, mañana alguien investiga una falla que provocó una prueba.
import tempfile as _tmp_log, registro as _LOG_PRUEBA   # noqa: E402
_LOG_PRUEBA.usar_carpeta(_tmp_log.mkdtemp(prefix="verif_logs_"))
import servidor as S          # noqa: E402
import motor_pedido as MP     # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)


CAT = MP.catalogo_fuentes(S.FUENTES)
_internos = {i["interno"]: r for r, i in CAT.items()}
print(f"catálogo del sistema: {len(CAT)} tipografías")

# ── 1. La fuente del arte que SÍ está en el catálogo se resuelve a ella ──────────────────────
# (se prueba con las que hay de verdad, no con nombres inventados)
_casos = [(i["interno"], r) for r, i in CAT.items()]
_malos = []
for interno, ruta in _casos:
    got = MP.resolver_fuente(interno, {"carpetas": [S.FUENTES], "alias": {}})
    if not got or os.path.normcase(got) != os.path.normcase(ruta):
        _malos.append((interno, os.path.basename(got) if got else None))
ok(not _malos, f"tipografías del catálogo que NO resuelven a su propio archivo: {_malos[:4]}")
print(f"  · {len(_casos) - len(_malos)}/{len(_casos)} resuelven exactamente a su archivo")

# ── 2. El reemplazo del PEDIDO manda… y sin él vuelve la original ────────────────────────────
if len(_casos) >= 2:
    (n_a, r_a), (n_b, r_b) = _casos[0], _casos[1]
    con = MP.resolver_fuente(n_a, {"carpetas": [S.FUENTES], "alias": {n_a: n_b}})
    ok(con and os.path.normcase(con) == os.path.normcase(r_b),
       "el reemplazo del pedido no se aplicó")
    sin = MP.resolver_fuente(n_a, {"carpetas": [S.FUENTES], "alias": {}})
    ok(sin and os.path.normcase(sin) == os.path.normcase(r_a),
       "sin reemplazo NO vuelve la tipografía original")
    print(f"  · «{n_a}» → con reemplazo: {os.path.basename(r_b)} · sin reemplazo: {os.path.basename(r_a)}")

# ── 3. 🔴 LO GUARDADO EN EL MOLDE YA NO MANDA ───────────────────────────────────────────────
# `_fuentes_para` sólo arma alias con lo que recibe por parámetro (lo que manda el pedido).
_fx = S._fuentes_para("prod_inexistente_para_la_prueba")
ok(_fx.get("alias") == {}, f"`_fuentes_para` trae alias de algún lado: {_fx.get('alias')}")
_fx2 = S._fuentes_para("prod_inexistente_para_la_prueba", {"X": "Y"})
ok(_fx2.get("alias") == {"X": "Y"}, "`_fuentes_para` no toma los reemplazos del pedido")
# …y ningún molde real puede imponer el suyo
_cat = S._cargar_catalogo() or {}
_con_alias = [p.get("nombre") for p in _cat.get("productos", []) if p.get("fuentes_reemplazo")]
_fx3 = S._fuentes_para((_cat.get("productos") or [{}])[0].get("id"))
ok(_fx3.get("alias") == {}, "un molde con `fuentes_reemplazo` guardado todavía impone su alias")
print(f"  · moldes con reemplazo viejo guardado: {_con_alias or '(ninguno)'} → ya no se leen")

# ── 4. La predeterminada existe (el fallback tiene con qué estampar) ─────────────────────────
_anton = MP.resolver_fuente("Anton Regular", {"carpetas": [S.FUENTES], "alias": {}})
ok(bool(_anton), "no está «Anton Regular»: el fallback de tipografía no encontrada no tiene con qué estampar")
print(f"  · predeterminada: {os.path.basename(_anton) if _anton else 'NO ESTÁ'}")

# ── 5. CAMBIAR LA TIPOGRAFÍA SE VE AL INSTANTE ──────────────────────────────────────────────
# El render por pieza está CACHEADO: si la clave no incluyera el reemplazo, elegir otra tipografía
# devolvería el dibujo anterior y parecería que no pasó nada. (El front hace lo mismo con su caché
# en memoria: `_pvKeyCon` incluye `fuentesReempl`.)
_prod = (S._cargar_catalogo() or {}).get("productos", [{}])[0]
_pid = _prod.get("id")
_args = dict(pid=_pid, sub=None, prod=_prod, mapeo={"Frente 1": 1}, edit_cfg={}, edit_tam={},
             variante="v_1", talle="M")
_k0 = S._piezas_base_clave(**_args, reempl={})
_k1 = S._piezas_base_clave(**_args, reempl={"ClubAmerica2021-2022": "Impact Regular"})
_k2 = S._piezas_base_clave(**_args, reempl={"ClubAmerica2021-2022": "Anton Regular"})
ok(_k0 != _k1, "cambiar la tipografía NO cambia la clave del caché (se serviría el dibujo viejo)")
ok(_k1 != _k2, "dos tipografías distintas comparten clave de caché")
ok(_k0 == S._piezas_base_clave(**_args, reempl={}), "la clave no es estable con los mismos datos")
print("  · la clave del render cambia con la tipografía elegida (se re-dibuja al instante)")

print()
if FALLOS:
    print("✗ FALLA:")
    for f in FALLOS:
        print("   ·", f)
    sys.exit(1)
print("OK fuentes: la del arte gana si está, el reemplazo es del PEDIDO y lo del molde ya no manda")
