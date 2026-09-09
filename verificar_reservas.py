# -*- coding: utf-8 -*-
"""
CONTRATO: «ESTO LO ESTÁ EDITANDO FULANO» — `py verificar_reservas.py`.

Pedido del usuario (2026-09-09): que en Configuración se pueda ver en vivo quién está trabajando
en qué, o directamente que si alguien está editando un molde o una regla de nesting, otro no pueda.

Guardar con versión (changelog 416) evita PERDER el trabajo del otro, pero no evita pisarle el
VALOR sin enterarse. La reserva es lo que lo hace visible: quien abre un editor toma esa cosa, y
los demás la ven en sólo lectura con el nombre de quien la tiene.

Lo que candamos:
  1. la toma es EXCLUSIVA y la decide la base, no el orden en que llegaron a la memoria;
  2. el dueño puede renovarla todas las veces que quiera (es su editor abierto);
  3. **se suelta SOLA** cuando la pantalla deja de latir — nadie queda bloqueado porque alguien se
     fue a almorzar con la ventana abierta;
  4. sólo el dueño la suelta (si no, soltar la del otro sería un botón para robarla);
  5. si la base no contesta, NO se traba a nadie: la reserva es una cortesía, no un requisito;
  6. no se puede reservar cualquier cosa (el nombre del recurso va validado).

⚠️ La parte de servidor va contra un doble en memoria ([[test-no-toca-mssql]]). La parte de SQL sí
va contra la base real, pero SÓLO sobre recursos de prueba con nombre propio, que se borran al
final: la tabla `reserva` es papel de borrador, no datos del usuario.
"""
import copy
import os
import sys
import tempfile
import types

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_TMP = tempfile.mkdtemp(prefix="verif_reservas_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK    " if cond else "  FALLA ") + msg)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1 · LA LÓGICA CONTRA LA BASE DE VERDAD (es una sentencia condicionada: tiene que decidir el motor)
# ══════════════════════════════════════════════════════════════════════════════════════════════
print("1 · LA TOMA LA DECIDE LA BASE")
_REC = "molde:zz_prueba_reservas"
_ANA, _BRUNO = 990001, 990002
_hay_base = True
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import db as _dbr   # noqa: E402
    _dbr.soltar_reserva(_REC, _ANA)
    _dbr.soltar_reserva(_REC, _BRUNO)
except Exception as e:
    _hay_base = False
    print(f"  (sin base: esta parte no se puede probar — {str(e)[:70]})")

if _hay_base:
    _m1, _d1 = _dbr.tomar_reserva(_REC, _ANA, "Ana")
    ok(_m1 is True, "quien llega primero se la queda")
    _m2, _d2 = _dbr.tomar_reserva(_REC, _BRUNO, "Bruno")
    ok(_m2 is False and (_d2 or {}).get("usuario") == "Ana",
       f"el segundo NO se la queda, y se le dice quién la tiene ({(_d2 or {}).get('usuario')})")
    ok(_dbr.tomar_reserva(_REC, _ANA, "Ana")[0] is True,
       "el dueño la renueva todas las veces que quiera (su editor sigue abierto)")
    ok(_dbr.soltar_reserva(_REC, _BRUNO) is False,
       "🔴 otro NO puede soltarla (sería un botón para robarla)")
    # VENCIMIENTO: con el tope en 0 segundos, cualquier reserva ya está vencida.
    ok(_dbr.tomar_reserva(_REC, _BRUNO, "Bruno", segundos=0)[0] is True,
       "🔴 una reserva que dejó de latir queda libre sola (nadie se traba por una ventana olvidada)")
    ok(_dbr.soltar_reserva(_REC, _BRUNO) is True, "y el dueño la suelta cuando cierra")
    ok(_REC not in _dbr.reservas_vivas(), "al soltarla desaparece de la lista")
    # …y la lista limpia lo vencido sin necesidad de un proceso aparte
    _dbr.tomar_reserva(_REC, _ANA, "Ana")
    ok(_REC not in _dbr.reservas_vivas(segundos=0),
       "pedir la lista es lo que limpia lo vencido (no hace falta un hilo cuidando esto)")
    _dbr.soltar_reserva(_REC, _ANA)

# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2 · LOS ENDPOINTS (contra un doble: acá lo que se prueba es la pantalla, no el SQL)
# ══════════════════════════════════════════════════════════════════════════════════════════════
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"
_RES = {}
_falso = types.ModuleType("db")


def _tomar(recurso, uid, usuario=None, segundos=None):
    d = _RES.get(recurso)
    if d and d["usuario_id"] != uid:
        return False, dict(d)
    _RES[recurso] = {"usuario_id": uid, "usuario": usuario}
    return True, dict(_RES[recurso])


_falso.tomar_reserva = _tomar
_falso.soltar_reserva = lambda r, uid: bool(
    _RES.get(r) and _RES[r]["usuario_id"] == uid and _RES.pop(r, None))
_falso.soltar_reservas_de = lambda uid: len(
    [_RES.pop(k) for k, v in list(_RES.items()) if v["usuario_id"] == uid])
