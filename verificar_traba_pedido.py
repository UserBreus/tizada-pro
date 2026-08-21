"""
CONTRATO DE LA TRABA DEL PEDIDO — se corre con `py verificar_traba_pedido.py`.

Los dos errores que frena salen **bien impresos**: la tizada parece correcta y el problema se
descubre recién con las telas cortadas. Por eso hay que avisar ANTES de fabricar.

  1. **Opción de toggle que el molde no tiene.** El motor arma la prenda por el NOMBRE de las
     piezas: elegir «Larga» cuando las piezas dicen «Manga Corta …» las saca a TODAS y la prenda
     sale **sin mangas**. Y si las piezas dicen «Manga Derecha» a secas —sin corta ni larga— el
     toggle no cambia nada: la columna miente. **Pasó de verdad** (trabajo 20260729-105151):
     2 filas en «Larga» sobre un molde cuyas 24 piezas de manga no dicen ni corta ni larga.
  2. **Pieza sin tela.** El motor la mandaba a una tela inventada, «Principal», con el ancho por
     defecto (180 cm) en vez del de la tela real → en ese mismo trabajo salió una **hoja fantasma
     de 6,8 cm** al lado de la hoja buena de «Dry Basket 1,60».

⚠️ No toca nada del usuario: `DATOS` va a un temporal y el módulo `db` se reemplaza por un doble
que explota (ver [[test-no-toca-mssql]]).
"""
import json
import os
import sys
import tempfile
import types

_TMP = tempfile.mkdtemp(prefix="verif_traba_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"

_falso_db = types.ModuleType("db")
_falso_db.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(
    AssertionError(f"LA PRUEBA INTENTO TOCAR MSSQL (db.{n}) — revisar el aislamiento")))

# ── LA "BASE" DEL REGISTRO, SIMULADA (2026-08-19: el server lee el registro SOLO de la base;
#    el doble la imita en memoria, sembrada del JSON que este contrato dejó en su tmp). ──
import json as _rj, os as _ro
_REG_MEM, _REG_REV = {}, {}
def _reg_leer(pid):
    if pid not in _REG_MEM:
        try:
            _p = _ro.path.join(_ro.environ["TIZADA_DATOS"], "productos", pid, "registro_producto.json")
            _REG_MEM[pid] = _rj.load(open(_p, encoding="utf-8")); _REG_REV[pid] = 1
        except Exception:
            return None
    return _REG_MEM.get(pid)
_falso_db.leer_registro = _reg_leer
_falso_db.registro_rev = lambda pid: (_REG_REV.get(pid, 1) if _reg_leer(pid) is not None else None)
_falso_db.guardar_registro = lambda pid, piezas, reg: (_REG_MEM.__setitem__(pid, reg),
                                                  _REG_REV.__setitem__(pid, _REG_REV.get(pid, 1) + 1), 1)[-1]
_falso_db.borrar_piezas_molde = lambda pid: (_REG_MEM.pop(pid, None), _REG_REV.pop(pid, None), 0)[-1]
sys.modules["db"] = _falso_db

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motor_pedido as MP        # noqa: E402
import servidor as S             # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)


# ══ 1. QUÉ OPCIONES TIENE REALMENTE UN MOLDE (la regla, sin servidor de por medio) ════════════
# a) el molde DISTINGUE corta/larga
_dist = ["Frente 1", "Espalda 1", "Manga Corta Derecha 1", "Manga Larga Derecha 1"]
s = MP.opciones_soportadas(_dist, "manga", ["Corta", "Larga"])
ok(s["corta"] == 1 and s["larga"] == 1 and s["__clave__"] == 2, f"mal conteo con corta y larga: {s}")
ok(not S._opcion_sin_piezas(s, "Larga"), "se bloqueo «Larga» en un molde que SI tiene manga larga")

# b) el molde SOLO tiene manga corta  ← elegir «Larga» dejaria la prenda SIN MANGAS
_solo = ["Frente 1", "Espalda 1", "Manga Corta Derecha 1", "Manga Corta izquierda 1"]
s = MP.opciones_soportadas(_solo, "manga", ["Corta", "Larga"])
ok(S._opcion_sin_piezas(s, "Larga"), f"no se detecto que el molde no tiene manga larga: {s}")
ok(not S._opcion_sin_piezas(s, "Corta"), f"se bloqueo la opcion que SI existe: {s}")

# c) EL CASO REAL DEL USUARIO: piezas «Manga Derecha» a secas → el toggle no cambia nada
_generico = ["Frente 13", "Espalda 13", "Manga Derecha 5", "Manga izquierda 5", "Cuello 12"]
s = MP.opciones_soportadas(_generico, "manga", ["Corta", "Larga"])
ok(s["__clave__"] == 2 and s["corta"] == 0 and s["larga"] == 0, f"mal conteo con mangas genericas: {s}")
ok(S._toggle_no_distingue(s),
   "no se detecto que el molde NO DISTINGUE las opciones (sus mangas no dicen corta ni larga)")
# …pero NO traba: lo que sale es correcto igual. Trabar acá dejaria al usuario sin poder generar
# NUNCA con ese molde (las 5 filas del pedido real caian en este caso).
ok(not S._opcion_sin_piezas(s, "Larga") and not S._opcion_sin_piezas(s, "Corta"),
   "se trabo un molde que no distingue las opciones: la tizada que sale es correcta, hay que AVISAR, no frenar")

