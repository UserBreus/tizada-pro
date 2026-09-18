# -*- coding: utf-8 -*-
"""
CONTRATO: EL NAVEGADOR DIBUJA LA VISTA IGUAL QUE EL SERVIDOR — `py verificar_navegador_vista.py [hoja.pdf ...]`

PLAN_NAVEGADOR.md, etapa 2. Lo que la pantalla del paso Tizada muestra —la mesa entera a 1200 px y
los recortes nítidos a 800/1600 px— lo dibuja hoy el pool del visor del servidor
(`servidor._dibujar_vista_mesa`: lista de dibujo → `get_pixmap(clip)` → PNG) y desde ahora la
computadora de quien mira (`frontend/src/motor/vista/dibujar.js`). Acá se dibuja LO MISMO de los dos
lados y se comparan los píxeles.

⚠️ QUÉ DIFERENCIA SE ACEPTA, Y POR QUÉ: la misma regla ESTRUCTURAL de
`verificar_navegador_render.py` (etapa 0, medido 2026-09-17): WebAssembly y el MuPDF nativo no dan
el mismo píxel en los bordes suavizados ni en la última fila/columna cuando la página no mide un
número entero de píxeles. Un valor distinto se acepta sólo si su vecindario 3×3 en la imagen del
servidor tiene contraste ≥ la diferencia (es un borde) o si está en la última fila/columna.
Cualquier otro píxel distinto es un dibujo distinto y el contrato corta.

⚠️ No toca nada del usuario: lee las hojas de `trabajos/` y dibuja en un temporal.
"""
import glob
import json
import os
import subprocess
import sys
import tempfile
import time

import pymupdf as fitz

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
NODE = os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "vista.mjs")
# Lo que pide la pantalla de verdad: la mesa entera (BASE_W) y los dos escalones de recorte.
CASOS = [(1200, None), (800, (0.0, 0.0, 0.5, 0.5)), (1600, (0.25, 0.25, 0.5, 0.5))]


