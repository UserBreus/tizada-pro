# -*- coding: utf-8 -*-
"""CONTRATO DE LA CONFIGURACIÓN ESTABLE DEL CAMINO B — `py verificar_config_con_diseno.py`

El cliente que sube un molde con el diseño adentro **no configura** el borde de corte, ni el
tamaño de la etiqueta, ni el nesting: eso lo deja el admin UNA vez y vale para todos esos moldes.

Y es **VIVA** (decisión del usuario, 2026-09-02): el molde APUNTA a esa config, no se le copia
nada, así que cambiarla afecta también a los moldes ya cargados.

Las tres cosas que se rompen si esto se hace a medias, y que por eso se verifican:

  1. **Que un solo lugar decida.** El preview del paso Arte, la ficha y las llamadas al motor
     leen el borde y la etiqueta por su cuenta. Si uno lee el del molde y otro el global, lo que
     se ve en pantalla deja de ser lo que se estampa — que es LA ley del proyecto.
  2. **Que el cambio se vea.** El preview está cacheado en disco. Si el valor resuelto no entra
     en la clave, el admin cambia el borde y el paso Arte sigue mostrando el viejo hasta que
     cambie cualquier otra cosa. Sale bien en la tizada y mal en la pantalla: nadie lo entiende.
  3. **Que el admin no pise el trabajo del cliente.** Lo global es la FORMA de la etiqueta; el
     DÓNDE va (`posiciones`) lo marca el cliente pieza por pieza. Si la config global arrastrara
     las posiciones, guardar en Configuración borraría ese trabajo en todos los pedidos.

⚠️ No toca nada del usuario: `db` es un doble que explota y el catálogo es un dict en memoria.
"""
import os
import sys
import tempfile
import types

sys.stdout.reconfigure(encoding="utf-8")
_TMP = tempfile.mkdtemp(prefix="verif_cfgb_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"
_fdb = types.ModuleType("db")
_fdb.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(
    AssertionError(f"LA PRUEBA INTENTO TOCAR MSSQL (db.{n})")))
# El registro se lee de la base: se simula en memoria (dos piezas alcanzan para la lista que
# devuelve `get_etiqueta`). Sin esto el endpoint revienta y el chequeo pasa mirando una respuesta
# de error, que es peor que fallar.
_REG = {"Frente": {"M": {"mesa": 1, "pieza_idx": 0}}, "Espalda": {"M": {"mesa": 2, "pieza_idx": 1}}}
_fdb.leer_registro = lambda pid: dict(_REG)
_fdb.registro_rev = lambda pid: 1
sys.modules["db"] = _fdb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import servidor as S               # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)


# El molde del camino B guarda SU trabajo (dónde va la etiqueta en cada pieza) y nada más.
MOLDE_B = {"id": "prod_b", "nombre": "Camiseta", "origen": "con_diseno", "efimero": True,
           "etiqueta": {"posiciones": {"Frente": {"rx": 0.2, "ry": 0.8, "ang": 0}}}}
# El del camino A tiene su propia config, y no la tiene que tocar nadie.
MOLDE_A = {"id": "prod_a", "nombre": "Camiseta de futbol",
           "borde_corte": {"activo": True, "ancho_mm": 7.5, "color": [0, 0, 0, 1], "alineacion": "dentro"},
           "etiqueta": {"size_mm": 9.0, "separador": "/"}}
CAT = {"activo": "prod_a", "productos": [MOLDE_A, MOLDE_B],
       "config_con_diseno": {"borde_corte": {"ancho_mm": 3.0, "alineacion": "centro"},
                             "etiqueta": {"size_mm": 5.0, "separador": " · "},
                             "nesting_preset_id": "nesting_default"}}

print("CONTRATO DE LA CONFIGURACIÓN ESTABLE — moldes con el diseño adentro\n")

