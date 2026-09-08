# -*- coding: utf-8 -*-
"""CONTRATO DE LA PODA DEL CAMINO B — `py verificar_poda_camino_b.py [ruta.ai]`

Al aislar el talle de un molde con el diseño adentro, ahora **se borran los trazados de los otros
talles** en vez de dejarlos escritos sin pintar (`aislar_capa(..., podar=True)`).

**Por qué:** medido sobre el archivo real, la mesa trae **398.653 operadores** —los 20 talles
encimados— y de un talle aislado **sólo 75 pintan**. Cada pieza de la tizada arrastraba los 398 mil
(7,6 MB); una hoja de 5 prendas dio **586 MB** y el aplanado para el RIP no terminaba a los 20
minutos. Lo que se borra no se dibujaba: son trazados sin su operador de pintura.

🔴 **LO QUE ESTE CONTRATO CUIDA ES QUE SE VEA EXACTAMENTE IGUAL.** La ley del proyecto es que la
tizada sea pixel-idéntica ante cambios internos, y acá se está tocando el content-stream del
archivo del usuario. Un ahorro de peso que cambie UN pixel del estampado no sirve: se compara el
render de la página podada contra el de la sin podar, pixel por pixel.

⚠️ No toca nada del usuario: trabaja sobre copias en un temporal.
"""
import os
import shutil
import sys
import tempfile
import time

sys.stdout.reconfigure(encoding="utf-8")
_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)

import pikepdf                       # noqa: E402
import pymupdf as fitz               # noqa: E402
import molde_real as MR              # noqa: E402

ORIG = sys.argv[1] if len(sys.argv) > 1 else \
    r"C:\Users\user2\Downloads\PRUEBA TIZADA PRO\para acomodo de archivos\CAMISETA JUGADOR.ai"
MESA, TALLE = 1, "M"
FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)


if not os.path.exists(ORIG):
    print(f"❌ no está el archivo de prueba:\n   {ORIG}")
    sys.exit(1)

tmp = tempfile.mkdtemp(prefix="verif_poda_")
print("CONTRATO DE LA PODA — el camino B no arrastra los otros talles\n")
print(f"copiando el archivo ({os.path.getsize(ORIG)/1e6:.0f} MB)…")
A = os.path.join(tmp, "sin_podar.ai")
B = os.path.join(tmp, "podado.ai")
shutil.copy2(ORIG, A)
shutil.copy2(ORIG, B)


def aislar(path, podar):
    pdf = pikepdf.open(path)
    pg = pdf.pages[MESA - 1]
    t0 = time.time()
    MR.aislar_capa(pdf, pg, TALLE, podar=podar)
    MR.sanear_oc(pdf, pg)
    n_ops = len(list(pikepdf.parse_content_stream(pg)))
    sal = path.replace(".ai", "_out.pdf")
    pdf.save(sal)
    pdf.close()
    return sal, n_ops, time.time() - t0


try:
    print(f"aislando el talle «{TALLE}» de la mesa {MESA}, con y sin poda…")
    pA, opsA, tA = aislar(A, False)
    pB, opsB, tB = aislar(B, True)

    # ══ 1. PESA MUCHO MENOS ══════════════════════════════════════════════════════════════════
    print("\n1 · LA PIEZA DEJA DE ARRASTRAR LOS OTROS TALLES")
    a, b = os.path.getsize(pA), os.path.getsize(pB)
    print(f"    operadores  sin podar: {opsA:>9,}   ·   podado: {opsB:>9,}   "
          f"({100 - 100*opsB/max(opsA,1):.1f} % menos)")
    print(f"    el archivo  sin podar: {a/1e6:>7.1f} MB  ·   podado: {b/1e6:>7.1f} MB")
    ok(opsB < opsA * 0.2,
       f"🔴 la poda casi no achicó el stream ({opsA:,} → {opsB:,}): la tizada va a seguir pesando")
    ok(b < a, f"🔴 el archivo podado no pesa menos ({a} → {b})")

    # ══ 2. 🔴 Y SE VE EXACTAMENTE IGUAL ══════════════════════════════════════════════════════
    print("\n2 · 🔴 Y SE VE EXACTAMENTE IGUAL (pixel a pixel)")
    dA, dB = fitz.open(pA), fitz.open(pB)
    pxA = dA[MESA - 1].get_pixmap(dpi=72, colorspace=fitz.csRGB)
    pxB = dB[MESA - 1].get_pixmap(dpi=72, colorspace=fitz.csRGB)
    ok(pxA.width == pxB.width and pxA.height == pxB.height,
       f"2. el tamaño de la página cambió: {pxA.width}x{pxA.height} vs {pxB.width}x{pxB.height}")
    if pxA.width == pxB.width and pxA.height == pxB.height:
        sA, sB = pxA.samples, pxB.samples
        distintos = sum(1 for i in range(0, len(sA), 3) if sA[i:i+3] != sB[i:i+3])
        total = pxA.width * pxA.height
        ok(distintos == 0,
           f"🔴 {distintos} de {total} píxeles CAMBIARON al podar ({100*distintos/max(total,1):.3f} %). "
           f"Se está borrando algo que sí se dibujaba: el ahorro no sirve si cambia el estampado")
        print(f"    {total:,} píxeles comparados · {distintos} distintos")
    # y el dibujo sigue estando (no se borró todo)
    _dibA = len(dA[MESA - 1].get_drawings())
    _dibB = len(dB[MESA - 1].get_drawings())
    ok(_dibB > 0, "🔴 la página podada quedó VACÍA")
    ok(abs(_dibA - _dibB) <= max(2, _dibA * 0.02),
       f"2. la cantidad de trazados dibujados cambió: {_dibA} → {_dibB}")
    print(f"    trazados que se dibujan: {_dibA} sin podar · {_dibB} podado")
    # el TEXTO (los placeholders de nombre/número) tiene que seguir
    tA_, tB_ = dA[MESA - 1].get_text("text").strip(), dB[MESA - 1].get_text("text").strip()
    ok(tA_ == tB_, f"🔴 el texto cambió al podar: {tA_[:40]!r} vs {tB_[:40]!r}")
    print(f"    texto conservado: {len(tB_.split())} palabra(s)")
    dA.close(); dB.close()

    # ══ 3. NO CUESTA MÁS ═════════════════════════════════════════════════════════════════════
    print("\n3 · Y NO TARDA MÁS QUE ANTES")
    print(f"    aislar sin podar: {tA:.1f}s  ·  podando: {tB:.1f}s")
    ok(tB < tA * 2.5 + 3, f"3. podar tardó demasiado ({tA:.1f}s → {tB:.1f}s)")

finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
if FALLOS:
    print(f"❌ {len(FALLOS)} FALLO(S):")
    for f in FALLOS:
        print("   -", f)
    sys.exit(1)
print("✅ CONTRATO VERDE — la pieza pesa una fracción y se ve idéntica, pixel por pixel")
