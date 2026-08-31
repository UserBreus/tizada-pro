# -*- coding: utf-8 -*-
"""
CONTRATO: EL ALTA Y EL VISOR DE UN MOLDE CON EL DISEÑO ADENTRO (camino B, E2).
Se corre con `py verificar_alta_con_diseno.py [ruta al .ai]`.

Qué se verifica:

  1. **El alta arma el registro exacto.** Una entrada por pieza y talle, con su mesa, su
     `pieza_idx` y su medida. Sin emparejar nada: en el camino B los talles son CAPAS de la misma
     mesa, así que la pieza *i* de la mesa *m* es la misma en todos los talles. Eso es lo que
     evita los cruces de piezas que arrastra el emparejado por forma del camino A.
  2. **El visor muestra TODAS las mesas juntas.** El de hoy elige UNA mesa; acá cada mesa es una
     pieza, así que mostrar una sola mostraría una sola pieza y no habría nada que nombrar.
  3. **El visor es LIVIANO**: van los contornos y nada más. De un archivo de 123 MB tienen que
     salir unos pocos KB.
  4. 🔴 **La marca entra en la clave del caché.** El alta detecta y DESPUÉS marca: con la misma
     ruta y el mismo mtime, la detección da distinto antes y después. Sin la marca en la clave, el
     visor sirve la detección vieja y no hay forma de refrescarla. (Ya pasó al probar esto.)
  5. 🔴 **Los moldes del camino A no cambian en nada.** Sin la marca, todo sigue igual.

⚠️ No toca datos del usuario: trabaja sobre una COPIA del archivo en un temporal.
"""
import os
import shutil
import sys
import tempfile
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
os.environ.setdefault("TIZADA_DB_SERVER", r"localhost\NO_EXISTE_ES_UNA_PRUEBA")

import motor_pedido as MP              # noqa: E402
import molde_real as MR                # noqa: E402
import piezas_con_diseno as PD         # noqa: E402

ORIG = (sys.argv[1] if len(sys.argv) > 1 else
        r"C:\Users\user2\Downloads\PRUEBA TIZADA PRO\para acomodo de archivos\CAMISETA JUGADOR.ai")
FALLOS = []


def ok(cond, msg):
    print(("  OK    " if cond else "  FALLA ") + msg)
    if not cond:
        FALLOS.append(msg)


if not os.path.exists(ORIG):
    print(f"No está el archivo de prueba:\n  {ORIG}\nPasale la ruta por parámetro.")
    sys.exit(1)

TMP = tempfile.mkdtemp(prefix="verif_camino_b_")
COPIA = os.path.join(TMP, "plantilla.ai")
t0 = time.time()
shutil.copy2(ORIG, COPIA)
print(f"copia de trabajo en {time.time()-t0:.1f}s  ({os.path.getsize(COPIA)/1e6:.0f} MB)")

# ─────────────────────────────────────────────────────────────────
print("\n1 · EL ALTA ARMA EL REGISTRO, SIN EMPAREJAR NADA")
t0 = time.time()
alta = PD.alta_molde_con_diseno(COPIA)
print(f"    ({time.time()-t0:.1f}s)")
reg = alta["registro"]
ok(alta["origen"] == "con_diseno", "el alta se declara del camino B")
ok(not alta["problemas"], f"sin problemas bloqueantes: {alta['problemas']}")
ok(len(reg) == alta["mesas"],
   f"una pieza por mesa: {len(reg)} piezas para {alta['mesas']} mesas")
ok(len(alta["talles"]) >= 2, f"con sus {len(alta['talles'])} talles")
ok(len(alta["completos"]) == len(alta["talles"]),
   f"y TODOS los talles quedan completos ({len(alta['completos'])}/{len(alta['talles'])})")

_una = reg[sorted(reg)[0]]
_t0 = sorted(_una)[0]
faltan = [k for k in ("mesa", "pieza_idx", "w_cm", "h_cm", "bbox_mu", "ancla") if k not in _una[_t0]]
ok(not faltan, f"cada entrada trae lo que espera el motor (faltan: {faltan})")

# 🔴 lo que hace exacta la correspondencia: la misma pieza es la misma mesa e índice en todo talle
_lios = [p for p, xt in reg.items()
         if len({(v["mesa"], v["pieza_idx"]) for v in xt.values()}) != 1]
ok(not _lios,
   f"🔴 cada pieza es la MISMA mesa e índice en todos sus talles — correspondencia exacta, "
   f"sin emparejar por forma ({len(_lios)} con líos)")

# y los talles crecen: si estuvieran fundidos, todos medirían igual
_p0 = reg[sorted(reg)[0]]
_anchos = {round(v["w_cm"], 1) for v in _p0.values()}
ok(len(_anchos) > 1, f"los talles de una pieza tienen medidas distintas: {len(_anchos)} tamaños")

