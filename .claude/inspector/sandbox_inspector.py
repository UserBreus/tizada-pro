# SANDBOX DEL INSPECTOR (`.claude/agents/inspector.md`) — `py .claude/inspector/sandbox_inspector.py [puerto]`
# Al cerrarse borra su carpeta temporal. Se mata SIEMPRE por PID (`netstat -ano | grep :<puerto>`), nunca en masa.
#
# SANDBOX COMPLETO, ESCRIBIBLE Y AISLADO (puerto 8062) para recorrer Pedido y Configuración en la
# pantalla real. De la base REAL sólo LEE (SELECT) una foto: documentos de config, registros de los
# moldes y configuraciones de molde guardadas. Copia entrada/, datos/ (sin cachés) y las fuentes a un
# temporal. Todo lo que se guarde queda en memoria / en el temporal: nada toca MSSQL ni los datos.
import atexit, json, os, shutil, sys, tempfile, time, types, itertools
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))   # la raíz del repo
sys.path.insert(0, R)
PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 else 8062

import db as _r                                        # lectura de la base REAL (sólo SELECT)
DOCS = {}
for f in _r.filas("SELECT clave, valor FROM config WHERE producto_id IS NULL"):
    try:
        DOCS[f["clave"]] = json.loads(f["valor"])
    except Exception:
        pass
REG = {}
for p in (DOCS.get("catalogo") or {}).get("productos", []):
    try:
        r = _r.leer_registro(p["id"])
        if r:
            REG[p["id"]] = r
    except Exception as e:
        print("registro", p.get("id"), e)
CFGM = {}
try:
    for f in _r.listar_configs_molde(todas=True):
        CFGM[int(f["id"])] = _r.leer_config_molde(f["id"])
except Exception as e:
    print("config_molde", e)
_r.cerrar_compartida()
del sys.modules["db"]
print("foto:", len(DOCS), "docs,", len(REG), "registros,", len(CFGM), "configs de molde", flush=True)

TMP = tempfile.mkdtemp(prefix="sandbox_inspector_")
atexit.register(lambda: shutil.rmtree(TMP, ignore_errors=True))   # la copia es descartable: que no quede basura
for k, d in (("TIZADA_DATOS", "datos"), ("TIZADA_ENTRADA", "entrada"), ("TIZADA_TRABAJOS", "trabajos"),
             ("TIZADA_FUENTES", "fuentes")):
    os.environ[k] = os.path.join(TMP, d)
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"
_CACHES = shutil.ignore_patterns("piezas_cache", "deteccion_cache", "desplegado_cache", "cache_ayuda",
                                 "*.bak")
shutil.copytree(os.path.join(R, "entrada"), os.path.join(TMP, "entrada"))
shutil.copytree(os.path.join(R, "datos"), os.path.join(TMP, "datos"), ignore=_CACHES)
shutil.copytree(os.path.join(R, "catalogo_fuentes"), os.path.join(TMP, "fuentes"))
os.makedirs(os.path.join(TMP, "trabajos"), exist_ok=True)

TRAB, RES = {}, {}
_ids = itertools.count(max(CFGM or [0]) + 1)
f = types.ModuleType("db")
f.__getattr__ = lambda n: (lambda *a, **k: None)
f.driver_disponible = lambda: False
f.get_doc = lambda c, default=None: json.loads(json.dumps(DOCS[c])) if c in DOCS else default
# la VERSIÓN de cada doc avanza con cada guardado, como en la base: si quedaba siempre en 1, `catalogo_rev` no
# cambiaba nunca y el aviso «el catálogo cambió» a las pantallas abiertas no se podía probar en el sandbox (MAPA 804)
VER = {}
f.get_doc_ver = lambda c, default=None: (f.get_doc(c, default), VER.get(c, 1))
f.doc_existe = lambda c: c in DOCS
def _set(c, o, version_esperada=None):
    DOCS[c] = json.loads(json.dumps(o)); VER[c] = VER.get(c, 1) + 1; return VER[c]
f.set_doc = _set
f.guardar_catalogo = lambda cat, version_esperada=None, solo=None: _set("catalogo", cat)
f.registro_rev = lambda pid: (1 if pid in REG else None)
f.leer_registro = lambda pid: REG.get(pid)
f.guardar_registro = lambda pid, piezas, reg: REG.__setitem__(pid, reg)
f.borrar_piezas_molde = lambda pid, cur=None: REG.pop(pid, None)
f.borrar_producto = lambda pid: REG.pop(pid, None)
f.filas = lambda sql, *a, **k: ([{"legacy_id": p, "registro_rev": 1} for p in REG]
                                if "registro_rev" in str(sql) else [])
f.valor = lambda sql, *a, **k: None
f.fila = lambda sql, *a, **k: None
# trabajos en memoria (la pantalla sondea su estado)
def _tc(lid, usuario_id=None, molde_nombre=None, moldes=None):
    TRAB[lid] = {"estado": "en cola", "progreso": "", "resultado": None, "error": None, "cancelar": False,
                 "creado_por": usuario_id, "molde_nombre": molde_nombre or "", "moldes": moldes or "",
                 "creado": time.time()}
