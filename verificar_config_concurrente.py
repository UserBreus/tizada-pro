"""
CONTRATO: LA CONFIGURACIÓN NO SE PISA — se corre con `py verificar_config_concurrente.py`.

Cubre los dos choques entre herramientas de la auditoría 2026-08-18 (changelog 171). Los dos
fallaban **en silencio**: nada rojo en pantalla, el usuario cree que guardó y no guardó.

  1. **Dos herramientas guardando a la vez se pisaban.** El catálogo es UNO solo y global, y ~43
     endpoints lo modifican con el patrón leer → cambiar lo mío → guardar entero. Sin un candado
     que abarque la secuencia, el que guarda último escribe SU copia y el cambio del otro
     desaparece. Ahora existe `_cargar_catalogo_para_editar()`.

  2. **El preview del Arte servía el render viejo.** `_piezas_base_clave` no miraba QUÉ PIEZAS se
     dibujan: ni la composición de la variable ni las columnas/reglas de toggle. Agregar una pieza
     a la variable dejaba el visor mostrando la prenda vieja mientras la TIZADA sí la incluía —
     justo lo que la ley «el arte se ve igual que la tizada» no permite.

⚠️ No toca nada del usuario: `DATOS` va a un temporal y el módulo `db` se reemplaza por un doble
en memoria (ver [[test-no-toca-mssql]]).
"""
import copy
import os
import sys
import tempfile
import threading
import types
import time

