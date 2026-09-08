"""
CONTRATO: **CADA MOLDE SE GENERA SÓLO EN SU DISEÑO** — se corre con `py verificar_pedido_por_diseno.py`.

🔴 EL CASO QUE LO MOTIVÓ (reporte del usuario 2026-09-08): un pedido con DOS espacios de diseño
(«Camiseta» y «Campera»), cada uno con SU molde, salió con **cuatro tizadas** —«Principal»,
«Deportivo Pro» y «Delta» repetidas— y con la ficha mostrando **dos veces el mismo molde**.
`/api/generar_multi` recorría, para cada molde, TODOS los diseños de la planilla: las filas de la
campera también se generaban con el molde de la camiseta. En el camino A eso lo tapaba a medias el
arte (un molde sin `arte.ai` para ese diseño se salteaba); en el camino B el diseño viene DENTRO del
molde, no hay arte que falte, y nada lo frenaba.

El front sabe qué molde eligió el usuario en cada espacio (`disenoMoldes`) y ahora lo manda:
`moldes_por_diseno = {slug_del_diseño: [pid, …]}`. Lo que se verifica acá:

  1. **Con el mapa**: cada molde recibe SÓLO las prendas de su diseño (una tizada por molde, no dos)
     y la ficha pide UN molde guía por molde, no uno por cada combinación molde × diseño.
  2. **Sin el mapa, con `vars_por_diseno`**: mismo resultado. Es el respaldo para una pantalla que
     quedó abierta con el front viejo (ese payload viaja desde antes).
  3. **Sin ningún mapa**: no se filtra nada (se prefiere generar de más antes que dejar prendas sin
     tizada) — se deja documentado que ése es el comportamiento, no un descuido.

⚠️ No toca nada del usuario: `DATOS`/`ENTRADA` son una COPIA en un temporal, el módulo `db` es un
doble que explota si alguien intenta ir a MSSQL, y el motor y el render de la ficha están espiados
(este contrato prueba el REPARTO, no el dibujo). Sólo lee los originales.
"""
import json
import os
import shutil
import sys
import tempfile
import time
import types

try:                                        # la consola de Windows es cp1252 y se traga las flechas
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = os.path.dirname(os.path.abspath(__file__))
# Molde base de la caja de arena: se COPIA dos veces (dos moldes distintos) para armar el pedido de
# dos espacios. Se usa uno chico a propósito — acá no se dibuja nada.
PID_ORIGEN = "prod_20260907_151231_8fa8"
PID_A, PID_B = "prod_prueba_reparto_a", "prod_prueba_reparto_b"

if not os.path.isdir(os.path.join(RAIZ, "datos", "productos", PID_ORIGEN)):
    print(f"AVISO: el molde {PID_ORIGEN} de este contrato ya no existe — no hay datos para "
          f"verificar. Actualizar el PID cuando haya un molde con talles cargados.")
    sys.exit(0)

# ── EL REGISTRO SE LEE DE LA BASE, UNA VEZ Y SÓLO DE LECTURA ──────────────────────────────────
# `datos/productos/<pid>/` ya no guarda `registro_producto.json` (desde 2026-08-19 la fuente de
# verdad es MSSQL). Se lee ACÁ, antes de aislar la base, y se deja como JSON en la caja de arena:
# de ahí en más la prueba no vuelve a tocar MSSQL.
# Este clon corre SIEMPRE contra su propia base (ver `INICIAR-PRUEBA-8051.bat`); si el que corre el
# contrato ya eligió una, manda la suya.
os.environ.setdefault("TIZADA_DB_NAME", "TizadaProCaminoB")
try:
    import db as _db_real
    _REGISTRO = _db_real.leer_registro(PID_ORIGEN)
except Exception as _e:
    print(f"AVISO: no se pudo leer el registro de {PID_ORIGEN} de la base ({_e}) — sin él no hay "
          f"talles con qué armar el pedido. Correr con la base del sistema levantada.")
    sys.exit(0)
if not _REGISTRO:
    print(f"AVISO: el molde {PID_ORIGEN} no tiene piezas cargadas — no hay nada que repartir. "
          f"Actualizar el PID cuando haya un molde con talles.")
    sys.exit(0)

_TMP = tempfile.mkdtemp(prefix="verif_reparto_")
_DATOS = os.path.join(_TMP, "datos")
_ENTRADA = os.path.join(_TMP, "entrada")
os.environ["TIZADA_DATOS"] = _DATOS
os.environ["TIZADA_ENTRADA"] = _ENTRADA
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_FUENTES"] = os.path.join(RAIZ, "catalogo_fuentes")   # sólo lectura
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"

