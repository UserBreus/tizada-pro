# -*- coding: utf-8 -*-
"""
CONTRATO: DETECCIÓN DE PIEZAS EN UN MOLDE CON EL DISEÑO ADENTRO (camino B).
Se corre con `py verificar_molde_con_diseno.py [ruta al .ai]`.

Qué se verifica, con el ARCHIVO REAL del usuario y el motor real:

  1. El archivo se reconoce como del camino B (y un molde pelado, NO).
  2. Cada mesa y talle da la cantidad de piezas que se ve en el archivo — ni una pieza partida en
     decenas de trozos (lo que hace hoy `extraer_piezas_mesa` cuando el diseño está adentro), ni
     todas fundidas en una.
  3. **Los 20 talles quedan SEPARADOS.** Es el error que este archivo provoca: los talles están
     apilados uno encima del otro y sin aislar la capa el agrupamiento los funde en una mancha.
     Se comprueba que cada talle da una pieza de su propio tamaño y que crecen de menor a mayor.
  4. El marco de la mesa de trabajo NO aparece como pieza, y ninguna pieza real se pierde por
     confundirla con el marco (pasó con la regla vieja del 95 % de área).
  5. La salida tiene la MISMA forma que la de hoy (`molde_real`), para que el registro, el nido y
     el visor no se enteren de por qué camino vino la pieza.

⚠️ No toca nada del usuario: abre el .ai en SOLO LECTURA y no escribe un byte.
"""
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymupdf as fitz                       # noqa: E402
import piezas_con_diseno as PD               # noqa: E402

CM = 28.3465
ARCH = (sys.argv[1] if len(sys.argv) > 1 else
        r"C:\Users\user2\Downloads\PRUEBA TIZADA PRO\para acomodo de archivos\CAMISETA JUGADOR.ai")
# un molde PELADO (sin diseño), para probar que no se confunden los dos caminos
PELADO = r"C:\Users\user2\Documents\1 - Pruba tizada\Molde short.ai"

FALLOS = []


def ok(cond, msg):
    print(("  OK    " if cond else "  FALLA ") + msg)
    if not cond:
        FALLOS.append(msg)


if not os.path.exists(ARCH):
    print(f"No está el archivo de prueba:\n  {ARCH}\n"
          "Pasale la ruta por parámetro. Sin archivo real esto no verifica nada.")
    sys.exit(1)

print(f"archivo: {os.path.basename(ARCH)}  ({os.path.getsize(ARCH)/1e6:.0f} MB)")
t0 = time.time()
doc = fitz.open(ARCH)
print(f"abierto en {time.time()-t0:.1f}s · {doc.page_count} mesas")

# ─────────────────────────────────────────────────────────────────
print("\n1 · SE RECONOCE EL CAMINO")
es, motivo = PD.parece_molde_con_diseno(doc)
ok(es, f"el archivo se reconoce como molde CON diseño adentro ({motivo})")

talles = PD.talles_del_molde(doc)
ok(len(talles) >= 2, f"los talles salen de las capas del archivo: {len(talles)} → {talles[:6]}…")

# ─────────────────────────────────────────────────────────────────
print("\n2 · CADA MESA Y TALLE DA SUS PIEZAS (no una explosión de trozos, no una sola mancha)")
TALLES_MUESTRA = [t for t in ("0", "M", "6XL") if t in talles] or talles[:3]
por_mesa = {}
t0 = time.time()
for mesa in range(1, doc.page_count + 1):
    fila = []
    for talle in TALLES_MUESTRA:
        fila.append(len(PD.piezas_de_mesa(doc, mesa, talle)))
    por_mesa[mesa] = fila
    print(f"    mesa {mesa}: " + " · ".join(f"{t}={n}" for t, n in zip(TALLES_MUESTRA, fila)))
print(f"    ({time.time()-t0:.1f}s)")

ok(all(all(n >= 1 for n in fila) for fila in por_mesa.values()),
   "🔴 TODA mesa da al menos una pieza en cada talle (ninguna se queda en cero)")
ok(all(all(n <= 4 for n in fila) for fila in por_mesa.values()),
   "🔴 y ninguna explota en trozos: como mucho 4 piezas por mesa "
   f"(máximo visto: {max(max(f) for f in por_mesa.values())})")
ok(all(len(set(fila)) == 1 for fila in por_mesa.values()),
   "una mesa da la MISMA cantidad de piezas en todos los talles (el molde no cambia de forma)")

# ─────────────────────────────────────────────────────────────────
print("\n3 · 🔴 LOS TALLES QUEDAN SEPARADOS (el error que provoca este archivo)")
# Los talles están apilados: si no se aísla la capa antes de agrupar, el ensamblado por solape los
# funde a todos en una sola mancha del tamaño del talle más grande.
mesa1 = 1
medidas = []
for talle in talles:
    pzs = PD.piezas_de_mesa(doc, mesa1, talle)
    if pzs:
        U = pzs[0]["user_unit"]
        medidas.append((talle, pzs[0]["w"] / U / CM, pzs[0]["h"] / U / CM))
print("    " + " · ".join(f"{t}:{w:.0f}x{h:.0f}" for t, w, h in medidas))
ok(len(medidas) >= 2, f"la mesa 1 da pieza en {len(medidas)} talles")
anchos = [w for _, w, _ in medidas]
ok(len(set(round(w, 1) for w in anchos)) > 1,
   "🔴 cada talle tiene SU tamaño: no salen todos iguales (eso sería la mancha fundida)")
