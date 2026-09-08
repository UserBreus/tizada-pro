# -*- coding: utf-8 -*-
"""
CONTRATO: EL CANDADO DEL CATÁLOGO ES CORTO — `py verificar_catalogo_candado.py`.

El catálogo es UNO solo y global, y ~43 endpoints lo modifican con el patrón leer → cambiar lo mío
→ guardar. `_LOCK_CAT_EDICION` hace que esa secuencia sea atómica (changelog 171). El problema no
era el candado: era **cuánto tiempo se lo tenía tomado, y quiénes escribían sin él**.

  1. **Trabajo pesado adentro.** Borrar un molde lo tomaba y no lo soltaba hasta el final del
     request — con dos `rmtree` (el caché de piezas son miles de archivos) y un borrado en la
     base adentro. Guardar los grupos de telas lo tenía durante una consulta HTTP a la API del
     sistema, con 12 s de timeout. Nombrar piezas lo arrastraba hasta el alta manual del molde
     entero. Todo el taller esperaba detrás.
  2. **Un GET tomaba el candado de ESCRITURA.** `/api/plantilla/deteccion` (~19 veces al asignar
     variantes) lo tomaba para corregir la variante guía, y no lo soltaba hasta el final.
  3. **Leer el catálogo ESCRIBE.** `_cargar_catalogo` completa lo que falta y guarda. Eso lo hace
     cualquier request, incluido un GET, **y los workers del pool de dibujo**, que son otros
     procesos: el candado es por proceso, así que desde ahí se pisaba sin que nada lo frenara.

⚠️ No toca datos del usuario ni la base (el módulo `db` se reemplaza antes de importar `servidor`).
"""
import copy
import os
import sys
import tempfile
import threading
import time
import types

_TMP = tempfile.mkdtemp(prefix="verif_candado_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = "localhost\\NO_EXISTE_ES_UNA_PRUEBA"

_DOCS = {}
_GUARDADOS = []          # cada vez que se guarda el catálogo, se anota acá
_falso = types.ModuleType("db")
_falso.get_doc = lambda c, default=None: copy.deepcopy(_DOCS.get(c, default))
_falso.set_doc = lambda c, o: _DOCS.__setitem__(c, copy.deepcopy(o))
_falso.guardar_catalogo = lambda cat: (_GUARDADOS.append(time.time()),
                                       _DOCS.__setitem__("catalogo", copy.deepcopy(cat)))[-1]
_falso.__getattr__ = lambda n: (lambda *a, **k: None)
sys.modules["db"] = _falso

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tempfile as _tmp_log, registro as _LOG_PRUEBA   # noqa: E402
_LOG_PRUEBA.usar_carpeta(_tmp_log.mkdtemp(prefix="verif_logs_"))
import servidor as S   # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
S._USUARIOS_ON = False
C = S.app.test_client()
FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK    " if cond else "  FALLA ") + msg)


def candado_libre(espera=1.0):
    """¿Otro hilo podría editar la configuración ahora mismo?"""
    res = {"si": False}

    def _probar():
        if S._LOCK_CAT_EDICION.acquire(timeout=espera):
            res["si"] = True
            S._LOCK_CAT_EDICION.release()

    t = threading.Thread(target=_probar)
    t.start()
    t.join(espera + 1)
    return res["si"]


PID = "prod_candado"
_DOCS["catalogo"] = {"activo": PID, "productos": [{"id": PID, "nombre": "Molde de prueba"}]}

print("1) Leer el catálogo puede completar cosas… pero eso es ESCRIBIR")
_GUARDADOS.clear()
S._cargar_catalogo()
ok(len(_GUARDADOS) >= 1, "un catálogo incompleto se completa y se guarda (una sola vez)")
ok(candado_libre(), "y el candado queda LIBRE después")
_GUARDADOS.clear()
S._cargar_catalogo()
ok(not _GUARDADOS, "leerlo de nuevo ya no escribe nada (es idempotente)")

print("\n2) 🔴 Un worker del pool NUNCA escribe el catálogo")
_DOCS["catalogo"] = {"activo": PID, "productos": [{"id": PID, "nombre": "Molde de prueba"}]}
_GUARDADOS.clear()
cat = S._cargar_catalogo(solo_lectura=True)
ok(not _GUARDADOS,
   "en modo sólo lectura NO guarda (el candado es por proceso: desde un worker pisaría a ciegas)")
ok("plantillas_planillas" in cat,
   "pero devuelve el catálogo YA completo, igual que el servidor (si no, dibujaría otra cosa)")
ok(S._CATALOGO_SOLO_LECTURA is (not S._es_proceso_principal()),
   "el modo sale de si este proceso es el servidor o un worker")
_visor = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "srv_visor.py"),
              encoding="utf-8").read()