# d) la variable NO lleva mangas → el toggle es irrelevante, NO se traba nada
_sin = ["Frente 1", "Espalda 1", "Cuello 1"]
s = MP.opciones_soportadas(_sin, "manga", ["Corta", "Larga"])
ok(not S._opcion_sin_piezas(s, "Larga"),
   "se trabo una musculosa: si la variable no lleva mangas, el toggle no aplica y no hay nada que avisar")

# e) acentos y mayúsculas no cambian el resultado
ok(MP.tokens_pieza("Manga  IZQUIERDA (corta)") == ["manga", "izquierda", "corta"],
   f"la normalizacion del nombre cambio: {MP.tokens_pieza('Manga  IZQUIERDA (corta)')}")


# ══ 2. LA TRABA COMPLETA, sobre un molde de mentira escrito en el temporal ════════════════════
PID = "prod_traba"
os.makedirs(os.path.join(_TMP, "productos", PID), exist_ok=True)
_reg = {n: {"M": {"mesa": 1, "pieza_idx": i}} for i, n in enumerate(_solo)}
json.dump(_reg, open(os.path.join(_TMP, "productos", PID, "registro_producto.json"), "w",
                     encoding="utf-8"), ensure_ascii=False)
json.dump({"version": 2, "piezas": [{"id": "pz_%04d" % (i + 1), "clave": n, "nombre": n, "numero": None}
                                    for i, n in enumerate(_solo)]},
          open(os.path.join(_TMP, "productos", PID, "piezas.json"), "w", encoding="utf-8"),
          ensure_ascii=False)

CAT = {"reglas_planilla": [{"id": "r_manga", "nombre": "Manga", "comportamiento": "manga",
                            "tipo": "toggle", "opciones": "Corta, Larga"}],
       "plantillas_planillas": [{"id": "tpl", "columnas": [
           {"id": "talle", "role": "talle"}, {"id": "manga", "role": "manga"}]}]}
PROD = {"id": PID, "nombre": "Camiseta de prueba", "planilla_template_id": "tpl",
        "variante_guia": "M",
        "variantes": [{"clave": "v_corta", "valores": [{"pieza_id": "pz_0003"}, {"pieza_id": "pz_0004"},
                                                       {"pieza_id": "pz_0001"}]},
                      {"clave": "v_musculosa", "valores": [{"pieza_id": "pz_0001"},
                                                           {"pieza_id": "pz_0002"}]}]}

_disp = S._toggles_disponibles(PROD, CAT, _reg)
ok("manga" in _disp, f"no se detecto el toggle de la plantilla: {list(_disp)}")
ok(_disp["manga"]["v_musculosa"]["__clave__"] == 0,
   f"la variable sin mangas no deberia tener piezas de manga: {_disp['manga']['v_musculosa']}")

_fila = lambda vcl, op: {"talle": "M", "variante_clave": vcl,
                         "variante_piezas": list(_reg.keys()),
                         "toggles": [{"clave": "manga", "opcion": op, "opciones": ["Corta", "Larga"]}]}
_tela = {n: "Dry Basket" for n in _reg}

# ⬇⬇ LA QUE ATRAPA EL BUG QUE REPORTO EL USUARIO ⬇⬇
_e = S._validar_pedido(PID, "Camiseta de prueba", PROD, CAT, [_fila("v_corta", "Larga")], _tela, _reg)
ok(_e is not None, "el pedido con «Larga» sobre un molde sin manga larga NO se trabo")
ok(_e and "Fila 1" in " ".join(_e[1]), f"la traba no dice QUE FILA corregir: {_e}")

# la opción que sí existe pasa
ok(S._validar_pedido(PID, "x", PROD, CAT, [_fila("v_corta", "Corta")], _tela, _reg) is None,
   "se trabo un pedido correcto (la opcion existe)")
# la variable sin mangas pasa con cualquier opción
ok(S._validar_pedido(PID, "x", PROD, CAT, [_fila("v_musculosa", "Larga")], _tela, _reg) is None,
   "se trabo una variable que no lleva mangas")

# ⬇⬇ LA HOJA FANTASMA «Principal» ⬇⬇  una pieza sin tela tiene que frenar el pedido
_medias = {n: "Dry Basket" for n in list(_reg)[:2]}
_e2 = S._validar_pedido(PID, "x", PROD, CAT, [_fila("v_corta", "Corta")], _medias, _reg)
ok(_e2 is not None and "tela" in _e2[0].lower(),
   f"una pieza SIN TELA no trabo el pedido (el motor le inventaba la hoja «Principal»): {_e2}")


# ══ Veredicto ════════════════════════════════════════════════════════════════════════════════
import shutil
shutil.rmtree(_TMP, ignore_errors=True)
if FALLOS:
    print(f"\nx LA TRABA DEL PEDIDO NO FUNCIONA ({len(FALLOS)}):\n")
    for f in FALLOS:
        print("    -", f)
    sys.exit(1)
print("OK traba del pedido: no deja generar con una opcion que el molde no tiene ni con piezas sin tela")