# ══ 1. CADA MOLDE LEE DE DONDE CORRESPONDE ═══════════════════════════════════════════════════
print("1 · EL MOLDE CON DISEÑO LEE LA DEL ADMIN; EL DE SIEMPRE, LA SUYA")
_bb = S._borde_de(MOLDE_B, CAT)
_ba = S._borde_de(MOLDE_A, CAT)
ok(_bb["ancho_mm"] == 3.0 and _bb["alineacion"] == "centro",
   f"🔴 el molde con diseño no usa el borde del admin: {_bb}")
ok(_ba["ancho_mm"] == 7.5 and _ba["alineacion"] == "dentro",
   f"🔴 al molde de siempre le cambiaron el borde: {_ba}")
_eb, _ea = S._etiqueta_de(MOLDE_B, CAT), S._etiqueta_de(MOLDE_A, CAT)
ok(_eb["size_mm"] == 5.0 and _eb["separador"] == " · ",
   f"🔴 el molde con diseño no usa la etiqueta del admin: size={_eb['size_mm']}")
ok(_ea["size_mm"] == 9.0 and _ea["separador"] == "/",
   f"🔴 al molde de siempre le cambiaron la etiqueta: size={_ea['size_mm']}")
print(f"    OK    con diseño: borde {_bb['ancho_mm']} mm · etiqueta {_eb['size_mm']} mm  |  "
      f"de siempre: {_ba['ancho_mm']} mm · {_ea['size_mm']} mm")

# ══ 2. ES VIVA ═══════════════════════════════════════════════════════════════════════════════
print("\n2 · 🔴 CAMBIARLA ALCANZA A LOS MOLDES YA CARGADOS")
CAT["config_con_diseno"]["borde_corte"]["ancho_mm"] = 12.0
ok(S._borde_de(MOLDE_B, CAT)["ancho_mm"] == 12.0,
   "🔴 el molde ya cargado se quedó con el borde viejo: la config no es viva (¿se copió al alta?)")
ok(S._borde_de(MOLDE_A, CAT)["ancho_mm"] == 7.5,
   "🔴 el cambio del admin le tocó el borde a un molde del camino A")
print("    OK    el admin cambia 3 → 12 mm y el molde con diseño ya sale con 12; el otro sigue en 7,5")

# ══ 3. EL ADMIN NO PISA EL TRABAJO DEL CLIENTE ═══════════════════════════════════════════════
print("\n3 · 🔴 LA FORMA ES DEL ADMIN, EL DÓNDE ES DEL CLIENTE")
CAT["config_con_diseno"]["etiqueta"]["posiciones"] = {"Frente": {"rx": 0.99, "ry": 0.01}}
_eb = S._etiqueta_de(MOLDE_B, CAT)
ok(_eb["posiciones"] == {"Frente": {"rx": 0.2, "ry": 0.8, "ang": 0}},
   f"🔴 la config del admin PISÓ dónde puso la etiqueta el cliente: {_eb['posiciones']}")
ok("posiciones" not in S._cfg_con_diseno(CAT)["etiqueta"],
   "🔴 la config global acepta `posiciones`: el dónde no puede ser global, es de cada molde")
print("    OK    el cliente conserva su «Frente» en (0.2, 0.8) aunque el admin mande otra cosa")

# ══ 4. EL CAMBIO SE VE EN LA PANTALLA ════════════════════════════════════════════════════════
print("\n4 · 🔴 EL PREVIEW SE REGENERA SOLO (el valor resuelto entra en la clave del caché)")
_args = dict(pid="prod_b", sub=None, prod=MOLDE_B, mapeo={}, edit_cfg={}, edit_tam={},
             variante=None, talle="M", edit_color={}, cat=CAT, reempl={}, edit_marca={})
_k1 = S._piezas_base_clave(**_args)
CAT["config_con_diseno"]["borde_corte"]["ancho_mm"] = 0.5
_k2 = S._piezas_base_clave(**_args)
ok(_k1 != _k2,
   "🔴 cambiar el borde del admin NO mueve la clave del caché: el paso Arte seguiría mostrando el "
   "borde viejo (bien en la tizada, mal en la pantalla — el bug que nadie entiende)")
