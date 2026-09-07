# -*- coding: utf-8 -*-
"""CONTRATO DEL NOMBRE EN LA ETIQUETA — `py verificar_etiqueta_nombre.py`

Regla del usuario (2026-08-21): en la etiqueta de corte va el **nombre GENERAL** de la pieza,
**sin el número al lado** — «Frente 9» se rotula «Frente». Las piezas homónimas se distinguen por
el `#nro` que la propia etiqueta ya trae.

Se verifica con el MOTOR REAL: se intercepta `_eops_borde` —quien recibe el texto que se dibuja
sobre el borde— y se mira exactamente qué string llegó.

⚠️ NO TOCA NADA DEL USUARIO:
  · `datos`/`entrada` se copian a un temporal y el motor trabaja ahí (`TIZADA_DATOS`/`TIZADA_ENTRADA`).
  · El registro de piezas vive en **MSSQL**: se lee UNA vez con el `db` real (sólo lectura) y se
    vuelca al temporal; después se reemplaza el módulo `db` por un doble que explota si alguien
    intenta tocar la base (ver [[test-no-toca-mssql]]).
"""
import json
import os
import re
import shutil
import sys
import tempfile
import types

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

# ── 1. Elegir molde y LEER EL REGISTRO DE LA BASE (única lectura real) ──────────────────────
try:
    _cat = json.load(open(os.path.join(RAIZ, "datos", "productos_catalogo.json"), encoding="utf-8"))
except Exception as e:
    print(f"no se pudo leer el catálogo: {e}")
    sys.exit(1)

import db as _db_real   # noqa: E402

_cands = []
for _p in (_cat.get("productos") or []):
    _pid = _p.get("id")
    if not (_pid and os.path.exists(os.path.join(RAIZ, "entrada", _pid, "plantilla.ai"))):
        continue
    try:
        _reg = _db_real.leer_registro(_pid)
    except Exception as e:
        print(f"  (no se pudo leer el registro de {_pid}: {str(e)[:70]})")
        _reg = None
    if not _reg:
        continue
    # se prefiere el que tenga piezas NUMERADAS: es el caso que se está verificando
    _num = sum(1 for n in _reg if re.search(r"\s+\d+\s*$", str(n)))
    _cands.append({"pid": _pid, "nombre": _p.get("nombre"), "reg": _reg, "num": _num, "prod": _p})

if not _cands:
    print("No hay ningún molde con plantilla + registro: no se puede verificar.")
    sys.exit(1)
_cands.sort(key=lambda c: (c["num"], len(c["reg"])), reverse=True)
_M = _cands[0]
PID, REG = _M["pid"], _M["reg"]

# un diseño con arte cargado (si hay)
DISENO = "principal"
for _d in (_M["prod"].get("disenos") or []):
    _nom = _d.get("nombre") if isinstance(_d, dict) else _d
    _slug = re.sub(r"[^a-z0-9]+", "-", str(_nom or "").lower()).strip("-")[:48] or "principal"
    if os.path.exists(os.path.join(RAIZ, "entrada", PID, "disenos", _slug, "arte.ai")):
        DISENO = _nom
        break

# ── 2. Sandbox: copia de los datos + doble de `db` ──────────────────────────────────────────
_TMP = tempfile.mkdtemp(prefix="verif_etq_nom_")
_DATOS, _ENTRADA = os.path.join(_TMP, "datos"), os.path.join(_TMP, "entrada")
os.environ.update({"TIZADA_DATOS": _DATOS, "TIZADA_ENTRADA": _ENTRADA,
                   "TIZADA_TRABAJOS": os.path.join(_TMP, "trabajos"),
                   "TIZADA_FUENTES": os.path.join(RAIZ, "catalogo_fuentes"),
                   "TIZADA_DB_SERVER": r"localhost\NO_EXISTE_ES_UNA_PRUEBA"})

os.makedirs(os.path.join(_DATOS, "productos", PID), exist_ok=True)
for _f in os.listdir(os.path.join(RAIZ, "datos")):
    _o = os.path.join(RAIZ, "datos", _f)
    if os.path.isfile(_o):
        shutil.copy2(_o, os.path.join(_DATOS, _f))
for _f in os.listdir(os.path.join(RAIZ, "datos", "productos", PID)):
    _o = os.path.join(RAIZ, "datos", "productos", PID, _f)
    _d = os.path.join(_DATOS, "productos", PID, _f)
    (shutil.copytree if os.path.isdir(_o) else shutil.copy2)(_o, _d)
shutil.copytree(os.path.join(RAIZ, "entrada", PID), os.path.join(_ENTRADA, PID))
# el registro de la base, volcado al temporal (de ahí lo lee el doble)
json.dump(REG, open(os.path.join(_DATOS, "productos", PID, "registro_producto.json"), "w",
                    encoding="utf-8"), ensure_ascii=False)

_falso = types.ModuleType("db")
_falso.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(
    AssertionError(f"LA PRUEBA INTENTO TOCAR MSSQL (db.{n}) — revisar el aislamiento")))
_REG_MEM = {PID: REG}
_falso.leer_registro = lambda pid: _REG_MEM.get(pid)
_falso.registro_rev = lambda pid: (1 if _REG_MEM.get(pid) is not None else None)
_falso.guardar_registro = lambda pid, piezas, reg: (_REG_MEM.__setitem__(pid, reg), 1)[-1]
_falso.borrar_piezas_molde = lambda pid: (_REG_MEM.pop(pid, None), 0)[-1]
sys.modules["db"] = _falso