_TMP = tempfile.mkdtemp(prefix="verif_config_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"

# La "base": un dict en memoria que serializa como la de verdad (deepcopy = otra instancia,
# igual que si volviera de MSSQL). Todo lo demás de `db` es no-op.
_DOCS = {}
_falso = types.ModuleType("db")
_falso.set_doc = lambda c, o: _DOCS.__setitem__(c, copy.deepcopy(o))
_falso.get_doc = lambda c: copy.deepcopy(_DOCS.get(c))
_falso.__getattr__ = lambda n: (lambda *a, **k: None)

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
_falso.leer_registro = _reg_leer
_falso.registro_rev = lambda pid: (_REG_REV.get(pid, 1) if _reg_leer(pid) is not None else None)
_falso.guardar_registro = lambda pid, piezas, reg: (_REG_MEM.__setitem__(pid, reg),
                                                  _REG_REV.__setitem__(pid, _REG_REV.get(pid, 1) + 1), 1)[-1]
_falso.borrar_piezas_molde = lambda pid: (_REG_MEM.pop(pid, None), _REG_REV.pop(pid, None), 0)[-1]
sys.modules["db"] = _falso

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import servidor as S             # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK    " if cond else "  FALLA ") + msg)


PID = "prod_verif"


def _sembrar():
    _DOCS["catalogo"] = {
        "activo": PID,
        "reglas_planilla": [{"id": "rg1", "opciones": "Corta, Larga"}],
        "plantillas_planillas": [{"id": "tpl1", "columnas": [{"id": "manga", "role": "manga", "reglaId": "rg1"}]}],
        "productos": [{"id": PID, "nombre": "Molde", "planilla_template_id": "tpl1",
                       "etiqueta": {"activo": False, "texto": "viejo"},
                       "borde_corte": {"activo": False, "ancho_mm": 1},
                       "variantes": [{"clave": "v_a", "label": "MP1-A",
                                      "valores": [{"pieza_id": 1}, {"pieza_id": 2}]}]}],
    }


def _correr_dos_pantallas(con_candado):
    """Dos pantallas de configuración guardando a la vez: el patrón exacto de set_etiqueta /
    set_borde_corte / set_telas / set_variantes… El `sleep` sólo fuerza el entrelazado que en
    producción da la latencia de la base (la que guarda más lento termina última)."""
    _sembrar()
    barrera = threading.Barrier(2)

    def _pantalla(campo, valor, demora):
        if con_candado:
            barrera.wait()                          # los dos requests llegan a la vez…
            cat = S._cargar_catalogo_para_editar()  # …y el candado los ordena
        else:
            cat = S._cargar_catalogo()              # como era antes: sin candado
            barrera.wait()                          # los dos ya leyeron el MISMO estado
        try:
            prod = next(p for p in cat["productos"] if p["id"] == PID)
            prod[campo] = valor
            time.sleep(demora)
            S._guardar_catalogo(cat)
        finally:
            S._soltar_edicion_catalogo()

    t1 = threading.Thread(target=_pantalla, args=("etiqueta", {"activo": True, "texto": "NUEVO"}, 0.05))
    t2 = threading.Thread(target=_pantalla, args=("borde_corte", {"activo": True, "ancho_mm": 3}, 0.20))
    t1.start(); t2.start(); t1.join(timeout=30); t2.join(timeout=30)
    if t1.is_alive() or t2.is_alive():
        return None                                  # se colgó: el candado no libera
    p = next(x for x in S._cargar_catalogo()["productos"] if x["id"] == PID)
    return (p.get("etiqueta", {}).get("texto") == "NUEVO",
            p.get("borde_corte", {}).get("ancho_mm") == 3)


print("[1] SIN candado se pisan (si no, el resto de la prueba no probaría nada)")
_sin = _correr_dos_pantallas(con_candado=False)
ok(_sin is not None and not all(_sin),
   "sin candado, el cambio de una pantalla se pierde (el escenario es real)")

print()
print("[2] CON candado sobreviven los dos")
_con = _correr_dos_pantallas(con_candado=True)
ok(_con is not None, "las dos pantallas terminaron (el candado no deja a nadie colgado)")
if _con:
    ok(_con[0], "la ETIQUETA que guardó una pantalla sobrevivió")
    ok(_con[1], "el BORDE que guardó la otra sobrevivió")

# El candado tiene que quedar LIBRE: si un endpoint corta antes de guardar y nadie lo suelta,
# la siguiente edición de cualquiera se cuelga para siempre.
_libre = S._LOCK_CAT_EDICION.acquire(timeout=2)
ok(_libre, "el candado queda libre después de editar (no se cuelga la próxima edición)")
if _libre:
    S._LOCK_CAT_EDICION.release()


def _corta_antes_de_guardar():
    S._cargar_catalogo_para_editar()
    S._soltar_edicion_catalogo()      # lo que hace el teardown_request del server


_h = threading.Thread(target=_corta_antes_de_guardar)
_h.start(); _h.join()
_libre2 = S._LOCK_CAT_EDICION.acquire(timeout=2)
ok(_libre2, "un endpoint que corta ANTES de guardar (validación/error) igual suelta el candado")
if _libre2:
    S._LOCK_CAT_EDICION.release()


print()
print("[3] la clave del preview mira QUÉ PIEZAS se dibujan")
_sembrar()
cat = S._cargar_catalogo()
base = next(p for p in cat["productos"] if p["id"] == PID)


def clave(prod, c=cat):
    return S._piezas_base_clave(PID, None, prod, {"Frente": 1}, {}, {}, "v_a", "M", {}, c)


k0 = clave(base)

# (a) la variable pasa a tener una pieza más (Variables · paso 2)
p_var = copy.deepcopy(base)
p_var["variantes"][0]["valores"].append({"pieza_id": 3})
ok(clave(p_var) != k0, "agregar una pieza a la VARIABLE invalida el preview")

# (b) cambian las opciones del toggle (Reglas de planilla), sin agregar ni quitar reglas
cat_reglas = copy.deepcopy(cat)
cat_reglas["reglas_planilla"][0]["opciones"] = "Corta, Larga, 3/4"
ok(clave(base, cat_reglas) != k0, "cambiar las OPCIONES de una regla invalida el preview")

# (c) cambia la planilla asignada al molde
p_tpl = copy.deepcopy(base)
p_tpl["planilla_template_id"] = "tpl_otra"
ok(clave(p_tpl) != k0, "cambiar la PLANILLA asignada invalida el preview")

# (d) tocar OTRA variable no tiene por qué regenerar ésta (que invalide de más también cuesta:
#     son ~17 s de dibujo por talle)
p_otra = copy.deepcopy(base)
p_otra["variantes"].append({"clave": "v_b", "label": "MP1-B", "valores": [{"pieza_id": 9}]})
ok(clave(p_otra) == k0, "tocar OTRA variable NO regenera ésta (no invalida de más)")

# (e) control: algo que ya estaba en la clave tiene que seguir invalidando
p_borde = copy.deepcopy(base)
p_borde["borde_corte"] = {"activo": True, "ancho_mm": 9}
ok(clave(p_borde) != k0, "CONTROL: el borde de corte sigue invalidando")

print()
if FALLOS:
    print(f"FALLARON {len(FALLOS)}:")
    for f in FALLOS:
        print("  -", f)
    sys.exit(1)
print("TODO OK")
