# -*- coding: utf-8 -*-
"""
CONTRATO: EL PAQUETE DEL PEDIDO ACEPTA LAS TELAS CON ACENTO Y RECHAZA NOMBRES RAROS — `py verificar_paquete_pedido.py`

`POST /api/paquetes/pedido` (PLAN_NAVEGADOR, etapa 4) valida los nombres de las hojas. El nombre
lleva la tela tal como la escribió el usuario («Jacquard Charrúa»): el slug del motor deja letras y
números de cualquier idioma, y el servidor rebotaba una tizada entera por un acento (2026-09-18,
«nombre de hoja que no corresponde»). Acá: una hoja con acento se guarda como un trabajo más; un
nombre con `..` o espacios se rechaza con 400.

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
_TMP = tempfile.mkdtemp(prefix="verif_paq_pedido_")
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
_LG.usar_carpeta(tempfile.mkdtemp(prefix="verif_paq_pedido_logs_"))
import servidor as S                          # noqa: E402

S._USUARIOS_ON = False
CLI = S.app.test_client()
FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK    " if cond else "  FALLA ") + msg)


import io as _io                               # noqa: E402
import pymupdf                                 # noqa: E402

PID = "pP"
_DOCS["catalogo"] = {"activo": PID, "productos": [{"id": PID, "nombre": "Molde de prueba"}]}
os.makedirs(os.path.join(_TMP, "productos", PID), exist_ok=True)


def pdf_de(paginas=1):
    d = pymupdf.open()
    for _ in range(paginas):
        d.new_page(width=500, height=700)
    b = d.tobytes()
    d.close()
    return b


def mandar(nombre_hoja, paginas=1):
    res = {"hojas": [{"tela": "Jacquard Charrúa (1,83)", "archivo": nombre_hoja, "paginas": paginas, "consumo_cm": 100.0,
                      "alturas_cm": [100.0] * paginas, "ancho_cm": 183.0, "aprovechamiento": 50.0, "previews": [],
                      "grupo": "g0", "moldes": ["Molde de prueba"]}],
           "validaciones": [], "duracion_s": 1.0, "piezas": 3, "avisos": [], "avisos_pedido": [], "perfil_icc": None, "ficha": None}
    datos = {"resultado": json.dumps(res), "prendas": json.dumps([{"talle": "M"}]), "nombres": json.dumps(["Molde de prueba"]),
             "pids": json.dumps([PID]), nombre_hoja: (_io.BytesIO(pdf_de(paginas)), nombre_hoja)}
    return CLI.post("/api/paquetes/pedido", data=datos, content_type="multipart/form-data")


print(chr(10) + "1 · UNA TELA CON ACENTO PASA")
r = mandar("HOJA_g0_Jacquard_Charrúa__1_83_.pdf")
d = r.get_json() or {}
ok(r.status_code == 200 and d.get("id"), f"la hoja «HOJA_g0_Jacquard_Charrúa__1_83_.pdf» se guardó (HTTP {r.status_code}: {d.get('error') or d.get('id')})")
if d.get("id"):
    ok(os.path.exists(os.path.join(_TMP, "trabajos", d["id"], "HOJA_g0_Jacquard_Charrúa__1_83_.pdf")), "y el archivo quedó en el trabajo con ese nombre")
    ok((d.get("resultado") or {}).get("navegador") is True, "marcado como generado por el navegador")

print(chr(10) + "2 · LOS NOMBRES RAROS SE RECHAZAN")
for nom in ("HOJA_../x.pdf", "HOJA_g0 con espacio.pdf", "hoja_g0.pdf", "HOJA_g0.txt"):
    r = mandar(nom)
    ok(r.status_code == 400, f"«{nom}» → {r.status_code}")

shutil.rmtree(_TMP, ignore_errors=True)
print()
if FALLOS:
    print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
    for f in FALLOS:
        print("   · " + f)
    sys.exit(1)
print("✅ CONTRATO VERDE — el paquete del pedido acepta las telas con acento y rechaza los nombres raros")