ok("_CATALOGO_SOLO_LECTURA = True" in _visor,
   "y el sandbox de sólo lectura lo apaga también (sus GET escribían en la base de verdad)")

print("\n3) La sección de edición se cuenta de a una (no le suelta el candado a quien la llamó)")
with S._seccion_edicion():
    ok(not candado_libre(0.2), "adentro, nadie más puede editar")
    with S._seccion_edicion():
        pass
    ok(not candado_libre(0.2),
       "🔴 salir de una sección ANIDADA no suelta la de afuera (con `_soltar_edicion_catalogo` sí)")
ok(candado_libre(), "y al salir del todo, queda libre")
ok(getattr(S._edicion_cat, "n", 0) == 0, "el contador vuelve a cero")

print("\n4) Un GET ya no se queda con el candado de escritura")
_DOCS["catalogo"] = {"activo": PID, "productos": [{"id": PID, "nombre": "M", "variante_guia": "vieja"}]}
S._cargar_catalogo()
ok(S._ajustar_variante_guia(PID, ["S", "M"]) == "S", "corrige la guía cuando apunta a algo que no existe")
ok(candado_libre(), "y suelta el candado (antes lo tenía hasta el final del request)")
ok(S._ajustar_variante_guia(PID, ["S", "M"]) is None, "si ya está bien, no cambia nada")
ok(candado_libre(), "🔴 y TAMBIÉN suelta cuando corta sin hacer nada (era el camino más común)")

print("\n5) El trabajo pesado corre SIN el candado")
_libre_durante = {}


def _rmtree_lento(*a, **k):
    time.sleep(0.6)
    _libre_durante["borrar"] = candado_libre(0.3)


import shutil   # noqa: E402
_rm_real = shutil.rmtree
shutil.rmtree = _rmtree_lento
S._guard_id = lambda *a, **k: None
_DOCS["catalogo"] = {"activo": PID, "productos": [{"id": PID, "nombre": "M"}]}
S._cargar_catalogo()
r = C.post("/api/productos/eliminar", json={"id": PID})
shutil.rmtree = _rm_real
ok(r.status_code == 200, f"borrar el molde funciona (contestó {r.status_code})")
ok(_libre_durante.get("borrar") is True,
   "🔴 mientras se borran los archivos del molde, otro puede seguir configurando")

_libre_durante.clear()
_DOCS["catalogo"] = {"activo": PID, "productos": [{"id": PID, "nombre": "M"}]}
S._cargar_catalogo()
S._guard_sesion_telas = lambda *a, **k: None


def _telas_lentas(cat):
    time.sleep(0.6)
    _libre_durante["telas"] = candado_libre(0.3)
    return []


S._telas_efectivas = _telas_lentas
r = C.post("/api/telas", json={"grupos": [{"nombre": "Livianas", "telas": ["1"]}]})
ok(r.status_code == 200, f"guardar los grupos de telas funciona (contestó {r.status_code})")
ok(_libre_durante.get("telas") is True,
   "🔴 y la consulta a la API de telas (hasta 12 s) ya no bloquea la configuración")

print("\n6) El espejo en JSON no hace esperar a nadie, y gana el último")
_ruta = os.path.join(_TMP, "productos_catalogo.json")
for i in range(5):
    S._guardar_catalogo_json_espejo({"vuelta": i})
time.sleep(0.3)
import json as _json   # noqa: E402
with open(_ruta, encoding="utf-8") as f:
    ok(_json.load(f).get("vuelta") == 4, "el archivo termina con el ÚLTIMO estado guardado")
ok(not [n for n in os.listdir(_TMP) if n.endswith(".tmp")], "y no quedan temporales tirados")
_t0 = time.time()
S._guardar_catalogo_json_espejo({"vuelta": 99})
ok(time.time() - _t0 < 0.5,
   "🔴 guardar no se queda esperando (eran hasta 7,2 s de reintentos CON el candado tomado)")

print()
if FALLOS:
    print(f"FALLARON {len(FALLOS)}:")
    for f in FALLOS:
        print("  -", f)
    sys.exit(1)
print("TODO OK: el candado se toma poquito, y nadie escribe el catálogo sin él")
