# -*- coding: utf-8 -*-
"""
CONTRATO DEL GUARDADO DE TUTORIALES — se corre con `py verificar_tutorial_ventana.py`.

El caso que lo motivó (2026-08-28): un paso grabado DENTRO de una ventana emergente (el
«Entendido» del Perfil de color) llegaba al editor como un chip suelto — «este paso se hace en
una ventana emergente y no la veo a la ventana». El grabador ahora guarda `ventana` (el título
del [data-modal] donde cayó el clic) y el sanitizador del server tiene que PERSISTIRLA: sin eso
el editor no puede dibujar la ventanita ni la reproducción explicar dónde vive el paso.

También cubre lo que el sanitizador ya hacía y nadie vigilaba: texto y modal sobreviven al
guardado, la basura se recorta, y los campos del CICLO DE DISEÑOS (eliminado 2026-08-28:
`vuelta`/`mid`/`repite`/`solo`) ya no entran ni aunque los manden.

⚠️ No toca nada del usuario: el módulo `db` se reemplaza por un doble que explota (ver
[[test-no-toca-mssql]]) y `DATOS` va a un temporal.
"""
import os
import sys
import tempfile
import types

# la consola de Windows es cp1252: sin esto los emojis del reporte revientan
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_TMP = tempfile.mkdtemp(prefix="verif_tut_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"

_falso_db = types.ModuleType("db")
_falso_db.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(
    AssertionError(f"LA PRUEBA INTENTO TOCAR MSSQL (db.{n}) — revisar el aislamiento")))
# El catalogo vive en la base (get_doc/set_doc): el doble lo imita EN MEMORIA, igual que
# verificar_config_concurrente.py — todo lo demas sigue explotando.
import copy as _cp
_DOCS = {}
_falso_db.set_doc = lambda c, o: _DOCS.__setitem__(c, _cp.deepcopy(o))
_falso_db.get_doc = lambda c, default=None: _cp.deepcopy(_DOCS.get(c, default))
# Desde 2026-09-07 el catálogo se guarda con `guardar_catalogo` (documento + proyección a las
# tablas, en UNA transacción). El doble imita el documento, que es lo que la app vuelve a leer.
_falso_db.guardar_catalogo = lambda cat: _DOCS.__setitem__("catalogo", _cp.deepcopy(cat))
_falso_db.proyectar_catalogo = lambda cat: None   # la proyeccion a tablas no aplica en memoria
sys.modules["db"] = _falso_db

# Sin sistema de usuarios (mismo saboteo que srv_visor): el import de `bp` falla,
# _USUARIOS_ON queda en False y el server no exige sesion — la prueba entra sola.
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# 🔴 El registro de la prueba va a un temporal, y se engancha ANTES de importar `servidor`
# (que espeja la consola al importarse): un test no puede ensuciar el registro del sistema
# de verdad — si no, mañana alguien investiga una falla que provocó una prueba.
import tempfile as _tmp_log, registro as _LOG_PRUEBA   # noqa: E402
_LOG_PRUEBA.usar_carpeta(_tmp_log.mkdtemp(prefix="verif_logs_"))
import servidor as S               # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK   " if cond else "  FALLA") + " " + msg)


c = S.app.test_client()

# ── 1) el paso con `ventana` la conserva al guardar y al leer ───────────────────────────────
r = c.post("/api/tutoriales", json={
    "nombre": "prueba ventana",
    "pasos": [
        {"ancla": "pedido-diseno-lista", "accion": "click", "etiqueta": "JUGADOR",
         "donde": {"tab": "pedidos", "paso": "diseno"}},
        {"ancla": "txt:entendido", "accion": "click", "etiqueta": "Entendido",
         "ventana": "Perfil de color del diseño",
         "texto": "Cerrá el aviso del perfil", "donde": {"tab": "pedidos", "paso": "arte"}},
        {"accion": "modal", "modal": "Poniendo el diseño sobre el molde", "donde": {}},
        {"ancla": "arte-telas", "accion": "click", "donde": {}},
    ],
})
ok(r.status_code == 200, f"el POST guarda (status {r.status_code})")
tid = (r.get_json() or {}).get("tutorial", {}).get("id")
pasos = (r.get_json() or {}).get("tutorial", {}).get("pasos") or []
p_v = next((p for p in pasos if p.get("ancla") == "txt:entendido"), {})
ok(p_v.get("ventana") == "Perfil de color del diseño",
   "🔴 el paso grabado dentro de una ventana PERSISTE su `ventana`")
