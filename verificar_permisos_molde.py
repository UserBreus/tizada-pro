"""
CONTRATO DE VISIBILIDAD / PERMISOS DE UNA MOLDERÍA — se corre con `py verificar_permisos_molde.py`.

Dos cosas que NO son lo mismo y que el sistema había mezclado:

  · `creado_por` = **AUTORÍA** (quién dio de alta la moldería). La lleva TODA moldería creada con
    sesión, incluidas las del catálogo, que se cargan desde Configuración.
  · `propio`     = **PRIVACIDAD** («Mi artículo» del pedido, lo ve sólo su dueño).

Usar `creado_por` como señal de privacidad escondía del resto de los usuarios los moldes cargados
desde Configuración —que son justamente los de todos— y los mandaba a «Mis artículos».

Y el reverso, que es lo que rompe si se arregla a medias: si el catálogo lo ve todo el mundo,
**ver no puede seguir habilitando a escribir** — ahí entran `molde.editar` / `molde.borrar`.

⚠️ No toca nada del usuario: el módulo `db` se reemplaza por un doble que explota (ver
[[test-no-toca-mssql]]) y `DATOS` va a un temporal.
"""
import os
import sys
import tempfile
import types

_TMP = tempfile.mkdtemp(prefix="verif_perm_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"

_falso_db = types.ModuleType("db")
_falso_db.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(
    AssertionError(f"LA PRUEBA INTENTO TOCAR MSSQL (db.{n}) — revisar el aislamiento")))

# ── LA "BASE" DEL REGISTRO, SIMULADA (2026-08-19: el server lee el registro SOLO de la base;
#    el doble la imita en memoria, sembrada del JSON que este contrato dejó en su tmp). ──
import json as _rj, os as _ro
_REG_MEM, _REG_REV = {}, {}
def _reg_leer(pid):
    if pid not in _REG_MEM:
        try:
            _p = _ro.path.join(_ro.environ["TIZADA_DATOS"], "productos", pid, "registro_producto.json")
            _REG_MEM[pid] = _rj.load(open(_p, encoding="utf-8")); _REG_REV[pid] = 1
        except Exception:
            return None
    return _REG_MEM.get(pid)
_falso_db.leer_registro = _reg_leer
_falso_db.registro_rev = lambda pid: (_REG_REV.get(pid, 1) if _reg_leer(pid) is not None else None)
_falso_db.guardar_registro = lambda pid, piezas, reg: (_REG_MEM.__setitem__(pid, reg),
                                                  _REG_REV.__setitem__(pid, _REG_REV.get(pid, 1) + 1), 1)[-1]
_falso_db.borrar_piezas_molde = lambda pid: (_REG_MEM.pop(pid, None), _REG_REV.pop(pid, None), 0)[-1]
sys.modules["db"] = _falso_db

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import servidor as S               # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)


# ── Los actores, con los permisos REALES de los roles del sistema ────────────────────────────
ADMIN = {"id": 1, "permisos": ["molde.ver", "molde.editar", "molde.borrar", "molde.crear",
                               "molde.ver_todos", "config.ver"]}
DISENADOR = {"id": 2, "permisos": ["molde.ver", "molde.editar", "molde.crear", "config.ver"]}
OPERARIO = {"id": 3, "permisos": ["molde.ver", "pedido.crear", "pedido.generar"]}

CATALOGO = {"id": "prod_a", "nombre": "Camisetas", "creado_por": 1, "propio": False}
CATALOGO_VIEJO = {"id": "prod_b", "nombre": "Molde 1"}                 # sin ninguno de los dos campos
MI_ARTICULO = {"id": "prod_c", "nombre": "Short", "creado_por": 1, "propio": True}


# ══ 1. VER ════════════════════════════════════════════════════════════════════════════════════
# ⬇⬇ LA QUE ATRAPA EL BUG QUE REPORTÓ EL USUARIO ⬇⬇
ok(S._puede_ver_molde(CATALOGO, OPERARIO),
   "una molderia cargada desde Configuracion NO la ve el resto (es del catalogo, es de todos)")