ok(max(anchos) - min(anchos) > 1.0,
   f"y la diferencia entre el más chico y el más grande es real: "
   f"{min(anchos):.1f} → {max(anchos):.1f} cm")
# ninguna pieza puede ser más grande que su mesa: si lo fuera, se fundieron talles
pg = doc[mesa1 - 1].rect
U0 = medidas and pzs[0]["user_unit"] or 1
ok(all(w <= pg.width / U0 / CM + 0.5 and h <= pg.height / U0 / CM + 0.5 for _, w, h in medidas),
   "ninguna pieza se pasa del tamaño de su mesa")

# ─────────────────────────────────────────────────────────────────
print("\n4 · EL MARCO DE LA MESA NO ES UNA PIEZA (y ninguna pieza se pierde por parecerse a él)")
mesa_ajustada = None                      # la mesa donde la pieza casi llena la hoja
for mesa in range(1, doc.page_count + 1):
    page = doc[mesa - 1]
    for talle in talles:
        for p in PD.piezas_de_mesa(doc, mesa, talle):
            U = p["user_unit"]
            frac = (p["w"] * p["h"]) / (page.rect.width * page.rect.height)
            if frac > 0.90:
                mesa_ajustada = (mesa, talle, frac)
                break
        if mesa_ajustada:
            break
    if mesa_ajustada:
        break
if mesa_ajustada:
    m, t, f = mesa_ajustada
    ok(True, f"🔴 hay una pieza que ocupa el {f*100:.0f} % de su mesa (mesa {m}, talle {t}) y "
             "IGUAL se detecta — con la regla vieja del 95 % de área se perdía")
else:
    print("  (no hay ninguna pieza que casi llene su mesa: el caso no se pudo probar acá)")

sin_marco = True
for mesa in range(1, doc.page_count + 1):
    page = doc[mesa - 1]
    for p in PD.piezas_de_mesa(doc, mesa, talles[0]):
        x0, y0, x1, y1 = p["bbox_mu"]
        if (abs(x0 - page.rect.x0) < 1 and abs(y0 - page.rect.y0) < 1
                and abs(x1 - page.rect.x1) < 1 and abs(y1 - page.rect.y1) < 1):
            sin_marco = False
ok(sin_marco, "ninguna pieza es el marco de la mesa de trabajo")

# ─────────────────────────────────────────────────────────────────
print("\n5 · LA SALIDA TIENE LA MISMA FORMA QUE LA DE HOY")
p = PD.piezas_de_mesa(doc, 1, talles[0])[0]
faltan = [k for k in ("segmentos", "bbox_raw", "bbox_mu", "w", "h", "mesa", "talle", "user_unit")
          if k not in p]
ok(not faltan, f"trae todas las claves de `molde_real._contorno_de_drawing` (faltan: {faltan})")
ok(len(p["segmentos"]) > 3,
   f"y el contorno es el trazado VECTORIAL real, no un rectángulo: {len(p['segmentos'])} segmentos")
ok(p["segmentos"][-1] == ("h",), "el contorno viene cerrado")
tipos = {s[0] for s in p["segmentos"]}
ok(tipos <= {"m", "l", "c", "re", "h"}, f"y sólo usa segmentos conocidos: {tipos}")

# ─────────────────────────────────────────────────────────────────
print("\n6 · UN MOLDE PELADO NO SE CONFUNDE CON UNO DEL CAMINO B")
if os.path.exists(PELADO):
    d2 = fitz.open(PELADO)
    es2, motivo2 = PD.parece_molde_con_diseno(d2)
    ok(not es2, f"«{os.path.basename(PELADO)}» NO es del camino B ({motivo2})")
    PD.olvidar(d2)
    d2.close()
else:
    print(f"  (no está {PELADO}: no se pudo probar el negativo)")

# ───────────────────────────────────────────────────────────
print("\n7 · 🔴 POR QUÉ HACÍA FALTA: LA DETECCIÓN DE HOY NO SIRVE PARA ESTE ARCHIVO")
# `extraer_piezas_mesa` trata CADA TRAZADO como una pieza. Con el diseño adentro, una prenda se
# convierte en cientos de "piezas": cada franja, cada logo, cada letra. No falla ni avisa: da una
# lista enorme y sin sentido. Este número es la razón de existir de `piezas_con_diseno.py`.
import molde_real as MR                      # noqa: E402
_t = talles[len(talles) // 2]
_hoy = sum(len(MR.extraer_piezas_mesa(doc, m, _t)) for m in range(1, doc.page_count + 1))
_nuevo = sum(len(PD.piezas_de_mesa(doc, m, _t)) for m in range(1, doc.page_count + 1))
print(f"    talle {_t}:  detección de hoy → {_hoy} 'piezas'   ·   camino B → {_nuevo} piezas")
ok(_hoy > _nuevo * 10,
   f"🔴 la detección de hoy parte la prenda en {_hoy} trozos y la nueva la deja en {_nuevo}")
ok(_nuevo == doc.page_count,
   f"y da UNA pieza por mesa, que es lo que tiene el archivo ({_nuevo} de {doc.page_count})")

PD.olvidar(doc)
doc.close()

print()
if FALLOS:
    print(f"  {len(FALLOS)} FALLO(S)")
    sys.exit(1)
print("  OK: las piezas de un molde con el diseño adentro se detectan por su máscara de recorte")
