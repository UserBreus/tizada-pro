"""
CONTRATO DE LAS MESAS LARGAS (más de 5,08 m) — se corre con `py verificar_mesa_larga.py`.

Una página PDF no puede pasar de **14400 unidades** por lado (200 pulgadas = 508 cm). Para mesas
más largas, `componer_pdf_contorno` escribe **/UserUnit**: cada unidad vale N puntos y el lector
multiplica de vuelta. Si eso se rompe, la hoja sale a **1/N de escala** — y eso no se nota en
pantalla: se descubre con la tela ya impresa. De ahí este contrato.

Verifica, componiendo hojas de verdad con el motor:
  1. Una mesa NORMAL (< 5,08 m) sale exactamente como siempre: sin /UserUnit, medidas en puntos.
  2. Una mesa LARGA (10 m) entra en el límite del formato y mide 10 m de verdad (MediaBox × UserUnit).
  3. Las PIEZAS quedan en la posición y el tamaño correctos (en centímetros reales), no corridas
     ni a escala.
  4. El aplanado para el RIP (`aplanar_rip`) NO se come el /UserUnit.

No toca datos del usuario: dibuja piezas sintéticas en un temporal.
"""
import os
import shutil
import sys
import tempfile

import fitz
import pikepdf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nesting_contorno import CM, componer_pdf_contorno   # noqa: E402

FALLOS = []


def ok(cond, que):
    print(("  OK    " if cond else "  FALLA ") + que)
    if not cond:
        FALLOS.append(que)


def _pieza(ancho_cm, alto_cm, etiqueta="P"):
    """Una pieza de prueba: un rectángulo del tamaño pedido."""
    d = fitz.open()
    pg = d.new_page(width=ancho_cm * CM, height=alto_cm * CM)
    pg.draw_rect(pg.rect, color=(0, 0, 0), width=1)
    return {"doc": d, "etiqueta": etiqueta}


def _hoja(alto_total_cm, ancho_cm=180.0):
    """Colocaciones que llenan una mesa de `alto_total_cm`: una pieza arriba y otra al final."""
    pz1, pz2 = _pieza(40, 30, "arriba"), _pieza(40, 30, "abajo")
    w, h = 40 * CM, 30 * CM
    return [[
        {"cx": 30 * CM, "cy": 20 * CM + h / 2, "bw": w, "bh": h, "ang": 0, "pieza": pz1},
        {"cx": 30 * CM, "cy": (alto_total_cm - 25) * CM, "bw": w, "bh": h, "ang": 0, "pieza": pz2},
    ]]


def _alto_esperado(alto_total_cm, sup=1, inf=1):
    """Lo que TIENE que medir la página: la última pieza está centrada 25 cm antes del final y mide
    30 → su borde inferior queda en `alto-10`; más los márgenes de arriba y abajo."""
    return alto_total_cm - 25 + 15 + sup + inf


def _medir(path):
    """Alto/ancho REALES de cada página (MediaBox × UserUnit) en cm, y el UserUnit."""
    out = []
    with pikepdf.open(path) as pdf:
        for pg in pdf.pages:
            mb = [float(x) for x in pg.MediaBox]
            uu = float(pg.get("/UserUnit", 1))
            out.append({"uu": uu,
                        "ancho_cm": (mb[2] - mb[0]) * uu / CM,
                        "alto_cm": (mb[3] - mb[1]) * uu / CM,
                        "unidades": max(mb[2] - mb[0], mb[3] - mb[1])})
    return out


CFG = {"ancho_cm": 180.0, "espaciado_cm": 0.5, "margenes_cm": {"sup": 1, "inf": 1, "izq": 1, "der": 1}}