_falso.reservas_vivas = lambda segundos=None: copy.deepcopy(_RES)
_DOCS = {}
_VERS = {}
_falso.get_doc = lambda c, default=None: copy.deepcopy(_DOCS.get(c, default))
_falso.get_doc_ver = lambda c, default=None: (copy.deepcopy(_DOCS.get(c, default)), _VERS.get(c, 0))
_falso.set_doc = lambda c, o, version_esperada=None: _VERS.__setitem__(c, _VERS.get(c, 0) + 1)
_falso.guardar_catalogo = lambda cat, version_esperada=None: _DOCS.__setitem__("catalogo", cat)
_falso.__getattr__ = lambda n: (lambda *a, **k: None)
sys.modules["db"] = _falso
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")

import tempfile as _tmp_log, registro as _LOG_PRUEBA   # noqa: E402
_LOG_PRUEBA.usar_carpeta(_tmp_log.mkdtemp(prefix="verif_logs_"))
import servidor as S               # noqa: E402

print("\n2 · LOS ENDPOINTS")
_QUIEN = {"u": {"id": 1, "nombre": "Ana"}}
S._usuario_actual = lambda: _QUIEN["u"]
CLI = S.app.test_client()

_r = CLI.post("/api/reserva/tomar", json={"recurso": "nesting:preset_1"}).get_json()
ok(_r.get("mia") is True, f"Ana toma la regla de nesting ({_r})")
_QUIEN["u"] = {"id": 2, "nombre": "Bruno"}
_r = CLI.post("/api/reserva/tomar", json={"recurso": "nesting:preset_1"}).get_json()
ok(_r.get("mia") is False and (_r.get("dueno") or {}).get("usuario") == "Ana",
   f"Bruno no la puede tomar, y la pantalla puede decir de quién es ({_r})")
_r = CLI.post("/api/reserva/soltar", json={"recurso": "nesting:preset_1"}).get_json()
ok(_r.get("ok") is False, "y tampoco soltársela")
_l = CLI.get("/api/reservas").get_json()
ok("nesting:preset_1" in (_l.get("reservas") or {}) and _l.get("yo") == 2,
   f"la lista dice qué está tomado y quién soy yo ({_l})")

# El LATIDO que la pantalla ya hace es el que renueva (no hay un segundo reloj)
_QUIEN["u"] = {"id": 1, "nombre": "Ana"}
_r = CLI.get("/api/actualizacion/estado?reservas=molde:pA,nesting:preset_1").get_json()
ok("molde:pA" in (_r.get("reservas") or {}),
   f"el latido toma lo que la pantalla tenga abierto ({sorted((_r.get('reservas') or {}))})")
ok(_r.get("yo") == 1, "y dice quién soy, para pintar lo mío distinto de lo del otro")

# Recursos: no se puede reservar cualquier cosa
_r = CLI.post("/api/reserva/tomar", json={"recurso": "loquesea"})
ok(_r.status_code == 400, f"un recurso con nombre inventado se rechaza (HTTP {_r.status_code})")
_r = CLI.post("/api/reserva/tomar", json={"recurso": "molde:../../etc"})
ok(_r.status_code == 400, f"y uno con caracteres raros también (HTTP {_r.status_code})")

# Cerrar sesión / irse: se sueltan todas las suyas de una
CLI.post("/api/reserva/tomar", json={"recurso": "planilla:tpl1"})
_r = CLI.post("/api/reserva/soltar", json={"recurso": "*"}).get_json()
ok(_r.get("ok") is True and not [k for k, v in _RES.items() if v["usuario_id"] == 1],
   f"al irse se sueltan todas las suyas de una ({_r})")

print("\n3 · SI LA BASE NO CONTESTA, NADIE SE TRABA")
# 🔴 La reserva es una cortesía para no pisarse, no un requisito para trabajar. Si se cayera la
# base y encima no dejara editar, un problema de infraestructura se convertiría en un paro total.
_falso.tomar_reserva = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("base caída"))
_r = CLI.post("/api/reserva/tomar", json={"recurso": "molde:pA"}).get_json()
ok(_r.get("mia") is True and _r.get("sin_base") is True,
   f"sin base se sigue trabajando, y se dice que la reserva no pudo tomarse ({_r})")
_falso.tomar_reserva = _tomar

print("\n4 · Y LAS TIZADAS SON DE QUIEN LAS PIDIÓ")
# 🔴 Medido el 2026-09-09 ANTES de esto: pedir los moldes sin sesión daba 401, pero bajar el PDF de
# una tizada daba 200 — sin login. La ruta de descarga no empieza con `/api/`, así que no pasaba
# por la guardia.
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "servidor.py"),
            encoding="utf-8").read()
_desc = _src[_src.index('def descargar(tid, archivo):'):]
_desc = _desc[:_desc.index("send_from_directory")]
ok("_sesion_o_403()" in _desc, "🔴 la descarga de una tizada pide sesión")
ok("_trabajo_ajeno(tid)" in _desc, "🔴 y que la tizada sea tuya")
ok(_src.count("_trabajo_ajeno(") >= 6,
   f"todas las rutas de trabajos lo verifican ({_src.count('_trabajo_ajeno(')} usos)")
ok('"usuario": _u' in _src, "el trabajo nace con dueño")
ok("duenio.json" in _src,
   "y el dueño queda en disco (los trabajos se podan de memoria y los archivos quedan)")

print()
if FALLOS:
    print(f"  {len(FALLOS)} FALLO(S)")
    for f in FALLOS:
        print("   ·", f)
    sys.exit(1)
print("  OK: se ve quién está editando qué, se suelta solo, y las tizadas son de quien las pidió")
