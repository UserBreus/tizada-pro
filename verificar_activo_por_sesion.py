# -*- coding: utf-8 -*-
"""
CONTRATO: LO QUE ELIGE UNA PERSONA NO LE CAMBIA LA PANTALLA A OTRA — `py verificar_activo_por_sesion.py`

Tres cosas que se veían «en vivo» pero mal (MAPA changelog 481):
  1. `/api/productos` devolvía el molde activo GLOBAL. Elegir un molde lo reescribe y sube la revisión
     del catálogo; en el próximo latido las pantallas de los DEMÁS pedían el catálogo, cambiaban de
     molde, la planilla se vaciaba a 5 filas y el paso Arte lo volvía a activar (pisando al otro).
     Ahora cada sesión recibe SU activo.
  2. Mientras la pestaña que subió un molde prepara sus páginas por talle, las OTRAS pestañas de la
     misma persona ofrecían «Terminar de preparar» (y un clic lo preparaba dos veces). Ahora la
     pestaña que trabaja late (`/api/plantilla/paginas/latido`) y `/api/productos` dice hace cuánto
     (`paginas_navegador_hace`); la pantalla lo ofrece sólo si el latido se cortó.
  3. El nido (piezas acomodadas por talle) no tenía el TALLE GUÍA en su clave de caché: cambiarlo en
     la pantalla seguía mostrando el nido de la guía anterior.

⚠️ No toca nada del usuario: DATOS a un temporal y `db` es un doble (nada de MSSQL).
"""
import json
import os
import sys
import tempfile
import time
import types

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_AQUI = os.path.dirname(os.path.abspath(__file__))
_TMP = tempfile.mkdtemp(prefix="verif_activo_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"

_DOCS = {}
_falso = types.ModuleType("db")
_falso.__getattr__ = lambda n: (lambda *a, **k: None)
_falso.get_doc = lambda c, default=None: _DOCS.get(c, default)
_falso.get_doc_ver = lambda c, default=None: (_DOCS.get(c, default), 0)
_falso.set_doc = lambda c, o, version_esperada=None: (_DOCS.__setitem__(c, o), 1)[-1]
_falso.guardar_catalogo = lambda cat, version_esperada=None: (_DOCS.__setitem__("catalogo", cat), 1)[-1]
_falso.leer_registro = lambda pid: None
sys.modules["db"] = _falso
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")

sys.path.insert(0, _AQUI)
import registro as _LG                        # noqa: E402
_LG.usar_carpeta(tempfile.mkdtemp(prefix="verif_activo_logs_"))
import servidor as S                          # noqa: E402
import piezas_con_diseno as PD                # noqa: E402

S._USUARIOS_ON = False
FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK    " if cond else "  FALLA ") + msg)


_DOCS["catalogo"] = {"activo": "prod_a", "productos": [
    {"id": "prod_a", "nombre": "Molde A"}, {"id": "prod_b", "nombre": "Molde B"}]}

print("\n1 · CADA SESIÓN VE SU MOLDE ACTIVO")
ana, beto = S.app.test_client(), S.app.test_client()
ok(ana.post("/api/productos/activar", json={"id": "prod_a"}).status_code == 200, "Ana elige el molde A")
ok(beto.post("/api/productos/activar", json={"id": "prod_b"}).status_code == 200, "Beto elige el molde B (después)")
_a = ana.get("/api/productos").get_json() or {}
_b = beto.get("/api/productos").get_json() or {}
ok(_a.get("activo") == "prod_a", f"🔴 Ana sigue viendo el A aunque Beto eligió después (ve {_a.get('activo')!r})")
ok(_b.get("activo") == "prod_b", f"y Beto ve el B (ve {_b.get('activo')!r})")
_nuevo = S.app.test_client().get("/api/productos").get_json() or {}
ok(_nuevo.get("activo") in ("prod_a", "prod_b"), f"una sesión que no eligió nada cae al activo general ({_nuevo.get('activo')!r})")

print("\n2 · LAS PÁGINAS QUE PREPARA OTRA PESTAÑA NO SE OFRECEN PARA TERMINAR")
_pl = S._ruta_entrada("plantilla.ai", pid="prod_a", original=True)
os.makedirs(os.path.dirname(_pl), exist_ok=True)
open(_pl, "wb").write(b"%PDF-1.4\n%prueba\n")
_marca = os.path.join(PD._carpeta_desplegado(_pl), PD.PENDIENTE_NAVEGADOR)
os.makedirs(os.path.dirname(_marca), exist_ok=True)
json.dump({"sha1": "x", "desde": time.time()}, open(_marca, "w"))


def _molde_a():
    return next((p for p in (ana.get("/api/productos").get_json() or {}).get("productos", []) if p["id"] == "prod_a"), {})


_p = _molde_a()
ok(_p.get("paginas_navegador") is True and isinstance(_p.get("paginas_navegador_hace"), int)
   and _p["paginas_navegador_hace"] < 45,
   f"recién subido: pendiente y con latido fresco (hace {_p.get('paginas_navegador_hace')} s)")
_viejo = time.time() - 300
os.utime(_marca, (_viejo, _viejo))
_p = _molde_a()
ok((_p.get("paginas_navegador_hace") or 0) >= 290,
   f"si la pestaña dejó de latir, se ve viejo y se ofrece terminar (hace {_p.get('paginas_navegador_hace')} s)")
_r = ana.post("/api/plantilla/paginas/latido", json={"pid": "prod_a"})
_p = _molde_a()
ok(_r.status_code == 200 and (_r.get_json() or {}).get("pendiente") is True and _p.get("paginas_navegador_hace") is not None and _p["paginas_navegador_hace"] < 45,
   f"🔴 el latido lo vuelve fresco: las otras pestañas no lo ofrecen (hace {_p.get('paginas_navegador_hace')} s)")
os.remove(_marca)
_r = ana.post("/api/plantilla/paginas/latido", json={"pid": "prod_a"})
_p = _molde_a()
ok((_r.get_json() or {}).get("pendiente") is False and not os.path.exists(_marca),
   "sin marca, el latido no crea nada")
ok(_p.get("paginas_navegador") is False and _p.get("paginas_navegador_hace") is None,
   "y el molde ya no figura pendiente")
_bid = next((p for p in (beto.get("/api/productos").get_json() or {}).get("productos", []) if p["id"] == "prod_b"), {})
ok(_bid.get("paginas_navegador") is False, "un molde sin archivo no figura pendiente")

print("\n3 · CAMBIAR EL TALLE GUÍA REHACE EL NIDO")
# El nido se arma con `talle_guia` y se guarda en memoria y en disco con una clave. Cambiar la guía
# no toca ningún archivo: si no está en la clave, se seguía mostrando el nido de la guía anterior.
with S.app.test_request_context("/?pid=prod_a"):
    _k1 = S._nido_clave()
    next(p for p in _DOCS["catalogo"]["productos"] if p["id"] == "prod_a")["variante_guia"] = "XL"
    _k2 = S._nido_clave()
ok(_k1 != _k2 and "XL" in _k2, f"🔴 la clave del nido cambia con el talle guía ({_k1[-1]!r} → {_k2[-1]!r})")

print()
if FALLOS:
    print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
    for f in FALLOS:
        print("   · " + f)
    sys.exit(1)
print("✅ CONTRATO VERDE — lo que elige una persona no le cambia la pantalla a otra, y las páginas en preparación no se ofrecen dos veces")