ok(S._puede_ver_molde(CATALOGO, DISENADOR), "el disenador no ve una molderia del catalogo")
ok(S._puede_ver_molde(CATALOGO_VIEJO, OPERARIO), "no se ve una molderia vieja (sin dueno ni propio)")
ok(not S._es_privado(CATALOGO), "una molderia del catalogo quedo marcada como privada")

# «Mi artículo» sigue siendo privado: eso NO se toca
ok(S._puede_ver_molde(MI_ARTICULO, ADMIN), "el admin (molde.ver_todos) no ve el articulo de otro")
ok(S._puede_ver_molde(MI_ARTICULO, {"id": 1, "permisos": []}), "el dueno no ve su propio articulo")
ok(not S._puede_ver_molde(MI_ARTICULO, OPERARIO),
   "un usuario cualquiera VE el «Mi articulo» de otro — eso tiene que seguir privado")
ok(not S._puede_ver_molde(MI_ARTICULO, DISENADOR),
   "el disenador (sin molde.ver_todos) ve el «Mi articulo» de otro")


# ══ 2. ESCRIBIR — ver el catálogo no habilita a tocarlo ═══════════════════════════════════════
# ⬇⬇ ESTA ES LA CONTRACARA: sin ella, arreglar la visibilidad abre el catalogo a cualquiera ⬇⬇
ok(not S._puede_editar_molde(CATALOGO, "molde.editar", OPERARIO),
   "un Operario puede EDITAR una molderia del catalogo (solo tiene molde.ver)")
ok(not S._puede_editar_molde(CATALOGO, "molde.borrar", DISENADOR),
   "el disenador puede BORRAR del catalogo y no tiene molde.borrar")
ok(S._puede_editar_molde(CATALOGO, "molde.editar", DISENADOR), "el disenador no puede editar el catalogo")
ok(S._puede_editar_molde(CATALOGO, "molde.borrar", ADMIN), "el admin no puede borrar del catalogo")

# pero su PROPIO artículo lo configura siempre, sin permisos de catálogo: para eso está la pestaña
ok(S._puede_editar_molde({"id": "x", "creado_por": 3, "propio": True}, "molde.editar", OPERARIO),
   "el Operario no puede configurar SU PROPIO articulo (no tiene molde.editar, y no le hace falta)")
# el de OTRO no, ni con ver_todos: verlo no es tocarlo
ok(not S._puede_editar_molde(MI_ARTICULO, "molde.editar", OPERARIO),
   "el Operario puede editar el «Mi articulo» de otro")

# usar el molde (activar, generar) NO pide permiso de escritura
ok(S._puede_editar_molde(CATALOGO, None, OPERARIO),
   "activar/generar con un molde del catalogo pide permiso de edicion — un Operario no podria trabajar")


# ══ 2.b DE QUIÉN ES CADA MOLDE (la regla, dicha por el usuario 2026-07-29) ════════════════════
#   · Lo que se carga en CONFIGURACIÓN es del SISTEMA: sin dueño personal, lo ve y usa todo el
#     mundo — aunque lo haya cargado alguien con su sesión.
#   · Lo que se sube en PEDIDO → «Mis artículos» es de QUIEN TIENE LA SESIÓN, y no lo ve nadie más.
#   · Y los «Mis artículos» NO se listan en Configuración: usan las mismas herramientas pero se
#     manejan aparte.
def alta(propio, uid):
    """Lo que guarda `crear_producto` para cada camino (espejo de servidor.py)."""
    return {"creado_por": (uid if propio else None), "alta_por": uid, "propio": propio}


_cfg = alta(False, 1)          # cargado en Configuracion por el usuario 1
_mio = alta(True, 7)           # subido en Pedido por el usuario 7 (felipe)
_otro = {"id": 9, "permisos": ["molde.ver"]}
_felipe = {"id": 7, "permisos": ["molde.ver"]}