import motor_pedido as MP      # noqa: E402
# 🔴 El registro de la prueba va a un temporal, y se engancha ANTES de importar `servidor`
# (que espeja la consola al importarse): un test no puede ensuciar el registro del sistema
# de verdad — si no, mañana alguien investiga una falla que provocó una prueba.
import tempfile as _tmp_log, registro as _LOG_PRUEBA   # noqa: E402
_LOG_PRUEBA.usar_carpeta(_tmp_log.mkdtemp(prefix="verif_logs_"))
import servidor as S           # noqa: E402

FALLOS = []


def ok(cond, que):
    print(("  OK    " if cond else "  FALLA ") + que)
    if not cond:
        FALLOS.append(que)


# ── 3. Espiar el texto que se manda a dibujar ───────────────────────────────────────────────
_TEXTOS = []
_orig = MP._eops_borde


def _espia(cont, Sc, x0, y0, B, rx, ry, t, texto, size, align, fetq, bc_activo=False):
    _TEXTOS.append(texto)
    return _orig(cont, Sc, x0, y0, B, rx, ry, t, texto, size, align, fetq, bc_activo)


MP._eops_borde = _espia


def _textos(mostrar):
    """Genera las piezas de una fila con la etiqueta pedida y devuelve los textos dibujados."""
    cat = S._cargar_catalogo()
    prod = next(p for p in cat["productos"] if p["id"] == PID)
    etq = dict(prod.get("etiqueta") or {})
    etq.update({"activo": True, "mostrar": mostrar, "zonas": {}, "piezas_off": []})
    etq.setdefault("separador", "-")
    sub = S._diseno_sub(DISENO)
    pl, arte = S._ruta_entrada("plantilla.ai", PID), S._ruta_entrada("arte.ai", PID, sub=sub)
    _b, _pv = S._mapeo_estructura(PID, sub=sub)
    mapeo = {"mapeo": _b or {}, "por_variable": _pv} if (_b or _pv) else None
    _cfg_n, _rot, telas, asig = S._config_produccion(PID)
    # fila de MUESTRA (no es un pedido): sin el filtro de columnas obligatorias de la
    # plantilla, que si no la descarta y esta prueba se queda sin piezas.
    prendas = S._traducir_prendas([{"talle": "M"}], prod, cat, DISENO, reg=REG,
                                  exigir_obligatorias=False)
    tmp = tempfile.mkdtemp()
    _TEXTOS.clear()
    try:
        ppt = MP.generar_pedido(pl, arte, REG, MP.extraer_personalizacion(arte), prendas, S.FUENTES,
                                tmp, mapeo_arte=mapeo, solo_piezas=True, asignacion_tela=asig,
                                telas_cfg=telas, borde_corte=prod.get("borde_corte"), etiqueta=etq,
                                editables_cfg=S._editables_cfg(prod, DISENO),
                                editables_tamano=S._editables_tamano(prod),
                                editables_color=S._editables_color(prod, DISENO),
                                objetos_agregados=S._objetos_agregados_motor(PID, sub))
        for _t, pzs in (ppt or {}).items():
            for pz in pzs:
                pz["doc"].close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return list(_TEXTOS)


def _gen(n):
    return re.sub(r"\s+\d+\s*$", "", str(n)).strip()


_numeradas = sorted(n for n in REG if re.search(r"\s+\d+\s*$", str(n)))
print(f"molde: {_M['nombre']} ({PID}) · diseño «{DISENO}» · {len(REG)} piezas, "
      f"{len(_numeradas)} numeradas"
      + ("" if _numeradas else "  ⚠️ ninguna numerada: el caso principal no se puede probar"))

# ── 4. LO QUE IMPORTA: el nombre va SIN el número ───────────────────────────────────────────
txts = _textos({"talle": True, "pieza": True, "numero": True})
print(f"  textos dibujados ({len(txts)}): {txts[:5]}{' …' if len(txts) > 5 else ''}")
ok(bool(txts), "la etiqueta se dibuja (si no, lo demás no prueba nada)")
if txts:
    _malos = [t for t in txts if re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]\s+\d+(-|$)", t)]
    ok(not _malos, f"ningún nombre de pieza sale numerado (salieron: {_malos[:3]})")
    ok(all(re.match(r"^M-.+-#\d{2}$", t) for t in txts),
       f"formato «talle-nombre-#nro» en todos: {txts[:3]}")
    if _numeradas:
        _esperados = {_gen(n) for n in _numeradas}
        _vistos = {t.split("-")[1] for t in txts if len(t.split("-")) >= 3}
        ok(bool(_esperados & _vistos),
           f"las piezas numeradas se rotulan con su nombre general (esperado alguno de "
           f"{sorted(_esperados)[:3]}, salieron {sorted(_vistos)[:3]})")
        ok(not any(f"-{n}-" in t for n in _numeradas for t in txts),
           "ninguna etiqueta trae el nombre numerado tal cual")

# ── 5. Controles: las opciones de «mostrar» siguen funcionando ──────────────────────────────
txt2 = _textos({"talle": True, "pieza": False, "numero": True})
ok(bool(txt2) and all(re.match(r"^M-#\d{2}$", t) for t in txt2),
   f"con «pieza» apagado va sólo talle y número: {txt2[:3]}")

txt3 = _textos({"talle": False, "pieza": True, "numero": False})
ok(bool(txt3) and not any(re.search(r"\d", t) for t in txt3),
   f"con sólo «pieza» no queda ningún dígito: {txt3[:3]}")

shutil.rmtree(_TMP, ignore_errors=True)
print()
if FALLOS:
    print("✗ FALLA:")
    for f in FALLOS:
        print("   ·", f)
    sys.exit(1)
print("OK etiqueta: se rotula el nombre GENERAL de la pieza, sin el número")
