# -*- coding: utf-8 -*-
"""CONTRATO: LAS TIZADAS SE VAN CON «NUEVO PEDIDO» — `py verificar_trabajos_se_borran.py`

Regla del usuario (2026-09-11): «después que pusieron nuevo pedido eso se borra y listo». Los PDF
de `trabajos/<id>` no se acumulan más en el servidor.

Lo que se prueba, sobre una carpeta TEMPORAL y una base DE MENTIRA (nunca `trabajos/` real):
  1. las tizadas anotadas por la pantalla se borran (carpeta + fila + memoria);
  2. una que está GENERANDO no se toca;
  3. un id con forma de ruta se ignora (nada de `../`);
  4. `incluir_anteriores` se lleva también las terminadas que la pantalla no tenía;
  5. con usuarios, la de OTRO usuario no se toca aunque la pantalla la mande;
  6. el confirmar de «Nuevo pedido» AVISA que las tizadas se borran.

⚠️ No escribe en `trabajos/`, `datos/` ni en la base.
"""
import io
import os
import shutil
import sys
import tempfile
import types

sys.stdout.reconfigure(encoding="utf-8")
_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")

import tempfile as _tmp_log, registro as _LOG_PRUEBA   # noqa: E402
_LOG_PRUEBA.usar_carpeta(_tmp_log.mkdtemp(prefix="verif_logs_"))
import servidor as S   # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)


# ── base de mentira ──────────────────────────────────────────────────────────────────────────
FILAS = {}          # legacy_id → {"estado", "usuario"}


def _leer(tid):
    d = FILAS.get(tid)
    return {"estado": d["estado"], "usuario": d.get("usuario")} if d else None


def _borrar(tid):
    return 1 if FILAS.pop(tid, None) is not None else 0


def _terminados_de(uid):
    return [k for k, v in FILAS.items() if v.get("usuario") == uid and v["estado"] in ("listo", "error", "cancelado")]


S.db.trabajo_leer = _leer
S.db.trabajo_borrar = _borrar
S.db.trabajos_terminados_de = _terminados_de

TMP = tempfile.mkdtemp(prefix="verif_trabajos_")
S.TRABAJOS = TMP
S.trabajos.clear()


def carpeta(tid, estado="listo", usuario=None, en_memoria=False):
    os.makedirs(os.path.join(TMP, tid), exist_ok=True)
    io.open(os.path.join(TMP, tid, "HOJA.pdf"), "w").write("x")
    FILAS[tid] = {"estado": estado, "usuario": usuario}
    if en_memoria:
        S.trabajos[tid] = {"estado": estado, "usuario": usuario}


def llamar(cuerpo):
    with S.app.test_request_context("/api/pedido/limpiar_trabajos", method="POST", json=cuerpo):
        r = S.limpiar_trabajos()
        return r.get_json() if hasattr(r, "get_json") else r[0].get_json()


def existe(tid):
    return os.path.isdir(os.path.join(TMP, tid))


try:
    # ── 1-3: sin usuarios (taller) ───────────────────────────────────────────────────────────
    S._USUARIOS_ON = False
    carpeta("20260911-100000-aaaa")
    carpeta("20260911-100100-bbbb", estado="generando", en_memoria=True)
    carpeta("20260911-100200-cccc", estado="error")
    r = llamar({"ids": ["20260911-100000-aaaa", "20260911-100100-bbbb", "../datos"]})
    ok("20260911-100000-aaaa" in r["borrados"] and not existe("20260911-100000-aaaa"), "la tizada anotada no se borró")
    ok("20260911-100000-aaaa" not in FILAS, "la fila de la base quedó")
    ok("20260911-100100-bbbb" in r["ignorados"] and existe("20260911-100100-bbbb"), "se borró una tizada que estaba GENERANDO")
    ok("../datos" in r["ignorados"], "un id con forma de ruta no se ignoró")
    ok(existe("20260911-100200-cccc"), "borró una que la pantalla NO mandó (sin incluir_anteriores)")
    print("  · anotada: borrada · generando: intacta · «../datos»: ignorado")

    # ── 4: incluir_anteriores se lleva lo terminado que la pantalla no tenía ─────────────────
    r = llamar({"ids": [], "incluir_anteriores": True})
    ok("20260911-100200-cccc" in r["borrados"] and not existe("20260911-100200-cccc"), "incluir_anteriores no se llevó la terminada")
    ok(existe("20260911-100100-bbbb"), "incluir_anteriores borró la que está generando")
    print("  · incluir_anteriores: la terminada se fue, la que genera sigue")

    # ── 5: con usuarios, la de OTRO no se toca ───────────────────────────────────────────────
    S._USUARIOS_ON = True
    S._uid_actual = lambda: 7
    carpeta("20260911-100300-dddd", usuario=7)
    carpeta("20260911-100400-eeee", usuario=9)
    r = llamar({"ids": ["20260911-100300-dddd", "20260911-100400-eeee"], "incluir_anteriores": True})
    ok("20260911-100300-dddd" in r["borrados"] and not existe("20260911-100300-dddd"), "no borró la mía")
    ok("20260911-100400-eeee" in r["ignorados"] and existe("20260911-100400-eeee"), "🔴 borró la tizada de OTRO usuario")
    print("  · con usuarios: la mía se va, la de otro queda")
finally:
    S.trabajos.clear()
    shutil.rmtree(TMP, ignore_errors=True)

# ── 6: el confirmar avisa ────────────────────────────────────────────────────────────────────
_app = io.open(os.path.join(_AQUI, "frontend", "src", "App.jsx"), encoding="utf-8").read()
ok("Las tizadas generadas en este pedido se borran del servidor" in _app, "el confirmar de «Nuevo pedido» no avisa que las tizadas se borran")
ok("/api/pedido/limpiar_trabajos" in _app and "incluir_anteriores: true" in _app, "«Nuevo pedido» no llama a limpiar_trabajos con incluir_anteriores")
ok("Las tizadas ya generadas y la configuración de los moldes no se tocan" not in _app, "el aviso viejo («no se tocan») sigue")
print("  · el confirmar avisa y el front llama al endpoint")

print()
if FALLOS:
    print("✗ FALLA:")
    for f in FALLOS:
        print("   ·", f)
    sys.exit(1)
print("OK trabajos: «Nuevo pedido» borra las tizadas del pedido (nunca una generando ni una ajena)")