# ── EL DOBLE DE `db`: si algo intenta ir a la base de verdad, la prueba se cae acá ──────────────
_falso_db = types.ModuleType("db")
_falso_db.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(
    AssertionError(f"LA PRUEBA INTENTO TOCAR MSSQL (db.{n}) — revisar el aislamiento")))
_REG_MEM, _REG_REV = {}, {}


def _reg_leer(pid):
    if pid not in _REG_MEM:
        try:
            _p = os.path.join(os.environ["TIZADA_DATOS"], "productos", pid, "registro_producto.json")
            _REG_MEM[pid] = json.load(open(_p, encoding="utf-8")); _REG_REV[pid] = 1
        except Exception:
            return None
    return _REG_MEM.get(pid)


_falso_db.leer_registro = _reg_leer
_falso_db.registro_rev = lambda pid: (_REG_REV.get(pid, 1) if _reg_leer(pid) is not None else None)
_falso_db.guardar_registro = lambda pid, piezas, reg: (_REG_MEM.__setitem__(pid, reg),
                                                       _REG_REV.__setitem__(pid, _REG_REV.get(pid, 1) + 1), 1)[-1]
_falso_db.borrar_piezas_molde = lambda pid: (_REG_MEM.pop(pid, None), _REG_REV.pop(pid, None), 0)[-1]
sys.modules["db"] = _falso_db


