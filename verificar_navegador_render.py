# -*- coding: utf-8 -*-
"""
CONTRATO: EL NAVEGADOR DIBUJA EL MOLDE IGUAL QUE EL SERVIDOR — `py verificar_navegador_render.py [molde.ai ...]`

PLAN_NAVEGADOR.md, etapa 0 (y la base de la etapa 2, el visor en el navegador). Rasteriza cada
mesa con PyMuPDF (`get_pixmap`) y con mupdf.js en Node (`frontend/src/motor/pruebas/render.mjs`),
a la misma escala, en RGB sin alfa, y cuenta los píxeles distintos. Es el mismo MuPDF: lo
esperado es CERO. Informa también cuánto se aparta el peor píxel, para distinguir un
redondeo de antialias (1-2 niveles) de un dibujo distinto.

⚠️ QUÉ DIFERENCIA SE ACEPTA, Y POR QUÉ (medido 2026-09-17). WebAssembly y el MuPDF nativo NO dan
el mismo píxel en dos lugares, y **no es la versión**: con MuPDF 1.26.2 en los dos lados
(PyMuPDF 1.26.1 en un entorno aparte contra mupdf.js 1.26.2) aparecen exactamente las mismas
diferencias que con 1.26.12 contra 1.26.4. Son:
  · píxeles de BORDE suavizado (antialias): el valor cambia unos niveles donde un trazo corta el
    píxel — en la camiseta de 28 MB, 66 valores de 1,35 millones, todos en borde;
  · la ÚLTIMA fila/columna de la imagen, cuando la página no mide un número entero de píxeles a
    esa escala (el píxel parcial se rellena distinto).
La regla es ESTRUCTURAL, no un umbral a ojo: un valor distinto se acepta sólo si en la imagen del
servidor su vecindario 3×3 tiene un contraste ≥ la diferencia (es un borde), o si está en la última
fila/columna. Cualquier otro píxel distinto es un dibujo distinto y el contrato corta. Esto es la
VISTA en pantalla: el PDF que se imprime es vector y se compara aparte, exacto.
La ICC va PRENDIDA en los dos (es lo que hace PyMuPDF): apagada difieren 625 mil valores.
"""
import os
import subprocess
import sys
import tempfile
import time

import pymupdf as fitz

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
NODE = os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "render.mjs")
ESCALA = float(os.environ.get("VERIF_RENDER_ESCALA") or 0.1)


def comparar(path):
    doc = fitz.open(path)
    lineas, fallas = [], 0
    tmp = tempfile.mkdtemp(prefix="verif_render_")
    for i in range(doc.page_count):
        t = time.time()
        pix = doc[i].get_pixmap(matrix=fitz.Matrix(ESCALA, ESCALA), alpha=False, colorspace=fitz.csRGB)
        t_py = time.time() - t
        raw = os.path.join(tmp, f"m{i + 1}.raw")
        r = subprocess.run(["node", NODE, path, str(i + 1), str(ESCALA), raw, "1"], capture_output=True, text=True, timeout=1800)
        if r.returncode != 0:
            return False, f"  Node falló en la mesa {i + 1}: {r.stderr[-600:]}"
        w, h, t_js = open(raw + ".txt").read().split()
        js = open(raw, "rb").read()
        py = pix.samples
        if (int(w), int(h)) != (pix.width, pix.height):
            fallas += 1
            lineas.append(f"  ✗ mesa {i + 1}: tamaño {pix.width}x{pix.height} vs {w}x{h}")
            continue
        distintos, peor, fuera = 0, 0, 0
        W, H = pix.width, pix.height
        for k, (a, b) in enumerate(zip(py, js)):
            if a == b:
                continue
            distintos += 1
            peor = max(peor, abs(a - b))
            px, c = divmod(k, 3)
            x, y = px % W, px // W
            if x == W - 1 or y == H - 1:
                continue                              # el píxel parcial del borde de la página
            vec = [py[(yy * W + xx) * 3 + c] for yy in range(max(0, y - 1), min(H, y + 2))
                   for xx in range(max(0, x - 1), min(W, x + 2))]
            if max(vec) - min(vec) < abs(a - b):
                fuera += 1                            # no es un borde: el dibujo es otro
        dentro = fuera == 0
        if not dentro:
            fallas += 1
        marca = "✓" if not distintos else ("≈" if dentro else "✗")
        lineas.append(f"  {marca} mesa {i + 1}: {pix.width}x{pix.height} · "
                      f"{distintos} valores distintos (peor {peor}; fuera de borde {fuera}) · servidor {t_py:.2f} s · navegador {float(t_js):.2f} s")
        os.remove(raw)
    return fallas == 0, "\n".join(lineas)


def moldes_por_defecto():
    """Sin argumentos: los moldes del camino B que haya en `entrada/` y los de `laboratorio/`."""
    import glob
    out = [p for p in sorted(glob.glob(os.path.join(AQUI, "entrada", "*", "plantilla.ai")))
           if os.path.isdir(os.path.join(os.path.dirname(p), "desplegado"))]
    return out + sorted(glob.glob(os.path.join(AQUI, "laboratorio", "*.ai")))


if __name__ == "__main__":
    ok_todo = True
    for p in (sys.argv[1:] or moldes_por_defecto()):
        print(f"· {os.path.basename(p)} ({os.path.getsize(p) / 1e6:.1f} MB) a escala {ESCALA}")
        ok, txt = comparar(p)
        print(txt)
        ok_todo = ok_todo and ok
    print()
    print("✅ CONTRATO VERDE — el navegador dibuja lo mismo (≈ = sólo bordes suavizados y la fila parcial, WebAssembly vs nativo)" if ok_todo
          else "❌ CONTRATO ROTO — el dibujo difiere")
    sys.exit(0 if ok_todo else 1)
