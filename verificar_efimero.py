# -*- coding: utf-8 -*-
"""CONTRATO DEL MOLDE EFÍMERO — `py verificar_efimero.py`

Un molde del CAMINO B se sube **para un pedido y no queda guardado**: al terminar o reiniciar el
pedido se borra entero (archivo, datos y base). Eso significa que este sistema **borra solo**, y
por eso lo que se verifica acá es sobre todo **a quién NO toca**.

🔴 EL PELIGRO CONCRETO, Y YA PAGADO: en este proyecto se borraron 3 moldes del usuario —con todo
su nombrado de piezas adentro— por confundir «molde de prueba» con «molde que sobra». No se
pudieron recuperar. Un barrido que elija mal es exactamente el mismo accidente, pero automático y
todas las veces. De ahí la regla dura: **se borra por el flag `efimero: true` y por la fecha,
nunca "los que sobran", nunca por nombre, nunca por parecerse a uno de prueba.**

⚠️ No toca nada del usuario: `db` se reemplaza por un doble que explota (ver [[test-no-toca-mssql]])
y `DATOS` va a un temporal. El catálogo es un dict en memoria y el borrado real se ESPÍA (se anota
a quién se habría borrado) en vez de ejecutarse.
"""
import os
import sys
import tempfile
import time
import types

sys.stdout.reconfigure(encoding="utf-8")
_TMP = tempfile.mkdtemp(prefix="verif_efim_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"

_falso_db = types.ModuleType("db")
_falso_db.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(
    AssertionError(f"LA PRUEBA INTENTO TOCAR MSSQL (db.{n}) — revisar el aislamiento")))
_BORRADOS_DB = []                      # a quién se le pidió borrar, y por qué camino
_falso_db.borrar_producto = lambda pid: (_BORRADOS_DB.append(("producto", pid)), 1)[-1]
_falso_db.borrar_piezas_molde = lambda pid: (_BORRADOS_DB.append(("piezas", pid)), 1)[-1]
_falso_db.leer_registro = lambda pid: None
_falso_db.registro_rev = lambda pid: None
sys.modules["db"] = _falso_db

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import servidor as S               # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)


# ── EL CATÁLOGO DE LA PRUEBA (en memoria; el de verdad ni se abre) ───────────────────────────
AHORA = time.time()
VIEJO = AHORA - 48 * 3600          # dos días sin que nadie lo toque

def _catalogo():
    return {"activo": "prod_catalogo", "productos": [
        # 1. molde del taller: NO es efímero, no se toca jamás
        {"id": "prod_catalogo", "nombre": "Camiseta de futbol", "creado_por": None,
         "propio": False, "creado": VIEJO},
        # 2. «Mi artículo» de verdad, viejo y con un nombre que PARECE de prueba: tampoco se toca.
        #    Éste es el que ya se perdió una vez por «parecía de prueba y había varios iguales».
        {"id": "prod_mio", "nombre": "prueba 3", "creado_por": 7, "propio": True, "creado": VIEJO},
        # 3. efímero abandonado (nadie lo tocó en 48 h): ESTE sí
        {"id": "prod_efim_viejo", "nombre": "Camiseta", "creado_por": 7, "propio": True,
         "efimero": True, "efimero_visto": VIEJO, "origen": "con_diseno", "creado": VIEJO},
        # 4. efímero de un pedido ABIERTO ahora mismo (en otra pantalla): no se toca
        {"id": "prod_efim_hoy", "nombre": "Camiseta", "creado_por": 7, "propio": True,
         "efimero": True, "efimero_visto": AHORA, "origen": "con_diseno", "creado": AHORA},
    ]}


CAT = {}
BORRADOS = []                      # a quién se le pidió el borrado entero


