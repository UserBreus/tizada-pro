# -*- coding: utf-8 -*-
"""
CONTRATO: UNA LECTURA POR REQUEST, NO VEINTE — `py verificar_memo_request.py`.

Cada llamada a la base abre **su propia conexión** (no hay pool del lado de Python). Y había dos
cosas que se preguntaban una y otra vez dentro del mismo request:

  · **Quién sos** (`usuario_actual`): son TRES consultas —el usuario, sus roles, sus permisos—. Lo
    pregunta el guardia para toda la API y después casi cada endpoint lo vuelve a pedir para saber
    de quién es el molde. Eran 6 a 9 conexiones por request sólo para eso.
  · **El catálogo** (`_cargar_catalogo`): una consulta más el parseo del documento entero, y un
    endpoint cualquiera lo pide entre 3 y 6 veces (`_ruta_datos`, `_ruta_entrada`,
    `_get_active_producto_id`…).

La memoria vive en `flask.g`, o sea **muere con el request**: no es un caché entre pantallas ni
entre usuarios. Y tiene dos reglas que este contrato cuida:

  1. Lo que devuelve `_cargar_catalogo()` es **de sólo lectura**. Para cambiarlo va
     `_cargar_catalogo_para_editar()`, que **relee fresco** con el candado ya tomado — si
     devolviera lo memorizado, guardaría encima de lo que otro cambió mientras tanto.
  2. Fuera de un request (los hilos de fondo, los workers) no hay memoria: cada uno lee lo suyo.

⚠️ No toca datos del usuario ni la base (el módulo `db` se reemplaza antes de importar).
"""
import copy
import os
import re
import sys
import tempfile
import threading
import types