ok(_cfg["creado_por"] is None, f"un molde de Configuracion quedo con dueno personal: {_cfg}")
ok(_cfg["alta_por"] == 1, "se perdio la trazabilidad de quien lo dio de alta")
ok(not S._es_privado(_cfg), "un molde de Configuracion quedo privado")
ok(S._puede_ver_molde(_cfg, _otro) and S._puede_ver_molde(_cfg, _felipe),
   "un molde de Configuracion no lo ve todo el mundo")

ok(S._es_privado(_mio), f"un «Mi articulo» no quedo privado: {_mio}")
ok(S._puede_ver_molde(_mio, _felipe), "el dueno no ve su propio articulo")
ok(not S._puede_ver_molde(_mio, _otro), "el articulo de felipe lo ve otro usuario")
# su dueño lo configura sin permisos de catálogo; otro no lo toca ni con `molde.editar`
ok(S._puede_editar_molde(_mio, "molde.editar", _felipe), "el dueno no puede configurar su articulo")
ok(not S._puede_editar_molde(_mio, "molde.editar", {"id": 9, "permisos": ["molde.editar"]}),
   "otro usuario puede editar el «Mi articulo» de felipe")


# ══ 2.c UN «MI ARTÍCULO» SIN DUEÑO ES UN ESTADO IMPOSIBLE ═════════════════════════════════════
# `propio: true` + `creado_por: null` se comporta de las dos formas a la vez y mal: NO cuenta como
# privado (se cuela en Configuración) y a la vez `get_productos` lo marca «es mío» para CUALQUIERA
# (la rama `not creado_por`) → aparece en «Mis artículos» de todos. Pasó de verdad.
_roto = {"id": "x", "nombre": "Roto", "creado_por": None, "propio": True}
ok(not S._es_privado(_roto),
   "el estado roto SI cuenta como privado — entonces el sintoma seria otro, revisar la hipotesis")
# «es mío» tal cual lo calcula get_productos, mirado por alguien que NO lo creó
_es_mio_para = lambda p, u: bool(p.get("propio")) and (not u or not p.get("creado_por")
                                                       or p.get("creado_por") == u["id"])
ok(_es_mio_para(_roto, {"id": 9}),
   "el estado roto NO se ve como propio de un tercero — la hipotesis del sintoma no se sostiene")
# …y una vez reparado (pasa a ser del sistema) deja de mentirle a todos
_rep = {**_roto, "propio": False}
ok(not _es_mio_para(_rep, {"id": 9}) and not S._es_privado(_rep),
   "tras reparar sigue apareciendo como propio de otro")


# ══ 3. TALLER SIN SISTEMA DE USUARIOS: se puede todo, como siempre ════════════════════════════
_real_u, _real_on = S._usuario_actual, S._USUARIOS_ON
S._usuario_actual, S._USUARIOS_ON = (lambda: None), False
try:
    ok(S._puede_ver_molde(MI_ARTICULO),
       "sin sistema de usuarios se esconde un molde que NADIE puede reclamar (queda inaccesible)")
    ok(S._puede_editar_molde(CATALOGO, "molde.borrar"), "sin sesion se le exige un permiso a nadie")
    # con el sistema de usuarios ENCENDIDO y sin loguearse, lo privado sí se esconde
    S._USUARIOS_ON = True
    ok(not S._puede_ver_molde(MI_ARTICULO),
       "con usuarios activos, un anonimo ve el «Mi articulo» de otro")
finally:
    S._usuario_actual, S._USUARIOS_ON = _real_u, _real_on


# ══ Veredicto ════════════════════════════════════════════════════════════════════════════════
import shutil
shutil.rmtree(_TMP, ignore_errors=True)
if FALLOS:
    print(f"\nx PERMISOS DE MOLDERIA ROTOS ({len(FALLOS)}):\n")
    for f in FALLOS:
        print("    -", f)
    sys.exit(1)
print("OK permisos de molderia: el catalogo lo ve todo el mundo y lo toca solo quien tiene permiso")