def _instalar_dobles():
    """El catálogo en memoria + el borrado ESPIADO (no se ejecuta: sólo se anota a quién)."""
    global CAT, BORRADOS
    CAT, BORRADOS = _catalogo(), []
    del _BORRADOS_DB[:]
    S._cargar_catalogo = lambda *a, **k: CAT
    S._cargar_catalogo_para_editar = lambda *a, **k: CAT
    S._guardar_catalogo = lambda c, *a, **k: None
    S._borrar_molde_entero = lambda cat, pid, efimero=False: BORRADOS.append((pid, efimero))


_real_borrar = S._borrar_molde_entero
# Sesión simulada: sin esto la API contesta 401 y los chequeos del endpoint pasarían «en verde»
# mirando respuestas vacías (que es peor que fallar).
S._USUARIOS_ON = False
S._usuario_actual = lambda *a, **k: {"id": 7, "permisos": ["molde.borrar", "pedido.crear"]}
S._uid_actual = lambda *a, **k: 7

print("CONTRATO DEL MOLDE EFÍMERO (camino B)\n")

# ══ 1. EL BARRIDO DE ABANDONADOS ═════════════════════════════════════════════════════════════
print("1 · 🔴 EL BARRIDO SE LLEVA EL ABANDONADO Y NADA MÁS")
_instalar_dobles()
S._barrer_efimeros(horas=24)
_ids = [b[0] for b in BORRADOS]
ok(_ids == ["prod_efim_viejo"],
   f"🔴 el barrido borró {_ids} — tenía que borrar SOLO ['prod_efim_viejo']")
ok("prod_catalogo" not in _ids, "🔴 EL BARRIDO SE LLEVÓ UN MOLDE DEL CATÁLOGO")
ok("prod_mio" not in _ids,
   "🔴 EL BARRIDO SE LLEVÓ UN «Mi artículo» DEL USUARIO (el que se llama «prueba 3»: el nombre "
   "NO decide nada)")
ok("prod_efim_hoy" not in _ids,
   "el barrido se llevó un efímero que se está usando ahora (pedido abierto en otra pantalla)")
ok(all(b[1] is True for b in BORRADOS), "el borrado del efímero no fue marcado como efímero")
print(f"    OK    borró {_ids} y dejó los otros 3")

print("\n1b · Y NO BORRA NADA SI TODAVÍA NO PASÓ EL TIEMPO")
_instalar_dobles()
S._barrer_efimeros(horas=24 * 365)
ok(not BORRADOS, f"con un TTL enorme igual borró {[b[0] for b in BORRADOS]}")
print("    OK    con el plazo sin cumplir no borra nada")

print("\n1c · UN PRODUCTO SIN LA MARCA NO SE BARRE, POR VIEJO QUE SEA")
_instalar_dobles()
for p in CAT["productos"]:
    p["efimero_visto"] = 0          # todos viejísimos
    if p["id"] == "prod_efim_viejo":
        p.pop("efimero")            # le sacamos la marca: ya no es efímero
S._barrer_efimeros(horas=1)
ok(not BORRADOS,
   f"🔴 borró {[b[0] for b in BORRADOS]} y NINGUNO tenía `efimero: true` — es el accidente que "
   f"ya costó 3 moldes")
print("    OK    sin la marca no se borra nada, aunque todo esté viejo")

# ══ 2. LA LIMPIEZA QUE PIDE EL PEDIDO ════════════════════════════════════════════════════════
print("\n2 · «NUEVO PEDIDO» SÓLO PUEDE BORRAR LOS EFÍMEROS QUE MANDÓ")
_instalar_dobles()
S.trabajos.clear()
cli = S.app.test_client()
r = cli.post("/api/pedido/limpiar_efimeros",
             json={"pids": ["prod_efim_viejo", "prod_efim_hoy", "prod_catalogo", "prod_mio"]})
ok(r.status_code == 200, f"la limpieza respondió {r.status_code}")
_d = r.get_json() or {}
ok(sorted(_d.get("borrados") or []) == ["prod_efim_hoy", "prod_efim_viejo"],
   f"🔴 borró {_d.get('borrados')} — tenía que borrar los DOS efímeros y nada más")