if __name__ == "__main__":
    tmp = tempfile.mkdtemp(prefix="mesa_larga_")
    try:
        # ── 1) MESA NORMAL: nada cambia ──────────────────────────────────────────────────────
        print("\n[1] mesa normal (3 m)")
        p1 = os.path.join(tmp, "normal.pdf")
        componer_pdf_contorno(_hoja(300), dict(CFG, altura_max_cm=500), p1, etiquetas=False)
        m1 = _medir(p1)[0]
        print(f"    UserUnit={m1['uu']:g} · {m1['ancho_cm']:.1f} cm x {m1['alto_cm']:.1f} cm")
        ok(m1["uu"] == 1, "una mesa que entra en el PDF NO usa UserUnit (sale como siempre)")
        ok(abs(m1["ancho_cm"] - 180) < 0.1, "el ancho es el de la tela (180 cm)")
        ok(abs(m1["alto_cm"] - _alto_esperado(300)) < 1.0,
           f"el alto es el de las piezas + márgenes ({m1['alto_cm']:.1f} cm, esperado {_alto_esperado(300)})")

        # ── 2) MESA LARGA: 10 m ──────────────────────────────────────────────────────────────
        print("\n[2] mesa larga (10 m)")
        p2 = os.path.join(tmp, "larga.pdf")
        componer_pdf_contorno(_hoja(1000), dict(CFG, altura_max_cm=1200), p2, etiquetas=False)
        m2 = _medir(p2)[0]
        print(f"    UserUnit={m2['uu']:g} · {m2['ancho_cm']:.1f} cm x {m2['alto_cm']/100:.2f} m "
              f"· la página ocupa {m2['unidades']:.0f} unidades (tope del PDF: 14400)")
        ok(m2["uu"] > 1, "una mesa de 10 m sí usa UserUnit")
        ok(m2["unidades"] <= 14400, "la página respeta el límite del formato (14400 unidades)")
        ok(m2["alto_cm"] > 508, f"y supera de verdad el máximo del PDF común ({m2['alto_cm']/100:.2f} m > 5,08 m)")
        ok(abs(m2["alto_cm"] - _alto_esperado(1000)) < 2,
           f"mide lo que tiene que medir ({m2['alto_cm']:.0f} cm, esperado {_alto_esperado(1000)})")
        ok(abs(m2["ancho_cm"] - 180) < 0.2, f"el ancho sigue siendo el de la tela ({m2['ancho_cm']:.1f} cm)")

        # ── 3) LAS PIEZAS, EN SU LUGAR Y TAMAÑO ──────────────────────────────────────────────
        print("\n[3] las piezas dentro de la mesa larga")
        d = fitz.open(p2)
        pg = d[0]
        # ⚠️ PyMuPDF **YA aplica el UserUnit** al abrir: `pg.rect` y `get_drawings()` vienen en
        # puntos REALES (por eso `pg.rect.height` da los 28346 pt de los 10 m, no las 14173
        # unidades del MediaBox). Multiplicar otra vez por UserUnit da el doble — pasó al escribir
        # esta prueba. pikepdf, en cambio, entrega el MediaBox crudo y ahí SÍ hay que multiplicar.
        ok(abs(pg.rect.height / CM - m2["alto_cm"]) < 2,
           "PyMuPDF ya devuelve las medidas con el UserUnit aplicado (coincide con el cálculo crudo)")
        cajas = [r["rect"] for r in pg.get_drawings()]
        anchos = sorted({round(r.width / CM, 1) for r in cajas})
        altos = sorted({round(r.height / CM, 1) for r in cajas})
        y_arriba = min(r.y0 for r in cajas) / CM
        y_abajo = max(r.y1 for r in cajas) / CM
        print(f"    piezas dibujadas: {len(cajas)} · anchos {anchos} cm · altos {altos} cm")
        print(f"    la 1ª empieza a {y_arriba:.1f} cm del borde y la última termina a {y_abajo:.1f} cm")
        ok(any(abs(a - 40) < 0.6 for a in anchos) and any(abs(a - 30) < 0.6 for a in altos),
           "cada pieza mide 40 x 30 cm reales (no quedó a escala de 1/UserUnit)")
        ok(y_abajo > 900, f"la última pieza está al final de la mesa ({y_abajo/100:.2f} m), no amontonada arriba")
        d.close()

        # ── 4) EL APLANADO PARA EL RIP NO SE LO COME ─────────────────────────────────────────
        print("\n[4] tras aplanar para el RIP")
        from aplanar_rip import aplanar_para_rip
        aplanar_para_rip(p2)
        m3 = _medir(p2)[0]
        print(f"    UserUnit={m3['uu']:g} · {m3['alto_cm']/100:.2f} m")
        ok(m3["uu"] == m2["uu"] and abs(m3["alto_cm"] - m2["alto_cm"]) < 2,
           "el aplanado conserva /UserUnit y el largo (si no, saldría a 1/N de escala)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + ("TODO OK" if not FALLOS else f"{len(FALLOS)} FALLA(S):\n  - " + "\n  - ".join(FALLOS)))
    sys.exit(1 if FALLOS else 0)