# ─────────────────────────────────────────────────────────────────
print("\n1b · 🔴 LOS DOS ÍNDICES: `pieza_idx` ÚNICO POR TALLE, `idx_mesa` DENTRO DE LA MESA")
# El sistema usa `pieza_idx` para DOS cosas que en un molde de una sola mesa dan el mismo número:
#   · `motor_pedido._idx_a_nombre` arma un mapa GLOBAL pieza_idx→nombre por talle (resuelve las
#     VARIABLES). Si las 9 piezas tuvieran pieza_idx=0, ese mapa se quedaría con UNA y las otras
#     ocho serían invisibles para las variables y los toggles — sin fallar, que es lo peor.
#   · `motor_pedido._armar_base` indexa DENTRO de la mesa para sacar el contorno.
# Con 9 mesas eso se parte en dos números distintos, y por eso el registro guarda los dos.
_t = sorted(next(iter(reg.values())))[0]
_idxs = [v[_t]["pieza_idx"] for v in reg.values() if _t in v]
ok(len(set(_idxs)) == len(_idxs),
   f"🔴 en un talle, cada pieza tiene un `pieza_idx` DISTINTO: {sorted(_idxs)}")
ok(all("idx_mesa" in v[_t] for v in reg.values() if _t in v),
   "y cada una guarda además su `idx_mesa` (la posición dentro de su mesa, que usa el motor)")
_mapa = {}
for _nom, _pt in reg.items():
    for _i in (_pt or {}).values():
        _mapa.setdefault(int(_i["pieza_idx"]), _nom)
        break
ok(len(_mapa) == len(reg),
   f"🔴 el mapa pieza_idx→nombre que resuelve las VARIABLES ve las {len(reg)} piezas, no una sola "
   f"(ve {len(_mapa)})")

print("\n2 · EL VISOR MUESTRA TODAS LAS MESAS JUNTAS")
PD.marcar(COPIA, True)
MP._DET_CACHE.clear()
t0 = time.time()
det = MP.detectar_piezas(COPIA)
print(f"    ({time.time()-t0:.1f}s) · lienzo {det['img_w']:.0f} x {det['img_h']:.0f} mm")
ok(det.get("origen") == "con_diseno", "el visor sabe que es del camino B")
ok(len(det["piezas"]) == alta["mesas"],
   f"🔴 muestra las {len(det['piezas'])} piezas de las {alta['mesas']} mesas, no las de una sola")
ok(len({p["mesa"] for p in det["piezas"]}) == alta["mesas"],
   "y cada una dice de qué mesa viene")
ok(all("t_idx" in p for p in det["piezas"]),
   "con su índice dentro de la mesa, que es el del registro")
_pos = {(round(p["px"]), round(p["py"])) for p in det["piezas"]}
ok(len(_pos) == len(det["piezas"]), "ninguna pieza queda encima de otra en la grilla")
ok(all(p["px"] >= 0 and p["py"] >= 0 for p in det["piezas"]), "ninguna queda fuera del lienzo")

# ─────────────────────────────────────────────────────────────────
print("\n3 · EL VISOR ES LIVIANO (contornos y nada más)")
import json                                                    # noqa: E402
peso = len(json.dumps(det))
print(f"    el archivo pesa {os.path.getsize(COPIA)/1e6:.0f} MB · lo que viaja al visor: "
      f"{peso/1024:.1f} KB")
ok(peso < 200_000,
   f"🔴 lo que viaja al navegador son {peso/1024:.1f} KB (tope 200 KB), no los 123 MB del archivo")
ok(all(len(p["path_svg"]) < 20_000 for p in det["piezas"]),
   "y ningún contorno solo se desmadra")

# ─────────────────────────────────────────────────────────────────
print("\n4 · 🔴 LA MARCA ENTRA EN LA CLAVE DEL CACHÉ")
# El alta DETECTA y recién después MARCA: misma ruta, mismo mtime, resultado distinto. Sin la
# marca en la clave, el visor sirve la detección vieja para siempre. Pasó al probar este cambio.
MP._DET_CACHE.clear()
PD.marcar(COPIA, False)
det_a = MP.detectar_piezas(COPIA)              # como camino A (queda cacheado)
PD.marcar(COPIA, True)
det_b = MP.detectar_piezas(COPIA)              # ahora como camino B, SIN tocar el archivo
ok(len(det_b["piezas"]) != len(det_a["piezas"]),
   f"🔴 marcar el molde cambia lo que devuelve el visor sin tocar el archivo "
   f"(camino A: {len(det_a['piezas'])} · camino B: {len(det_b['piezas'])})")
ok(det_b.get("origen") == "con_diseno", "y lo que se sirve después de marcar es el camino B")

# ─────────────────────────────────────────────────────────────────
print("\n5 · 🔴 LOS MOLDES DEL CAMINO A NO CAMBIAN EN NADA")
import glob                                                    # noqa: E402
import pymupdf as pdfmod                                       # noqa: E402
_probados = 0
for pl in sorted(glob.glob(os.path.join(RAIZ, "entrada", "*", "plantilla.ai")))[:4]:
    d = pdfmod.open(pl)
    es, _ = PD.parece_molde_con_diseno(d)
    marcado = PD.es_camino_b(pl)
    PD.olvidar(d)
    d.close()
    ok(not es and not marcado,
       f"«{os.path.basename(os.path.dirname(pl))}» sigue siendo del camino A (y sin marca)")
    _probados += 1
if not _probados:
    print("  (no hay moldes en entrada/: no se pudo probar la no-regresión)")

MP.cerrar_abiertos()
PD.olvidar()
shutil.rmtree(TMP, ignore_errors=True)

print()
if FALLOS:
    print(f"  {len(FALLOS)} FALLO(S)")
    sys.exit(1)
print("  OK: el molde con diseño se da de alta, se ve entero y liviano, y no toca al camino A")
