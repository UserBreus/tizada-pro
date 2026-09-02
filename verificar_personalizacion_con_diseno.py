# -*- coding: utf-8 -*-
"""CONTRATO DEL NOMBRE Y EL NÚMERO EN EL CAMINO B — `py verificar_personalizacion_con_diseno.py`

EL REQUISITO DEL ARCHIVO (decisión del usuario, 2026-09-02): un molde que trae el diseño adentro
tiene que traer, además de las capas de talle, **una capa «nombre» y una capa «00»** con los
placeholders. Pueden ser subcapas de Illustrator y pueden estar dentro de una máscara de recorte:
lo que importa es que la capa exista con ese rótulo.

Por qué hace falta un contrato para algo tan chico: el estampado busca `persona[campo]`, donde
`campo` es **el nombre de la capa**, y la prenda trae «nombre» y «numero». Una capa rotulada «00»
apunta a un campo «00» que la prenda no tiene → **el número no se estampa y no falla nada**. Sale
la tizada entera, impecable, con el «00» del diseño en las 40 camisetas. Por eso el rótulo se
traduce al campo canónico, y por eso se verifica.

Y la otra mitad: en un molde del camino B **las capas son los TALLES**. Si el auto-descubrimiento
las tomara como campos (que es lo que hacía), el motor estamparía texto sobre los 20 talles.

⚠️ No toca nada del usuario: sólo lee constantes y una copia en memoria.
"""
import os
import sys
import types

sys.stdout.reconfigure(encoding="utf-8")
_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"
_fdb = types.ModuleType("db")
_fdb.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(AssertionError("MSSQL")))
sys.modules.setdefault("db", _fdb)

import motor_pedido as MP            # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)


print("CONTRATO DEL NOMBRE Y EL NÚMERO — molde con el diseño adentro\n")

# ══ 1. EL RÓTULO DE LA CAPA LLEGA AL CAMPO QUE LA PRENDA TIENE ═══════════════════════════════
print("1 · 🔴 UNA CAPA «00» ES EL CAMPO «numero»")
ok(MP._CAMPO_ALIAS.get("00") == "numero",
   "🔴 una capa «00» no se traduce al campo «numero»: el número NO se estamparía, y sin error")
ok("nombre" not in MP._CAMPO_ALIAS,
   "«nombre» se está traduciendo a otra cosa: ya es el campo canónico")
print(f"    OK    alias: {MP._CAMPO_ALIAS}")

print("\n1b · Y ASÍ ES COMO EL ESTAMPADO LO ENCUENTRA")
# Espejo de `generar_pieza`: `texto = persona[_norm_nombre(campo)]`. Si el campo quedara «00»,
# esto daría vacío y el número no saldría.
persona = {"nombre": "GONZALEZ", "numero": "10"}
for _capa, _esperado in (("nombre", "GONZALEZ"), ("00", "10"), ("Número", "10"), ("NRO", "10")):
    _cn = MP._norm_nombre(_capa)
    _campo = MP._CAMPO_ALIAS.get(_cn, _cn)
    _val = persona.get(MP._norm_nombre(_campo), "")
    ok(_val == _esperado,
       f"🔴 una capa «{_capa}» estamparía «{_val}» y tenía que estampar «{_esperado}»")
print("    OK    «nombre»→GONZALEZ · «00»→10 · «Número»→10 · «NRO»→10")

# ══ 2. UN TALLE NUNCA ES UN CAMPO ════════════════════════════════════════════════════════════
print("\n2 · 🔴 LOS TALLES NO SON CAMPOS DE PERSONALIZACIÓN")
# En este camino las capas son los talles: auto-descubrirlas haría que el motor estampe texto
# sobre las 20. La exclusión vive en `extraer_personalizacion` y se comprueba leyendo su código
# (probarlo de verdad pide un archivo con capas «nombre»/«00», que todavía no hay).
import inspect                                                     # noqa: E402
_src = inspect.getsource(MP.extraer_personalizacion)
ok("talles_del_molde" in _src and "es_camino_b" in _src,
   "🔴 el auto-descubrimiento de campos ya no excluye los talles del camino B: cada talle se "
   "tomaría como un campo de personalización")
ok("_CAMPO_ALIAS" in _src, "el rótulo de la capa no se traduce al campo canónico")
print("    OK    los talles quedan fuera del auto-descubrimiento")

print("\n2b · Y EL «0» SIGUE SIENDO UN TALLE, NO UN NÚMERO")
ok("0" not in MP._CAMPO_ALIAS,
   "🔴 «0» quedó como alias del número, y en estos moldes «0» es un TALLE (el más chico)")
ok("0" in MP.CAPAS_NO_PERS, "«0» dejó de estar entre las capas que no son campos")
print("    OK    «0» es talle · «00» es el número")

print()
if FALLOS:
    print(f"❌ {len(FALLOS)} FALLO(S):")
    for f in FALLOS:
        print("   -", f)
    sys.exit(1)
print("✅ CONTRATO VERDE — el rótulo de la capa llega al campo que la prenda trae")
print("\n📌 REQUISITO DEL ARCHIVO (para el manual): el .ai tiene que traer, además de una capa por")
print("   talle, una capa «nombre» y una capa «00» con los placeholders. Pueden ser subcapas y")
print("   pueden estar dentro de una máscara de recorte.")
print("   ⚠️ Falta probarlo contra un archivo real que las traiga: cuando exista, correr")
print("   `verificar_tizada_con_diseno.py` y mirar que el nombre y el número salgan estampados.")
