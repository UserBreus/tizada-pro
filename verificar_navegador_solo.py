# -*- coding: utf-8 -*-
"""
CONTRATO: CON «EL SERVIDOR NO CALCULA» PRENDIDO, EL SERVIDOR RECHAZA TODO LO PESADO — `py verificar_navegador_solo.py`

PLAN_NAVEGADOR.md, etapa 6 (cierre). El interruptor vive en el catálogo (`navegador_solo`, se
prende desde Configuración → Molde con diseño → `POST /api/config_con_diseno`) y el entorno
(`TIZADA_SOLO_NAVEGADOR`) manda si está. Prendido: un molde sin paquete (con o sin diseño), un
arte sin paquete y una tizada del camino B pedida al servidor contestan 409 con el motivo, y
ninguna función pesada corre. Apagado: el servidor sigue preparando (red de seguridad).

⚠️ No toca nada del usuario: DATOS a un temporal y `db` es un doble.
"""
import json
import os
import shutil
import sys
import tempfile
import time
import types

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_AQUI = os.path.dirname(os.path.abspath(__file__))
_TMP = tempfile.mkdtemp(prefix="verif_solo_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"
os.environ.pop("TIZADA_SOLO_NAVEGADOR", None)

_DOCS, _TRAB = {}, {}
_falso = types.ModuleType("db")
_falso.__getattr__ = lambda n: (lambda *a, **k: None)
_falso.get_doc = lambda c, default=None: _DOCS.get(c, default)
_falso.get_doc_ver = lambda c, default=None: (_DOCS.get(c, default), 0)
_falso.set_doc = lambda c, o, version_esperada=None: (_DOCS.__setitem__(c, o), 1)[-1]
_falso.guardar_catalogo = lambda cat, version_esperada=None: (_DOCS.__setitem__("catalogo", cat), 1)[-1]
_falso.registro_rev = lambda pid: None
_falso.leer_registro = lambda pid: None
_falso.trabajo_crear = lambda legacy_id, **k: _TRAB.__setitem__(legacy_id, {"estado": "en cola"})
_falso.trabajo_actualizar = lambda legacy_id, **k: (_TRAB.setdefault(legacy_id, {}).update(k), 1)[-1]
_falso.trabajo_leer = lambda tid: (dict(_TRAB[tid]) if tid in _TRAB else None)
_falso.trabajo_cancelado = lambda tid: False
_falso.trabajos_podar = lambda horas=6, vivos=200: 0
sys.modules["db"] = _falso
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")

sys.path.insert(0, _AQUI)
import registro as _LG                        # noqa: E402
_LG.usar_carpeta(tempfile.mkdtemp(prefix="verif_solo_logs_"))
import servidor as S                          # noqa: E402
import motor_pedido as MP                     # noqa: E402
import piezas_con_diseno as PD                # noqa: E402
import importar_dxf                           # noqa: E402

S._USUARIOS_ON = False
CLI = S.app.test_client()
FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK    " if cond else "  FALLA ") + msg)


_LLAMADAS = []


def _prohibido(nombre):
    def _f(*a, **k):
        _LLAMADAS.append(nombre)
        raise RuntimeError(f"el servidor intentó {nombre} con «el servidor no calcula» prendido")
    return _f


MP.alta_plantilla = _prohibido("alta_plantilla")
MP.alta_plantilla_manual = _prohibido("alta_plantilla_manual")
MP.detectar_piezas = _prohibido("detectar_piezas")
PD.alta_molde_con_diseno = _prohibido("alta_molde_con_diseno")
MP.detectar_arte = _prohibido("detectar_arte")
MP.validar_arte_separado = _prohibido("validar_arte_separado")
MP.validar_arte = _prohibido("validar_arte")
importar_dxf.dxf_a_pdf = _prohibido("dxf_a_pdf")

PID = "pS"
_DOCS["catalogo"] = {"activo": PID, "productos": [{"id": PID, "nombre": "Molde de prueba"}]}
os.makedirs(os.path.join(_TMP, "entrada", PID), exist_ok=True)
os.makedirs(os.path.join(_TMP, "productos", PID), exist_ok=True)
_ORIG = os.path.join(_AQUI, "entrada", "prod_20260911_165624_1ed7", "plantilla.ai")
if not os.path.exists(_ORIG):
    print("  (no está el molde de prueba: se saltea)")
    sys.exit(0)
_COPIA = os.path.join(_TMP, "molde.ai")
shutil.copy2(_ORIG, _COPIA)


def subir_molde(con_diseno):
    with open(_COPIA, "rb") as fh:
        r = CLI.post("/api/plantilla", data={"archivo": (fh, "molde.ai"), "pid": PID, "con_diseno": con_diseno}, content_type="multipart/form-data")
    d = r.get_json() or {}
    if r.status_code == 200 and d.get("job"):
        for _ in range(600):
            e = _TRAB.get(d["job"]) or {}
            if e.get("estado") in ("listo", "error"):
                return r.status_code, e
            time.sleep(0.1)
    return r.status_code, d


print("\n1 · EL INTERRUPTOR SE GUARDA DESDE LA PANTALLA")
c0 = CLI.get("/api/config_con_diseno").get_json() or {}
ok(c0.get("navegador_solo") is False and c0.get("navegador_solo_forzado") is False, f"arranca apagado y libre ({c0.get('navegador_solo')}, forzado={c0.get('navegador_solo_forzado')})")
r = CLI.post("/api/config_con_diseno", json={"navegador_solo": True})
ok(r.status_code == 200 and (r.get_json() or {}).get("navegador_solo") is True, f"se prende desde `POST /api/config_con_diseno` ({r.status_code})")
ok(_DOCS["catalogo"].get("navegador_solo") is True, "y queda en el catálogo (`navegador_solo`)")
ok((CLI.get("/api/navegador/config").get_json() or {}).get("solo") is True, "`/api/navegador/config` lo dice (`solo: true`)")
ok(S._solo_navegador() is True, "`_solo_navegador()` lo lee del catálogo")

print("\n2 · PRENDIDO, NADA PESADO CORRE EN EL SERVIDOR")
st, d = subir_molde("0")
ok(st == 409 or (d.get("estado") == "error" and "computadora" in str(d.get("error"))),
   f"un molde SIN diseño sin paquete se rechaza con el motivo (HTTP {st}: {str(d.get('error') or d)[:90]})")
st, d = subir_molde("1")
ok(st == 409 or (d.get("estado") == "error" and "computadora" in str(d.get("error"))),
   f"un molde CON diseño sin paquete se rechaza con el motivo (HTTP {st}: {str(d.get('error') or d)[:90]})")
# el arte: hace falta una plantilla en su lugar para llegar al chequeo
shutil.copy2(_COPIA, S._ruta_entrada("plantilla.ai", pid=PID, original=True))
with open(_COPIA, "rb") as fh:
    r = CLI.post("/api/arte", data={"archivo": (fh, "arte.ai"), "pid": PID}, content_type="multipart/form-data")
ok(r.status_code == 409 and "computadora" in str((r.get_json() or {}).get("error")), f"un arte sin paquete se rechaza con el motivo (HTTP {r.status_code}: {str((r.get_json() or {}).get('error'))[:90]})")
ok(not _LLAMADAS, f"y no corrió ninguna función pesada ({_LLAMADAS or 'ninguna'})")

print("\n3 · EL ENTORNO MANDA SI ESTÁ")
os.environ["TIZADA_SOLO_NAVEGADOR"] = "0"
ok(S._solo_navegador() is False, "`TIZADA_SOLO_NAVEGADOR=0` lo apaga aunque el catálogo lo tenga prendido")
ok((CLI.get("/api/config_con_diseno").get_json() or {}).get("navegador_solo_forzado") is True, "y la pantalla sabe que lo fija el entorno")
os.environ["TIZADA_SOLO_NAVEGADOR"] = "1"
ok(S._solo_navegador() is True, "`TIZADA_SOLO_NAVEGADOR=1` lo prende")
os.environ.pop("TIZADA_SOLO_NAVEGADOR", None)

print("\n4 · APAGADO, EL SERVIDOR VUELVE A SER LA RED DE SEGURIDAD")
r = CLI.post("/api/config_con_diseno", json={"navegador_solo": False})
ok(r.status_code == 200 and (r.get_json() or {}).get("navegador_solo") is False, "se apaga desde la pantalla")
_LLAMADAS.clear()
st, d = subir_molde("0")
ok("alta_plantilla" in _LLAMADAS, f"un molde sin paquete vuelve a prepararlo el servidor ({_LLAMADAS or 'no corrió'})")

shutil.rmtree(_TMP, ignore_errors=True)
print()
if FALLOS:
    print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
    for f in FALLOS:
        print("   · " + f)
    sys.exit(1)
print("✅ CONTRATO VERDE — «el servidor no calcula» se prende desde la pantalla y el servidor rechaza lo pesado")
