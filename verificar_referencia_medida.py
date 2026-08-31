# -*- coding: utf-8 -*-
"""CONTRATO DE «QUÉ DIMENSIÓN MANDA» — `py verificar_referencia_medida.py`

El molde se configura con `referencia_medida` = **alto** (por defecto) o **ancho**. Eso decide
cómo entra el diseño en la pieza y, por lo tanto, **dónde cae cada objeto editable**.

🔴 El bug que arregla (reportado por el usuario 2026-08-28): la configuración sólo cambiaba las
medidas de la PLANTILLA. La tizada escalaba SIEMPRE por el alto (`cm_encajar` lo tenía fijo). Con
«ancho manda», el diseñador hacía el arte con una medida y el motor lo escalaba con otra.

Las dos cosas que se verifican, y las dos importan:
  1. **NO-REGRESIÓN**: con `alto` (lo que usan todos los moldes salvo que se diga lo contrario)
     las cuentas dan EXACTAMENTE lo de antes. Un arreglo que cambia lo que ya funcionaba no es un
     arreglo.
  2. Con `ancho`, el diseño llena el ancho y se centra a lo alto — el espejo exacto.

Sólo LEE: geometría pura, no toca archivos ni base.
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import motor_pedido as MP  # noqa: E402

FALLOS = []


def ok(cond, msg):
    print(("  OK    " if cond else "  FALLA ") + msg)
    if not cond:
        FALLOS.append(msg)


def casi(a, b, tol=1e-9):
    return abs(a - b) < tol


# Un arte de 100×200 (alto el doble que ancho) sobre una pieza de 60×80.
AW, AH = 100.0, 200.0     # mesa del arte
PW, PH = 60.0, 80.0       # pieza

print("\n1 · NO-REGRESIÓN: con «alto» las cuentas son las de siempre")
awf, ahf, offx, offy = MP._encaje(AW, AH, PW, PH, "alto")
viejo_awf = (AW * (PH / AH)) / PW          # la fórmula que había antes, tal cual
ok(casi(awf, viejo_awf), f"el ancho del diseño sobre la pieza no cambió ({awf:.6f})")
ok(casi(ahf, 1.0), "el alto del diseño llena la pieza (ahf = 1)")
ok(casi(offy, 0.0), "y no se corre a lo alto (offy = 0)")
ok(casi(offx, (1 - viejo_awf) / 2), "el centrado a lo ancho es el mismo")

print("\n2 · con «ancho» manda, es el espejo exacto")
awf2, ahf2, offx2, offy2 = MP._encaje(AW, AH, PW, PH, "ancho")
ok(casi(awf2, 1.0), "el diseño llena el ancho de la pieza (awf = 1)")
ok(casi(offx2, 0.0), "y no se corre a lo ancho (offx = 0)")
ok(casi(ahf2, (AH * (PW / AW)) / PH), f"el alto sale de la proporción del arte ({ahf2:.6f})")
ok(casi(offy2, (1 - ahf2) / 2), "y queda centrado a lo alto")

print("\n3 · la escala es UNIFORME en los dos casos (el arte no se deforma)")
# alto manda: la escala es PH/AH · ancho manda: PW/AW. El lado que manda calza exacto…
ok(casi(ahf * PH, PH), "con «alto», el alto del diseño = alto de la pieza")
ok(casi(awf2 * PW, PW), "con «ancho», el ancho del diseño = ancho de la pieza")
# …y el otro sale de la MISMA escala, nunca mayor que la pieza
# La OTRA dimensión sale de la proporción del arte: a veces queda más chica (huecos al costado)
# y a veces más grande (lo recorta el contorno). Las dos cosas son correctas y esperadas.
ok(casi(awf * PW, AW * (PH / AH)), "con «alto», el ancho sale de la proporción del arte")
ok(casi(ahf2 * PH, AH * (PW / AW)), "con «ancho», el alto sale de la proporción del arte")
ok(ahf2 > 1.0, "y en este ejemplo el arte SOBRA a lo alto: lo recorta el contorno (es lo correcto)")
ok(casi((awf * PW) / (ahf * PH), AW / AH), "con «alto» se conserva la proporción del arte")
ok(casi((awf2 * PW) / (ahf2 * PH), AW / AH), "con «ancho» también")

print("\n4 · dónde cae un objeto del arte (lo que ve el editor y lo que imprime el motor)")
# un objeto en el centro exacto de la mesa del arte
obj = (40.0, 90.0, 60.0, 110.0)     # x0,y0,x1,y1 dentro de la mesa (centrado)
mesa = (0.0, 0.0, AW, AH)
pieza = (0.0, 0.0, PW, PH)
for ref in ("alto", "ancho"):
    p = MP._pos_en_pieza(mesa, obj, pieza, ref)
    cx, cy = p["rx"] + p["rw"] / 2, p["ry"] + p["rh"] / 2
    ok(casi(cx, 0.5, 1e-6) and casi(cy, 0.5, 1e-6),
       f"con «{ref}», un objeto centrado en el arte cae centrado en la pieza ({cx:.4f}, {cy:.4f})")
    ok("ahf" in p, f"con «{ref}», la posición informa el alto del diseño (para mover)")

print("\n5 · el motor recibe la referencia (no se quedó en la configuración)")
import inspect  # noqa: E402
sig = inspect.signature(MP.generar_pedido)
ok("referencia" in sig.parameters, "`generar_pedido` la acepta")
ok(sig.parameters["referencia"].default == "alto", "y por defecto es «alto» (no cambia lo existente)")
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "motor_pedido.py"),
           encoding="utf-8").read()
ok("_manda_ancho" in src and "if _manda_ancho:" in src, "`cm_encajar` mira la referencia")
# Las dos escalas por alto que quedan tienen que estar DENTRO de un `if` de la referencia:
# una suelta sería el bug de vuelta.
_lineas = [l for l in src.split(chr(10)) if "H / (ty1 - ty0)" in l]
ok(len(_lineas) == 2 and all(l.strip().startswith(("e = H /", "s = H /")) for l in _lineas),
   f"las escalas por alto que quedan son las del `else` de la referencia ({len(_lineas)})")
ok(src.count("if _manda_ancho:") == 2,
   "🔴 los DOS lugares que escalan el diseño miran la referencia (el encaje y el tamaño "
   "configurado del editable)")
ssrv = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "servidor.py"),
            encoding="utf-8").read()
ok("MP._encaje(" in ssrv,
   "🔴 el EDITOR usa el mismo encaje que el motor (si difieren, se rompe «el arte se ve igual "
   "que la tizada»)")
ok('str((prod or {}).get("referencia_medida") or "alto"),' in ssrv,
   "la referencia entra en la clave del caché del visor (si no, el ajuste no se vería)")

print("\n6 · lo que no rompe")
ok(MP._encaje(0, 0, 10, 10, "alto") == (1.0, 1.0, 0.0, 0.0), "medidas en cero → no explota")
ok(MP._pos_en_pieza(None, obj, pieza, "ancho") is None, "sin mesa → None")

print()
if FALLOS:
    print("✗ LA REFERENCIA NO SE RESPETA:")
    for f in FALLOS:
        print("   ·", f)
    sys.exit(1)
print("OK referencia: «ancho manda» llega al motor y «alto» sigue dando exactamente lo de antes")