def _armar_caja():
    """COPIA (nunca mueve ni borra) el molde real DOS VECES a la caja de arena y deja el catálogo
    con esos dos productos. Sin dueño: la prueba no simula login de verdad y `_guard_molde` cortaría."""
    os.makedirs(os.path.join(_DATOS, "productos"), exist_ok=True)
    for f in os.listdir(os.path.join(RAIZ, "datos")):
        o = os.path.join(RAIZ, "datos", f)
        if os.path.isfile(o):
            shutil.copy2(o, os.path.join(_DATOS, f))
    cat = json.load(open(os.path.join(_DATOS, "productos_catalogo.json"), encoding="utf-8"))
    base = next(p for p in cat["productos"] if p["id"] == PID_ORIGEN)
    prods = []
    for pid, nombre in ((PID_A, "MOLDE DE LA CAMISETA"), (PID_B, "MOLDE DE LA CAMPERA")):
        shutil.copytree(os.path.join(RAIZ, "datos", "productos", PID_ORIGEN),
                        os.path.join(_DATOS, "productos", pid))
        shutil.copytree(os.path.join(RAIZ, "entrada", PID_ORIGEN), os.path.join(_ENTRADA, pid))
        json.dump(_REGISTRO, open(os.path.join(_DATOS, "productos", pid, "registro_producto.json"),
                                  "w", encoding="utf-8"), ensure_ascii=False)
        p = json.loads(json.dumps(base))
        p["id"], p["nombre"] = pid, nombre
        p.pop("creado_por", None)
        p["propio"] = False
        prods.append(p)
    cat["productos"] = prods
    json.dump(cat, open(os.path.join(_DATOS, "productos_catalogo.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    return prods


PRODS = _armar_caja()

sys.path.insert(0, RAIZ)
import servidor as S            # noqa: E402

FALLOS = []


def ok(cond, que):
    print(("  OK   " if cond else "  FALLA ") + que)
    if not cond:
        FALLOS.append(que)


# ── EL PEDIDO DE LA PRUEBA ────────────────────────────────────────────────────────────────────
# Dos espacios de diseño, cada uno con SU molde y sus prendas. Es el pedido que reportó el usuario.
FILAS = [{"talle": "M", "dise_o": "Camiseta"}, {"talle": "S", "dise_o": "Camiseta"},
         {"talle": "L", "dise_o": "Campera"}, {"talle": "XL", "dise_o": "Campera"}]
TELA = "Dry Basket 1,60"


def _correr(extra):
    """Manda el pedido y devuelve (moldes_por_grupo, guias_pedidas). El motor y el molde guía están
    espiados: interesa QUÉ le llega a cada uno, no lo que dibujarían."""
    llamadas, guias = [], []

    def _motor_falso(grupos, fuentes, salida, **k):
        for g in grupos:
            for m in (g.get("moldes") or []):
                llamadas.append((os.path.basename(os.path.dirname(m.get("plantilla", ""))),
                                 len(m.get("prendas") or [])))
        os.makedirs(salida, exist_ok=True)
        return {"hojas": []}

    def _guia_espia(pid, prod, reg, diseno, var=None, reempl=None):
        guias.append((pid, diseno))
        return None            # sin dibujo: la ficha sale sin guías y no se paga el render

    orig = (S.MP.generar_pedido_grupos, S._molde_guia_ficha, S._usuario_actual)
    S.MP.generar_pedido_grupos = _motor_falso
    S._molde_guia_ficha = _guia_espia
    S._usuario_actual = lambda: {"id": "u_prueba", "nombre": "Prueba", "rol": "admin"}
    try:
        cli = S.app.test_client()
        cuerpo = {"molds": [PID_A, PID_B], "prendas": FILAS, "default_diseno": "camiseta",
                  "tela_base": {PID_A: TELA, PID_B: TELA},
                  "planilla": {"columnas": [{"id": "talle", "label": "Talle"},
                                            {"id": "dise_o", "label": "Diseño"}], "filas": FILAS}}
        cuerpo.update(extra)
        r = cli.post("/api/generar_multi", json=cuerpo)
        assert r.status_code == 200, f"HTTP {r.status_code}: {r.get_data(as_text=True)[:200]}"
        tid = r.get_json()["id"]
        t0 = time.time()
        while S.trabajos[tid]["estado"] not in ("listo", "error") and time.time() - t0 < 120:
            time.sleep(0.2)
        assert S.trabajos[tid]["estado"] == "listo", S.trabajos[tid].get("error")
    finally:
        S.MP.generar_pedido_grupos, S._molde_guia_ficha, S._usuario_actual = orig
    return llamadas, guias


def _resumen(llamadas):
    """{pid: prendas generadas} — dos entradas del mismo pid = ese molde se tizó dos veces."""
    d = {}
    for pid, n in llamadas:
        d[pid] = d.get(pid, 0) + n
    return d, [pid for pid, _ in llamadas]


def prueba(titulo, extra, exigir):
    print("\n" + titulo)
    llamadas, guias = _correr(extra)
    d, orden = _resumen(llamadas)
    print(f"      · el motor recibió: {orden}  → prendas por molde: {d}")
    print(f"      · la ficha pidió guías: {guias}")
    if not exigir:
        return
    ok(orden.count(PID_A) == 1 and orden.count(PID_B) == 1,
       f"cada molde entra UNA sola vez en la tizada (entró {orden})")
    ok(d.get(PID_A) == 2 and d.get(PID_B) == 2,
       f"cada molde se genera SOLO con las 2 prendas de su diseño ({d})")
    ok(len(guias) == 2, f"la ficha pide 2 moldes guía, uno por molde (pidió {len(guias)}: {guias})")
    ok({g[0] for g in guias} == {PID_A, PID_B}, f"y son los dos moldes distintos ({guias})")
    # OJO: el diseño de la guía es el que DE VERDAD SE ESTAMPÓ. Si el diseño pedido no tiene arte,
    # la tizada cae al de la moldería (`_fallback`) y la ficha tiene que mostrar ÉSE — por eso acá
    # no se exige «camiseta»/«campera», sino que cada molde traiga UNA guía y una sola.
    ok(len(set(g[0] for g in guias)) == len(guias), f"ninguna guía repite molde ({guias})")


try:
    prueba("[1] CON el mapa `moldes_por_diseno` (lo que manda el front de hoy)",
           {"moldes_por_diseno": {"camiseta": [PID_A], "campera": [PID_B]}}, True)
    prueba("[2] SIN el mapa, con `vars_por_diseno` (respaldo para una pantalla vieja)",
           {"vars_por_diseno": {"camiseta": {PID_A: "v_uupulkm"}, "campera": {PID_B: "v_uupulkm"}}}, True)
    # Sin NINGÚN mapa no hay con qué repartir: se genera de más (el usuario ve moldes repetidos)
    # antes que dejar prendas sin tizar. Queda a la vista para que no se lea como un descuido.
    prueba("[3] SIN ningún mapa: se genera de más, a propósito (nada que repartir)", {}, False)
finally:
    shutil.rmtree(_TMP, ignore_errors=True)

print("\n" + ("  OK: cada molde se tiza sólo en su diseño y la ficha no lo repite"
             if not FALLOS else f"  {len(FALLOS)} FALLA(S): " + " · ".join(FALLOS)))
sys.exit(1 if FALLOS else 0)
