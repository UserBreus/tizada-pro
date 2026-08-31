# -*- coding: utf-8 -*-
"""CONTRATO DE LA MEDIDA DEL DISEÑO — `py verificar_medidas_diseno.py`

La regla que protege, en una línea: **la medida que la plantilla le pide al diseñador tiene que
CUBRIR todos los talles, nunca quedarse corta.**

Por qué importa: el motor escala el diseño igualando el ALTO de la pieza en cada talle, con escala
uniforme (`cm_encajar`). Si el diseño es proporcionalmente más angosto que la pieza, lo que falta
queda **sin estampar** — una franja de tela cruda en el borde. Y sale bien impreso: nadie se entera
hasta que la prenda está cortada.

🔴 Lo que se rompió de verdad (2026-08-28): el cálculo estaba bien pero **redondeaba para abajo**
(`round(x, 1)`). En el molde del usuario, 11 de 34 piezas quedaban entre 0,1 y 0,5 mm cortas.
Ahora se redondea SIEMPRE HACIA ARRIBA (`_cm_arriba`). Sobrar no molesta: lo que sobra lo recorta
el contorno de la pieza.

Sólo LEE: trabaja con registros armados acá, no toca nada del usuario.
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


def registro(piezas):
    """{pieza: {talle: {w_cm, h_cm}}}"""
    return {p: {t: {"w_cm": w, "h_cm": h} for t, (w, h) in tt.items()} for p, tt in piezas.items()}


# ── 1 · LA REGLA DE ORO: el ancho cubre TODOS los talles ────────────────────────────────────
print("\n1 · el ancho cubre todos los talles (referencia = ALTO)")
reg = registro({
    # una pieza que se ensancha en los talles grandes: el crítico es el 2XL
    "Frente": {"S": (50.0, 70.0), "M": (55.0, 74.0), "L": (60.0, 76.0), "2XL": (70.0, 78.0)},
    # y una que se ANGOSTA: el crítico es el chico
    "Manga": {"S": (40.0, 30.0), "M": (42.0, 34.0), "L": (44.0, 38.0)},
})
med = MP.medidas_diseno(reg, "alto", talle_guia="M")
for pieza, por_talle in reg.items():
    m = med[pieza]
    base_h = m["alto_cm"]
    nec = max(d["w_cm"] * (base_h / d["h_cm"]) for d in por_talle.values())
    ok(m["ancho_cm"] + 1e-9 >= nec,
       f"«{pieza}»: da {m['ancho_cm']} cm y necesita {nec:.3f} cm")
ok(med["Frente"]["talle_critico"] == "2XL", f"el talle crítico del Frente es el 2XL ({med['Frente']['talle_critico']})")
ok(med["Manga"]["talle_critico"] == "S", f"el de la Manga es el S ({med['Manga']['talle_critico']})")

# ── 2 · NUNCA HACIA ABAJO ───────────────────────────────────────────────────────────────────
print("\n2 · 🔴 nunca redondea para abajo (el bug real del 2026-08-28)")
# 74.0 × (55.04/74.0) da 55.04 → con round() bajaba a 55.0 y dejaba 0,4 mm sin estampar
reg2 = registro({"P": {"M": (55.04, 74.0), "L": (55.0, 74.0)}})
m2 = MP.medidas_diseno(reg2, "alto", talle_guia="M")["P"]
ok(m2["ancho_cm"] >= 55.04, f"55.04 no se convierte en 55.0 (dio {m2['ancho_cm']})")
ok(m2["ancho_cm"] <= 55.2, f"…y tampoco se pasa de rosca (dio {m2['ancho_cm']})")
ok(MP._cm_arriba(10.01) == 10.1 and MP._cm_arriba(10.0) == 10.0 and MP._cm_arriba(9.999) == 10.0,
   "el redondeo al milímetro sube sólo cuando hace falta")

# ── 3 · LA OTRA REFERENCIA (ancho manda) ────────────────────────────────────────────────────
print("\n3 · con referencia = ANCHO, el que cubre es el alto")
med3 = MP.medidas_diseno(reg, "ancho", talle_guia="M")
for pieza, por_talle in reg.items():
    m = med3[pieza]
    base_w = m["ancho_cm"]
    nec = max(d["h_cm"] * (base_w / d["w_cm"]) for d in por_talle.values())
    ok(m["alto_cm"] + 1e-9 >= nec, f"«{pieza}»: alto {m['alto_cm']} cm, necesita {nec:.3f} cm")

# ── 4 · LA BASE ES LA DEL TALLE GUÍA ────────────────────────────────────────────────────────
print("\n4 · la medida se da en la escala del TALLE GUÍA")
ok(MP.medidas_diseno(reg, "alto", talle_guia="M")["Frente"]["alto_cm"] == 74.0,
   "con guía M, el alto es el del M (74 cm)")
ok(MP.medidas_diseno(reg, "alto", talle_guia="L")["Frente"]["alto_cm"] == 76.0,
   "con guía L, el alto es el del L (76 cm)")
_sin = MP.medidas_diseno(reg, "alto", talle_guia="NO_EXISTE")["Frente"]
ok(_sin["alto_cm"] == 78.0,
   f"si el talle guía no está, se toma el más grande — nunca uno chico ({_sin['alto_cm']})")

# ── 5 · LO QUE NO TIENE QUE ROMPER ──────────────────────────────────────────────────────────
print("\n5 · lo que no rompe")
ok(MP.medidas_diseno({}, "alto", talle_guia="M") == {}, "registro vacío → {} (no explota)")
ok("X" not in MP.medidas_diseno(registro({"X": {"M": (0, 0)}}), "alto", talle_guia="M"),
   "una pieza sin medidas se saltea, no inventa un número")
_una = MP.medidas_diseno(registro({"U": {"M": (30.0, 40.0)}}), "alto", talle_guia="M")["U"]
ok(_una["ancho_cm"] == 30.0 and _una["alto_cm"] == 40.0,
   f"con un solo talle, la medida es la de la pieza ({_una['ancho_cm']}×{_una['alto_cm']})")

print()
if FALLOS:
    print("✗ LA MEDIDA DEL DISEÑO NO CUBRE:")
    for f in FALLOS:
        print("   ·", f)
    sys.exit(1)
print("OK medidas: la plantilla pide una medida que CUBRE todos los talles, sin redondear para abajo")