def _ta(lid, **c):
    t = TRAB.get(lid)
    if not t: return 0
    for k in ("estado", "progreso", "error", "resultado", "cancelar"):
        if k in c: t[k] = c[k]
    return 1
def _tl(lid):
    t = TRAB.get(lid)
    if not t: return None
    return {"estado": t["estado"] or "en cola", "progreso": t["progreso"] or "", "resultado": t["resultado"],
            "error": t["error"], "cancelar_pedido": bool(t["cancelar"]), "usuario": t["creado_por"],
            "producto_nombre": t["molde_nombre"], "producto_id": t["moldes"], "creado": t["creado"]}
f.trabajo_crear, f.trabajo_actualizar, f.trabajo_leer = _tc, _ta, _tl
f.trabajo_cancelar = lambda lid: _ta(lid, cancelar=True) > 0
f.trabajo_cancelado = lambda lid: bool((TRAB.get(lid) or {}).get("cancelar"))
f.trabajos_podar = lambda horas=6, vivos=200: 0
f.trabajo_borrar = lambda lid: 1 if TRAB.pop(lid, None) else 0
f.trabajos_terminados_de = lambda uid: [k for k, t in TRAB.items()
                                        if t["creado_por"] == uid and t["estado"] in ("listo", "error", "cancelado")]
f.tomar_reserva = lambda rec, uid, usuario=None, segundos=None: (True, {"usuario_id": uid, "usuario": usuario})
f.soltar_reserva = lambda rec, uid: True
f.soltar_reservas_de = lambda uid: 0
f.reservas_vivas = lambda segundos=None: {}
def _gcm(nombre, sha1, molde, piezas_n, mesas_n, datos, creado_por=None, id_=None, huella=None):
    i = int(id_) if id_ and int(id_) in CFGM else next(_ids)
    CFGM[i] = {"id": i, "nombre": nombre, "sha1": sha1, "molde": molde, "piezas_n": piezas_n, "mesas_n": mesas_n,
               "creado_en": time.strftime("%Y-%m-%d %H:%M:%S"), "creado_por": creado_por, "huella": huella,
               "datos": json.loads(json.dumps(datos))}
    return i
f.guardar_config_molde = _gcm
f.listar_configs_molde = lambda creado_por=None, todas=False: [
    {k: v for k, v in c.items() if k != "datos"} for c in CFGM.values()
    if todas or c.get("creado_por") == creado_por]
f.leer_config_molde = lambda i: json.loads(json.dumps(CFGM.get(int(i)), default=str)) if CFGM.get(int(i)) else None
f.borrar_config_molde = lambda i: 1 if CFGM.pop(int(i), None) else 0
sys.modules["db"] = f
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")
import registro as _LG
_LG.usar_carpeta(os.path.join(TMP, "logs"))
import servidor as S
S._USUARIOS_ON = False
# 🔴 SIN SALIDA A INTERNET: la config de publicación se lee de la carpeta REAL del repo (`empaquetar.config_publicacion`,
# no de TIZADA_DATOS) y el sandbox mostraba el estado y los respaldos del PUBLICADO de verdad — un «Publicar» desde
# acá iría a internet (vuelta 22, MAPA 786). En el sandbox apunta a una dirección que no existe.
import empaquetar as _EMP
_SIN_PUB = lambda: {"url": "http://127.0.0.1:9/sandbox-sin-publicado", "token": "sandbox"}
_EMP.config_publicacion = _SIN_PUB
S._pub_cfg = _SIN_PUB
# …ni a la API de STOCK real (la actualización de telas de fondo corre a los 30 s: vuelta 26, MAPA 790)
S._config_externo = lambda: ("http://127.0.0.1:9/sandbox-sin-stock", "sandbox")
# …y PUBLICAR no se hace: escribiría `datos/publicacion.json` y `VERSION` del repo REAL (no la copia) y mandaría el
# paquete afuera. Toda escritura de /api/publicacion/ se rechaza en el sandbox.
from flask import request as _rq, jsonify as _js
@S.app.before_request
def _sin_publicar_en_el_sandbox():
    if _rq.path.startswith("/api/publicacion") and _rq.method not in ("GET", "HEAD", "OPTIONS"):
        return _js({"error": "en el sandbox del inspector no se publica (escribiría el repo real y saldría a internet)"}), 403
# PERFILAR EL HILO DE LA PÁGINA (`SANDBOX_PERFIL_JS=1`): habilita `new Profiler(...)` (JS Self-Profiling, sólo con
# este encabezado) para ver QUÉ traba la pantalla — la congelada de 47 s del pedido de 1000 (MAPA 803).
if os.environ.get("SANDBOX_PERFIL_JS") == "1":
    @S.app.after_request
    def _perfil_js(resp):
        resp.headers["Document-Policy"] = "js-profiling"
        return resp
print("SANDBOX", TMP, "puerto", PUERTO, flush=True)
S.app.run(host="127.0.0.1", port=PUERTO, threaded=True, use_reloader=False)