_TMP = tempfile.mkdtemp(prefix="verif_memo_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = "localhost\\NO_EXISTE_ES_UNA_PRUEBA"

_DOCS = {}
_CUENTA = {"get_doc": 0, "fila": 0, "filas": 0}
_falso = types.ModuleType("db")


def _get_doc(c, default=None):
    _CUENTA["get_doc"] += 1
    return copy.deepcopy(_DOCS.get(c, default))


def _fila(sql, *a):
    _CUENTA["fila"] += 1
    return {"id": 1, "usuario": "yo", "nombre": "Yo", "activo": 1}


def _filas(sql, *a):
    _CUENTA["filas"] += 1
    return [{"clave": "admin"}]


_falso.get_doc = _get_doc
_falso.fila = _fila
_falso.filas = _filas
_falso.guardar_catalogo = lambda cat: _DOCS.__setitem__("catalogo", copy.deepcopy(cat))
_falso.set_doc = lambda c, o: _DOCS.__setitem__(c, copy.deepcopy(o))
_falso.__getattr__ = lambda n: (lambda *a, **k: None)
sys.modules["db"] = _falso

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tempfile as _tmp_log, registro as _LOG_PRUEBA   # noqa: E402
_LOG_PRUEBA.usar_carpeta(_tmp_log.mkdtemp(prefix="verif_logs_"))
import servidor as S            # noqa: E402
import api_usuarios as AU       # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
FALLOS = []
PID = "prod_memo"


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK    " if cond else "  FALLA ") + msg)


def _catalogo_listo():
    """Un catálogo YA normalizado, para que leerlo no dispare ningún guardado."""
    _DOCS["catalogo"] = {"activo": PID, "productos": [{"id": PID, "nombre": "Molde"}]}
    S._cargar_catalogo()
    _CUENTA.update({k: 0 for k in _CUENTA})


print("1) Dentro de un request, el catálogo se lee UNA vez")
_catalogo_listo()
with S.app.test_request_context("/api/estado"):
    a = S._cargar_catalogo()
    b = S._cargar_catalogo()
    c = S._get_active_producto_id()
    ok(_CUENTA["get_doc"] == 1, f"tres pedidos = una sola lectura (fueron {_CUENTA['get_doc']})")
    ok(a is b, "y las dos veces es el MISMO catálogo (no dos copias que se pisan)")
    ok(c == PID, "el molde activo sale igual")

print("\n2) Fuera de un request no hay memoria (los hilos de fondo leen lo suyo)")
_catalogo_listo()
S._cargar_catalogo()
S._cargar_catalogo()
ok(_CUENTA["get_doc"] == 2, f"dos lecturas sueltas = dos viajes (fueron {_CUENTA['get_doc']})")
_res = {}


def _en_un_hilo():
    try:
        S._cargar_catalogo()
        _res["ok"] = True
    except Exception as e:
        _res["error"] = f"{type(e).__name__}: {e}"


t = threading.Thread(target=_en_un_hilo)
t.start()
t.join(10)
ok(_res.get("ok") is True, f"un hilo de fondo puede leer el catálogo sin reventar ({_res})")

print("\n3) 🔴 Para EDITAR se relee fresco (si no, se guardaría encima de otro)")
_catalogo_listo()
with S.app.test_request_context("/api/config"):
    S._cargar_catalogo()                       # lo lee y lo memoriza
    _DOCS["catalogo"]["productos"][0]["nombre"] = "Lo cambió otra pantalla"
    _CUENTA["get_doc"] = 0
    cat = S._cargar_catalogo_para_editar()
    ok(_CUENTA["get_doc"] >= 1, "pedirlo para editar vuelve a la base")
    ok(cat["productos"][0]["nombre"] == "Lo cambió otra pantalla",
       "y trae lo ÚLTIMO, no lo que este request había leído antes")
    cat["productos"][0]["nombre"] = "Lo mío"
    S._guardar_catalogo(cat)
    S._soltar_edicion_catalogo()
    ok(S._cargar_catalogo()["productos"][0]["nombre"] == "Lo mío",
       "después de guardar, el resto del request ve lo guardado")

print("\n4) Quién sos: una sola vez por request")
AU.session_prueba = True
with S.app.test_request_context("/api/estado"):
    from flask import session as _ses
    _ses["uid"] = 1
    _CUENTA.update({k: 0 for k in _CUENTA})
    u1 = AU.usuario_actual()
    u2 = AU.usuario_actual()
    u3 = AU.usuario_actual()
    ok(_CUENTA["fila"] == 1, f"tres preguntas = una consulta (fueron {_CUENTA['fila']})")
    ok(_CUENTA["filas"] <= 2, f"y sus roles/permisos una sola vez (fueron {_CUENTA['filas']})")
    ok(u1 is u2 is u3, "siempre el mismo")
    ok(u1["usuario"] == "yo", "y es quien tiene que ser")

print("\n5) Un login o un logout en el medio no devuelve al usuario de antes")
with S.app.test_request_context("/api/estado"):
    from flask import session as _ses
    _ses["uid"] = 1
    AU.usuario_actual()
    _ses["uid"] = 2                          # otro usuario en el mismo request
    _CUENTA.update({k: 0 for k in _CUENTA})
    u = AU.usuario_actual()
    ok(_CUENTA["fila"] == 1, "si cambia quién está logueado, se vuelve a preguntar")
    _ses.pop("uid", None)
    ok(AU.usuario_actual() is None, "y sin sesión no hay usuario (ni memoria que valga)")

print("\n6) El contrato de uso está escrito en el código, no sólo acá")
_srv = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "servidor.py"),
            encoding="utf-8").read()
ok("SÓLO LECTURA" in _srv.split("def _cargar_catalogo(")[1][:1200],
   "`_cargar_catalogo` avisa en su propia documentación que lo que devuelve no se toca")
# Nadie puede guardar el catálogo sin haber pedido el candado antes.
_fn = re.split(r"\ndef ", _srv)
_malas = []
for f in _fn:
    nombre = f.split("(")[0].strip()
    # `_guardar_catalogo_json_espejo` sólo *nombra* al espejo, no guarda el catálogo.
    if nombre in ("_cargar_catalogo", "_guardar_catalogo", "_normalizar_catalogo",
                  "_guardar_catalogo_json_espejo"):
        continue
    if "_guardar_catalogo(" in f and not ("_cargar_catalogo_para_editar(" in f
                                          or "_seccion_edicion(" in f):
        _malas.append(nombre)
ok(not _malas, f"ninguna función guarda el catálogo sin tomar el candado (sospechosas: {_malas})")

print()
if FALLOS:
    print(f"FALLARON {len(FALLOS)}:")
    for f in FALLOS:
        print("  -", f)
    sys.exit(1)
print("TODO OK: una lectura por request, y para editar siempre lo fresco")