ok(sorted(_d.get("ignorados") or []) == ["prod_catalogo", "prod_mio"],
   f"🔴 no ignoró los moldes de verdad que venían en la lista: {_d.get('ignorados')}")
print(f"    OK    borró {_d.get('borrados')} · ignoró {_d.get('ignorados')}")

print("\n2b · 🔴 NO SE BORRA UN MOLDE MIENTRAS SE ESTÁ GENERANDO SU TIZADA")
# El motor está LEYENDO `entrada/<pid>/plantilla.ai` para armar las hojas: borrarlo debajo rompe
# la generación a mitad de camino, y encima el usuario ya se fue a otra pantalla.
_instalar_dobles()
S.trabajos.clear()
S.trabajos["t1"] = {"estado": "generando", "producto_id": "prod_efim_viejo,prod_catalogo"}
r = cli.post("/api/pedido/limpiar_efimeros", json={"pids": ["prod_efim_viejo", "prod_efim_hoy"]})
_d = r.get_json() or {}
ok(_d.get("borrados") == ["prod_efim_hoy"],
   f"🔴 borró {_d.get('borrados')} — el que está generando NO se podía tocar")
ok("prod_efim_viejo" in (_d.get("ignorados") or []),
   "el molde que está generando no quedó anotado como ignorado")
S.trabajos.clear()
print("    OK    el que está generando queda, el otro se va")

# ══ 3. EL BORRADO DE VERDAD PIDE A LA BASE LO QUE CORRESPONDE ════════════════════════════════
print("\n3 · UN EFÍMERO SE LLEVA TAMBIÉN SU FILA DE LA BASE")
# Un molde normal usa borrado LÓGICO (puede tener historia); el efímero no existe después del
# pedido, así que dejar su fila acumularía una por cada subida, para siempre.
S._borrar_molde_entero = _real_borrar
S._guardar_catalogo = lambda c, *a, **k: None
S._limpiar_activo_si_borrado = lambda c, pid: None
del _BORRADOS_DB[:]
S._borrar_molde_entero({"productos": []}, "prod_x", efimero=True)
S._borrar_molde_entero({"productos": []}, "prod_y", efimero=False)
ok(("producto", "prod_x") in _BORRADOS_DB,
   f"un efímero no borró su fila de `producto` en la base ({_BORRADOS_DB})")
ok(("piezas", "prod_y") in _BORRADOS_DB,
   f"un molde normal no usó el borrado de siempre ({_BORRADOS_DB})")
ok(("producto", "prod_y") not in _BORRADOS_DB,
   "🔴 un molde NORMAL se llevó su fila de `producto`: eso es borrado definitivo, no es lo suyo")
print("    OK    efímero → fila borrada · molde normal → borrado lógico de siempre")

# ══ 4. EL ALTA MARCA BIEN ════════════════════════════════════════════════════════════════════
print("\n4 · UN EFÍMERO NO SE REUSA NI COMPITE POR EL NOMBRE")
# Subir «Camiseta» hoy y «Camiseta» mañana son dos pedidos distintos y dos moldes distintos: si el
# alta reusara el de ayer, el cliente se encontraría con el nombrado y las etiquetas de ayer sobre
# un archivo que puede ser otro.
import inspect                                                     # noqa: E402
_src = inspect.getsource(S.crear_producto)
ok("if propio and not efimero:" in _src,
   "🔴 el alta puede REUSAR un efímero anterior (falta excluirlo de la rama idempotente)")
ok('_choque = None' in _src and "if efimero:" in _src,
   "el alta le exige nombre único a un efímero (no puede: se sube uno por pedido)")
print("    OK    el alta no reusa efímeros ni les pide nombre único")

print()
if FALLOS:
    print(f"❌ {len(FALLOS)} FALLO(S):")
    for f in FALLOS:
        print("   -", f)
    sys.exit(1)
print("✅ CONTRATO VERDE — el molde efímero se borra solo, y sólo él")