_args_a = dict(_args, pid="prod_a", prod=MOLDE_A)
_ka1 = S._piezas_base_clave(**_args_a)
CAT["config_con_diseno"]["borde_corte"]["ancho_mm"] = 9.0
ok(S._piezas_base_clave(**_args_a) == _ka1,
   "un cambio de la config del camino B mueve la clave de un molde del camino A (regenera de más)")
print("    OK    la clave cambia con la config del admin, y sólo para los moldes con diseño")

# ══ 5. LA PANTALLA DEL MOLDE NO DEJA EDITAR LO QUE ES GLOBAL ═════════════════════════════════
print("\n5 · GUARDAR EL BORDE DE UN MOLDE CON DISEÑO SE RECHAZA (no se guarda al vacío)")
S._USUARIOS_ON = False
S._usuario_actual = lambda *a, **k: {"id": 1, "permisos": ["molde.editar", "config.editar"]}
S._cargar_catalogo = lambda *a, **k: CAT
S._cargar_catalogo_para_editar = lambda *a, **k: CAT
S._guardar_catalogo = lambda c, *a, **k: None
cli = S.app.test_client()
r = cli.post("/api/productos/borde_corte", json={"pid": "prod_b", "ancho_mm": 1.0})
ok(r.status_code == 409,
   f"🔴 dejó guardar el borde de un molde con diseño ({r.status_code}): la pantalla parecería "
   f"guardar y el motor seguiría leyendo el global")
r = cli.post("/api/productos/borde_corte", json={"pid": "prod_a", "ancho_mm": 1.0})
ok(r.status_code == 200, f"🔴 dejó de poder guardarse el borde de un molde normal ({r.status_code})")
print("    OK    con diseño → 409 con el motivo · de siempre → se guarda igual que antes")

print("\n5b · Y EL GET AVISA QUE ES GLOBAL")
r = cli.get("/api/productos/borde_corte?pid=prod_b")
ok((r.get_json() or {}).get("global") is True, "el GET no marca que el borde es el global")
r = cli.get("/api/productos/etiqueta?pid=prod_b")
ok((r.get_json() or {}).get("forma_global") is True, "el GET no marca que la forma es la global")
print("    OK    la pantalla puede mostrar esos campos bloqueados")

# ══ 6. EL ENDPOINT DEL ADMIN ═════════════════════════════════════════════════════════════════
print("\n6 · EL ADMIN LA GUARDA Y DICE A CUÁNTOS MOLDES ALCANZA")
r = cli.post("/api/config_con_diseno", json={"borde_corte": {"ancho_mm": 4.2},
                                             "etiqueta": {"size_mm": 6.0}})
_d = r.get_json() or {}
ok(r.status_code == 200, f"no se pudo guardar la config ({r.status_code}): {_d}")
ok(_d.get("borde_corte", {}).get("ancho_mm") == 4.2, f"no guardó el borde: {_d.get('borde_corte')}")
ok(_d.get("etiqueta", {}).get("size_mm") == 6.0, f"no guardó la etiqueta: {_d.get('etiqueta')}")
ok(_d.get("moldes") == 1, f"dice que alcanza a {_d.get('moldes')} molde(s), y hay 1 con diseño")
ok(S._borde_de(MOLDE_B, CAT)["ancho_mm"] == 4.2, "lo guardado no llegó al molde")
print(f"    OK    guardó 4,2 mm y avisa que alcanza a {_d.get('moldes')} molde(s)")

print()
if FALLOS:
    print(f"❌ {len(FALLOS)} FALLO(S):")
    for f in FALLOS:
        print("   -", f)
    sys.exit(1)
print("✅ CONTRATO VERDE — una sola config para todos esos moldes, viva, y sin pisar al cliente")