def _distintos(py_bytes, js_bytes, W, H, tolerancia=0):
    """(cuántos valores distintos, cuántos NO se explican por borde/última fila, el peor salto).
    `tolerancia`: una diferencia de hasta tantos niveles no cuenta como «fuera de borde»."""
    distintos = peor = fuera = 0
    for k in range(min(len(py_bytes), len(js_bytes))):
        a, b = py_bytes[k], js_bytes[k]
        if a == b:
            continue
        distintos += 1
        d = abs(a - b)
        peor = max(peor, d)
        if d <= tolerancia:
            continue
        px = (k // 3) % W
        py_ = (k // 3) // W
        if px >= W - 1 or py_ >= H - 1:
            continue                       # la última fila/columna: píxel parcial
        canal = k % 3
        # ¿es un borde? el vecindario 3×3 del servidor tiene al menos tanto contraste como la
        # diferencia: entonces lo que cambió es cómo se suavizó ese borde, no lo que se dibujó.
        vals = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                x, y = px + dx, py_ + dy
                if 0 <= x < W and 0 <= y < H:
                    vals.append(py_bytes[(y * W + x) * 3 + canal])
        if vals and (max(vals) - min(vals)) >= d:
            continue
        fuera += 1
    return distintos, fuera, peor


def comparar(path):
    tmp = tempfile.mkdtemp(prefix="verif_vista_")
    lineas, fallas = [], 0
    try:
        with fitz.open(path) as d:
            paginas = min(d.page_count, 2)
            for pi in range(paginas):
                r = fitz.Rect(d[pi].rect)
                dl = d[pi].get_displaylist()
                for ancho, rec in CASOS:
                    clip = None if rec is None else fitz.Rect(
                        r.x0 + r.width * rec[0], r.y0 + r.height * rec[1],
                        r.x0 + r.width * rec[2], r.y0 + r.height * rec[3])
                    ancho_pt = (clip.width if clip is not None else r.width) or 1.0
                    z = ancho / ancho_pt
                    t = time.time()
                    pix = dl.get_pixmap(matrix=fitz.Matrix(z, z), clip=clip, alpha=False)
                    t_py = time.time() - t
                    salida = os.path.join(tmp, f"p{pi}_{ancho}.png")
                    cmd = ["node", NODE, path, str(pi + 1), str(ancho), salida]
                    if rec is not None:
                        cmd += [str(x) for x in rec]
                    rr = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=1800)
                    if rr.returncode != 0:
                        return False, f"  Node falló (página {pi + 1}, {ancho} px): {rr.stderr[-600:]}"
                    info = json.loads(rr.stdout.strip().splitlines()[-1])
                    js = fitz.Pixmap(salida)
                    etiqueta = f"página {pi + 1} · {ancho} px" + ("" if rec is None else f" · recorte {rec}")
                    if (js.width, js.height) != (pix.width, pix.height):
                        fallas += 1
                        lineas.append(f"  ✗ {etiqueta}: tamaño {pix.width}x{pix.height} vs {js.width}x{js.height}")
                        continue
                    distintos, fuera, peor = _distintos(pix.samples, js.samples, pix.width, pix.height)
                    ok = fuera == 0
                    fallas += 0 if ok else 1
                    lineas.append(
                        f"  {'✓' if ok else '✗'} {etiqueta}: {pix.width}x{pix.height} · "
                        f"{distintos} valores distintos de {len(pix.samples)} (todos de borde/última fila)"
                        if ok else
                        f"  ✗ {etiqueta}: {fuera} píxel(es) distintos que NO son borde (peor salto {peor})")
                    lineas[-1] += f" · servidor {t_py:.2f} s · navegador {info['segundos']:.2f} s"
                    # EL REPLAY (lo que usa el visor, 2026-09-18): cada dibujo de origen interpretado
                    # una vez. Es el mismo rasterizador; lo único que cambia es el redondeo del color
                    # (± 1-2 niveles, invisible) y el suavizado de algún borde. Se exige eso: ninguna
                    # diferencia mayor a 2 niveles fuera de los bordes.
                    rr2 = subprocess.run(cmd + ["--replay"], capture_output=True, text=True, encoding="utf-8", timeout=1800)
                    if rr2.returncode == 2:
                        lineas.append(f"  · {etiqueta}: esta página no se puede repetir (va por el camino exacto)")
                    elif rr2.returncode != 0:
                        fallas += 1
                        lineas.append(f"  ✗ {etiqueta}: el replay falló: {rr2.stderr[-300:]}")
                    else:
                        info2 = json.loads(rr2.stdout.strip().splitlines()[-1])
                        js2 = fitz.Pixmap(salida)
                        if (js2.width, js2.height) != (pix.width, pix.height):
                            fallas += 1
                            lineas.append(f"  ✗ {etiqueta} (replay): tamaño {pix.width}x{pix.height} vs {js2.width}x{js2.height}")
                        else:
                            d2, fuera2, peor2 = _distintos(pix.samples, js2.samples, pix.width, pix.height, tolerancia=2)
                            ok2 = fuera2 == 0
                            fallas += 0 if ok2 else 1
                            lineas.append(f"  {'✓' if ok2 else '✗'} {etiqueta} (replay): {d2} valores distintos, {fuera2} fuera de borde con más de 2 niveles (peor {peor2}) · navegador {info2['segundos']:.2f} s")
                dl = None
        return fallas == 0, "\n".join(lineas)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def hojas_por_defecto():
    """Las hojas de tizada más recientes que haya en `trabajos/` (nunca se tocan: sólo se leen)."""
    out = []
    for d in sorted(glob.glob(os.path.join(AQUI, "trabajos", "*")), key=os.path.getmtime, reverse=True):
        h = sorted(glob.glob(os.path.join(d, "HOJA_*.pdf"))) or sorted(glob.glob(os.path.join(d, "*.pdf")))
        if h:
            out.append(h[0])
        if len(out) >= 2:
            break
    return out


if __name__ == "__main__":
    hojas = sys.argv[1:] or hojas_por_defecto()
    if not hojas:
        print("  (no hay hojas de tizada para comparar: se saltea)")
        sys.exit(0)
    ok_todo = True
    for p in hojas:
        print(f"· {os.path.basename(p)} ({os.path.getsize(p) / 1e6:.1f} MB)")
        ok, txt = comparar(p)
        print(txt)
        ok_todo = ok_todo and ok
    print()
    print("✅ CONTRATO VERDE — el navegador dibuja la vista igual que el servidor" if ok_todo
          else "❌ CONTRATO ROTO — la vista del navegador difiere")
    sys.exit(0 if ok_todo else 1)