ok(p_v.get("texto") == "Cerrá el aviso del perfil", "el texto corregido a mano persiste")
ok(not any(p.get("ventana") for p in pasos if p.get("ancla") == "pedido-diseno-lista"),
   "un paso sin ventana no la inventa")
ok(not any(p.get("mid") or p.get("repite") or p.get("solo") or p.get("vuelta2") for p in pasos),
   "🔴 los campos del ciclo de diseños NO se guardan (esa lógica se eliminó)")
ok(not any(p.get("accion") == "vuelta" for p in pasos),
   "una marca «↻» vieja no entra ni aunque la manden")

# lo que devuelve el GET es lo mismo que quedó guardado
r2 = c.get("/api/tutoriales")
t2 = next((t for t in (r2.get_json() or {}).get("tutoriales", []) if t.get("id") == tid), {})
p2 = next((p for p in t2.get("pasos", []) if p.get("ancla") == "txt:entendido"), {})
ok(p2.get("ventana") == "Perfil de color del diseño", "el GET devuelve la ventana del paso")

# ── 2) la basura se recorta ─────────────────────────────────────────────────────────────────
r3 = c.post("/api/tutoriales", json={
    "nombre": "prueba basura",
    "pasos": [{"ancla": "x", "accion": "click", "ventana": "V" * 500, "donde": {}}],
})
p3 = ((r3.get_json() or {}).get("tutorial", {}).get("pasos") or [{}])[0]
ok(len(p3.get("ventana") or "") == 80, "una ventana kilométrica se recorta a 80")
ok("solo" not in p3, "un `solo` (condición por cantidad de diseños) ya no se guarda")

# ── 3) SEGURIDAD: grabar un tutorial es del ADMIN ───────────────────────────────────────────
# Ocultar el botón NO es seguridad: el endpoint tiene que rechazar igual a quien no tiene el
# permiso `ayuda.grabar` (pedido del usuario 2026-08-28: «los tutoriales los puede crear un admin
# nomás»). Se simula el sistema de usuarios prendido con distintos usuarios.
import api_usuarios as _au   # el doble que se registró arriba (módulo vacío)

S._USUARIOS_ON = True
try:
    for quien, permisos, esperado in [
        (None, [], 401),                                   # sin sesión
        ({"id": 1, "permisos": ["pedido.crear"]}, None, 403),   # operario: no puede
        ({"id": 2, "permisos": ["ayuda.grabar"]}, None, 200),   # admin: puede
    ]:
        _au.usuario_actual = (lambda q: (lambda: q))(quien)
        r = c.post("/api/tutoriales", json={"nombre": "seguridad",
                                            "pasos": [{"ancla": "x", "accion": "click", "donde": {}}]})
        ok(r.status_code == esperado,
           f"POST /api/tutoriales con {'sin sesión' if quien is None else 'permisos ' + str(quien['permisos'])}"
           f" → {esperado} (dio {r.status_code})")
    # y borrar, lo mismo
    _au.usuario_actual = lambda: {"id": 1, "permisos": ["pedido.crear"]}
    r = c.post("/api/tutoriales/borrar", json={"id": "lo-que-sea"})
    ok(r.status_code == 403, f"🔴 borrar un tutorial sin permiso → 403 (dio {r.status_code})")
    # VER la ayuda no pide nada: es para todos
    _au.usuario_actual = lambda: {"id": 1, "permisos": []}
    ok(c.get("/api/tutoriales").status_code == 200, "VER los tutoriales no pide permiso (la ayuda es para todos)")
finally:
    S._USUARIOS_ON = False
    if hasattr(_au, "usuario_actual"):
        del _au.usuario_actual

print()
if FALLOS:
    print(f"  {len(FALLOS)} FALLO(S)")
    sys.exit(1)
print("  OK: el guardado conserva ventana/texto, recorta la basura y no deja entrar el ciclo viejo")
