"""
CONTRATO DEL TAMAÑO DE LA ETIQUETA — `py verificar_etiqueta_tamano.py`.

El usuario configura la etiqueta en MILÍMETROS y espera que **la letra mida eso**. Se pasaba el
número tal cual como tamaño de fuente, que es el **em**: el cuerpo entero, con lugar reservado para
las colas de la «p» y las tildes. Resultado medido: con **3 mm** configurados, la «M» de Arial Bold
salía de **2,15 mm** — 28 % menos. Sus palabras: *«si es 3 mm, todas las letras sin importar su
ubicación serán de 3 mm»*.

Se verifica midiendo la letra DIBUJADA en el PDF de la pieza (no la teoría): se generan las curvas
del texto con la misma función que usa el motor y se mide la altura real de las mayúsculas.

⚠️ No toca datos del usuario: sólo lee las fuentes del catálogo.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from texto_curvas import FuenteCurvas   # noqa: E402

MM = 72 / 25.4          # puntos por milímetro
FALLOS = []


def ok(cond, que):
    print(("  OK    " if cond else "  FALLA ") + que)
    if not cond:
        FALLOS.append(que)


def alto_dibujado(fc, texto, size_pt, solo=None):
    """Altura REAL (en mm) de lo dibujado: se recorren los contornos del glifo y se mide su bbox.
    `solo` = medir sólo esos caracteres (p. ej. la mayúscula)."""
    ys = []
    for ch in (solo or texto):
        try:
            ops, _ = fc._glifo(ch)
        except Exception:
            continue
        for _op, args in ops:
            for a in (args or ()):
                if isinstance(a, (tuple, list)) and len(a) == 2:
                    ys.append(a[1])
    if not ys:
        return 0.0
    return (max(ys) - min(ys)) * size_pt / fc.upem / MM


if __name__ == "__main__":
    fuentes = [f for f in os.listdir("catalogo_fuentes") if f.lower().endswith((".ttf", ".otf"))]
    pedido_mm = 3.0
    print(f"tamaño configurado: {pedido_mm} mm\n")
    print(f"{'fuente':<28}{'cap_ratio':>11}{'M (antes)':>12}{'M (ahora)':>12}")
    print("-" * 63)
    for nom in sorted(fuentes)[:8]:
        fc = FuenteCurvas(open(os.path.join("catalogo_fuentes", nom), "rb").read())
        antes = alto_dibujado(fc, "M", pedido_mm * MM, solo="M")              # como se hacía
        size_ok = fc.size_para_alto(pedido_mm * MM)                          # como se hace ahora
        ahora = alto_dibujado(fc, "M", size_ok, solo="M")
        print(f"{nom[:27]:<28}{fc.cap_ratio:>11.3f}{antes:>10.2f} mm{ahora:>10.2f} mm")
        ok(abs(ahora - pedido_mm) < 0.06, f"{nom}: la mayúscula mide {ahora:.2f} mm (pedidos {pedido_mm})")

    print("\ncon un texto que tiene colas hacia abajo («Mp»):")
    fc = FuenteCurvas(open("catalogo_fuentes/Arial-Bold.ttf", "rb").read())
    size_ok = fc.size_para_alto(pedido_mm * MM)
    m = alto_dibujado(fc, "Mp", size_ok, solo="M")
    p = alto_dibujado(fc, "Mp", size_ok, solo="p")
    total = alto_dibujado(fc, "Mp", size_ok)
    print(f"    la M mide {m:.2f} mm · la p (con su cola) {p:.2f} mm · el conjunto ocupa {total:.2f} mm")
    ok(abs(m - pedido_mm) < 0.06, "la M mide los 3 mm pedidos, aunque al lado haya una «p» con cola")
    ok(total > pedido_mm, "el conjunto ocupa más que 3 mm (la cola de la p baja) — eso es correcto")

    print("\nescala: el doble de milímetros = el doble de letra")
    a3 = alto_dibujado(fc, "M", fc.size_para_alto(3 * MM), solo="M")
    a6 = alto_dibujado(fc, "M", fc.size_para_alto(6 * MM), solo="M")
    print(f"    3 mm -> {a3:.2f} mm · 6 mm -> {a6:.2f} mm")
    ok(abs(a6 - 2 * a3) < 0.05, "6 mm da exactamente el doble que 3 mm")

    print("\n" + ("TODO OK" if not FALLOS else f"{len(FALLOS)} FALLA(S):\n  - " + "\n  - ".join(FALLOS)))
    sys.exit(1 if FALLOS else 0)
