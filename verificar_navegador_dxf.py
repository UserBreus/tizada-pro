# -*- coding: utf-8 -*-
"""
CONTRATO: EL NAVEGADOR IMPORTA EL DXF IGUAL QUE EL SERVIDOR — `py verificar_navegador_dxf.py [a.dxf ...]`

PLAN_NAVEGADOR.md, etapa 1, punto 7. `importar_dxf.dxf_a_pdf` (ezdxf + PyMuPDF) y
`frontend/src/motor/dxf/importar.js` (lector propio + mupdf.js) tienen que producir LO MISMO a partir
del mismo DXF de moldería:
  1. el `resumen` (piezas, talles, nombres, índices, escala) IGUAL, como diccionario;
  2. la página del mismo tamaño (1e-3 pt);
  3. las capas OCG con los mismos nombres y en el mismo orden (/OCProperties/D/Order);
  4. el content-stream de la página TOKEN POR TOKEN, normalizando los nombres `/MCn` por orden de
     primer uso. Los números se comparan COMO TEXTO: el JS reproduce el formateo de PyMuPDF
     (float32 + `round(x, 5)` + el `%g` de MuPDF), así que lo esperado es igualdad exacta. Lo que
     NO se puede reproducir es el último bit de `sin/cos/tan/atan/atan2/acos/pow` (el libm de
     Windows que usa Python contra el de V8; medido 2026-09-18 en 60 000 muestras: difieren en el
     0,04-21 % de los casos). Ese bit desaparece con `round(x, 5)` salvo que el valor caiga justo
     en un borde de redondeo: un número distinto se TOLERA sólo si difiere en ≤ 1 ulp de float32
     (lo que produce ese caso) y se informa cuántos hubo; más que eso es un dibujo distinto y corta;
  5. el dibujo: se rasterizan las dos páginas con PyMuPDF y se cuentan los píxeles distintos con
     la regla ESTRUCTURAL de `verificar_navegador_vista.py` (se tolera un valor distinto sólo en
     un borde —su vecindario 3×3 en la imagen del servidor tiene contraste ≥ la diferencia— o en
     la última fila/columna). A 100 dpi si la página entra en 2000 px de ancho; si no, a la escala
     que la deje en 2000 px (un molde de 9 m a 100 dpi son 500 MB por lado), y además un recorte
     del cuarto superior izquierdo a 100 dpi.

ENTRADAS (sólo lectura, copiadas a un temporal): `entrada/prod_20260911_165624_1ed7/
plantilla_fuente.dxf` (Optitex real, 19 piezas × 20 talles, POLYLINE + TEXT), el de Descargas
«camiseta basket masculino.dxf» si existe y es distinto, y tres DXF SINTÉTICOS que escribe este
mismo contrato con ezdxf: (a) AAMA con LWPOLYLINE con bulges, CIRCLE, ELLIPSE, SPLINE cúbica
sujeta, SPLINE cuadrática y SPLINE racional (los dos caminos de ezdxf: descomposición exacta y
aproximación), un contorno abierto que se ignora y una pieza chica que no entra en `indices`;
(b) AAMA con el contorno EXPLOTADO en LINEs (`_stitch` + ajuste Schneider con y sin esquinas);
(c) genérico: talle por capa, nombres por TEXT/MTEXT cercano, un INSERT girado y escalado.

⚠️ No toca nada del usuario ni la base: lee, copia a un temporal y compara.
"""
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time

import pymupdf as fitz

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
NODE = os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "dxf.mjs")
REAL = os.path.join(AQUI, "entrada", "prod_20260911_165624_1ed7", "plantilla_fuente.dxf")
DESCARGA = os.path.join(os.path.expanduser("~"), "Downloads", "camiseta basket masculino.dxf")
ANCHO_MAX_PX = 2000


# ── los DXF sintéticos ─────────────────────────────────────────────────────────
def _escribir_sinteticos(carpeta):
    import ezdxf
    rutas = []

    # (a) AAMA con curvas reales
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 4                     # mm
    msp = doc.modelspace()

    def texto(s, x, y):
        msp.add_text(s, dxfattribs={"insert": (x, y), "height": 5})

    def frente(x, y, w, h, b):
        # rectángulo con el cuello curvo (bulge) y una esquina redondeada
        return [(x, y, 0, 0, 0), (x + w, y, 0, 0, 0), (x + w, y + h * 0.7, 0, 0, b),
                (x + w * 0.75, y + h, 0, 0, 0), (x + w * 0.25, y + h, 0, 0, -b * 0.8), (x, y + h * 0.7, 0, 0, 0)]

    for i, (talle, esc) in enumerate((("S", 1.0), ("M", 1.1))):
        ox = 0.0
        texto(f"Size: {talle}", ox, -20 - i * 700)
        texto("Piece Name: @Frente", ox, -30 - i * 700)
        msp.add_lwpolyline(frente(ox, -i * 700, 300 * esc, 400 * esc, 0.35), format="xyseb", close=True)
        texto("Piece Name: Parche", ox + 400, -30 - i * 700)
        msp.add_circle((ox + 470, 80 - i * 700), 60 * esc)
        texto("Piece Name: Óvalo ñandú", ox + 600, -30 - i * 700)
        msp.add_ellipse((ox + 720, 80 - i * 700), major_axis=(90 * esc, 20 * esc), ratio=0.6)
        texto("Piece Name: Curva", ox + 900, -30 - i * 700)
        cps = [(900, 0), (1050, -40), (1150, 60), (1120, 220), (980, 260), (880, 180), (900, 0)]
        cps = [(x * esc + 100, y * esc - i * 700) for x, y in cps]
        msp.add_open_spline(cps, degree=3)                 # cúbica, sujeta, no racional
        texto("Piece Name: Cuadratica", ox + 1300, -30 - i * 700)
        cps2 = [(1300, 0), (1450, -30), (1520, 120), (1400, 230), (1290, 150), (1300, 0)]
        cps2 = [(x * esc, y * esc - i * 700) for x, y in cps2]
        msp.add_open_spline(cps2, degree=2)                # cuadrática → aproximación
        texto("Piece Name: Racional", ox + 1600, -30 - i * 700)
        cps3 = [(1600, 0), (1780, -20), (1820, 160), (1700, 250), (1580, 170), (1600, 0)]
        cps3 = [(x * esc, y * esc - i * 700) for x, y in cps3]
        msp.add_rational_spline(cps3, weights=[1, 0.8, 1.2, 1, 0.9, 1], degree=3)
        texto("Piece Name: Abierta", ox + 1900, -30 - i * 700)
        msp.add_lwpolyline([(1900, 0), (2000, 50), (2100, 0)], close=False)      # abierta: se ignora
        texto("Piece Name: Chica", ox + 2200, -30 - i * 700)
        msp.add_lwpolyline([(2200, 0), (2220, 0), (2220, 20), (2200, 20)], close=True)  # 4 cm²: fuera de `indices`
    ruta = os.path.join(carpeta, "sintetico_aama.dxf")
    doc.saveas(ruta)
    rutas.append(ruta)

    # (b) AAMA con el contorno explotado en LINEs (R12, como Optitex)
    doc = ezdxf.new("R12")
    msp = doc.modelspace()

    def pieza_lineas(cx, cy, esc, con_esquinas):
        pts = []
        n = 90
        for k in range(n):
            a = 2 * math.pi * k / n
            r = (120 + 30 * math.sin(3 * a)) * esc
            if con_esquinas and k % 30 == 0:
                r *= 1.25                                     # un pico: esquina > 32°
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        for k in range(n):
            a, b = pts[k], pts[(k + 1) % n]
            msp.add_line(a, b)
        # un piquete suelto (cadena chica): `_stitch` se queda con la grande
        msp.add_line((cx - 5, cy - 5), (cx + 5, cy + 5))
        msp.add_line((cx + 5, cy + 5), (cx + 5, cy - 5))

    # como en AAMA, CADA pieza lleva su «Size:» y su «Piece Name:» (el parser corta la pieza en el Size)
    for i, (talle, esc) in enumerate((("1", 1.0), ("2", 1.08))):
        msp.add_text(f"Size: {talle}", dxfattribs={"insert": (0, -i * 400), "height": 3})
        msp.add_text("Piece Name: Delantero", dxfattribs={"insert": (0, -10 - i * 400), "height": 3})
        pieza_lineas(150, 150 - i * 400, esc, False)
        msp.add_text(f"Size: {talle}", dxfattribs={"insert": (400, -i * 400), "height": 3})
        msp.add_text("Piece Name: Espalda", dxfattribs={"insert": (400, -10 - i * 400), "height": 3})
        pieza_lineas(550, 150 - i * 400, esc, True)
    ruta = os.path.join(carpeta, "sintetico_lineas.dxf")
    doc.saveas(ruta)
    rutas.append(ruta)

    # (c) genérico: talle por capa, nombre por texto cercano, INSERT girado y escalado
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 5                     # cm
    msp = doc.modelspace()
    for lay in ("S", "M", "L", "TALLE_LARGO", "XL"):
        doc.layers.add(lay)
    for i, (lay, esc) in enumerate((("S", 1.0), ("M", 1.08), ("L", 1.16), ("TALLE_LARGO", 1.24))):
        msp.add_lwpolyline([(0, 0, 0, 0, 0), (40 * esc, 0, 0, 0, 0.3), (40 * esc, 50 * esc, 0, 0, 0), (0, 50 * esc, 0, 0, 0)],
                           format="xyseb", close=True, dxfattribs={"layer": lay})
        msp.add_lwpolyline([(70, 0), (70 + 30 * esc, 0), (70 + 30 * esc, 20 * esc), (70, 20 * esc)],
                           close=True, dxfattribs={"layer": lay})
    msp.add_text("Manga", dxfattribs={"insert": (20, 25), "height": 2})
    msp.add_mtext("Cuello\\PDoble", dxfattribs={"insert": (85, 10), "char_height": 2})
    blk = doc.blocks.new("BLK", base_point=(1, 1))
    blk.add_lwpolyline([(0, 0, 0, 0, 0), (30, 0, 0, 0, -0.4), (30, 40, 0, 0, 0), (0, 40, 0, 0, 0.25)],
                       format="xyseb", close=True, dxfattribs={"layer": "XL"})
    blk.add_circle((15, 20), 6, dxfattribs={"layer": "XL"})
    msp.add_blockref("BLK", (150, 10), dxfattribs={"xscale": 1.5, "yscale": 1.5, "zscale": 1.5, "rotation": 30})
    msp.add_text("Bolsillo", dxfattribs={"insert": (150, 60), "height": 2})
    ruta = os.path.join(carpeta, "sintetico_generico.dxf")
    doc.saveas(ruta)
    rutas.append(ruta)
    return rutas


# ── comparaciones ──────────────────────────────────────────────────────────────
def _tokens(contenido):
    toks = contenido.decode("latin1").split()
    out, nombres = [], {}
    for t in toks:
        if t.startswith("/MC") and t[3:].isdigit():
            if t not in nombres:
                nombres[t] = "/L%d" % len(nombres)
            t = nombres[t]
        out.append(t)
    return out


def _ulp32(x):
    return abs(math.ldexp(1.0, math.frexp(abs(x))[1] - 24)) if x else 2 ** -149


def _comparar_tokens(a, b):
    """(fallas, tolerados, detalle)."""
    fallas, tolerados, detalle = 0, 0, []
    if len(a) != len(b):
        fallas += 1
        detalle.append(f"largo distinto: {len(a)} tokens en Python, {len(b)} en el navegador")
    for i, (x, y) in enumerate(zip(a, b)):
        if x == y:
            continue
        try:
            fx, fy = float(x), float(y)
        except ValueError:
            fallas += 1
            if len(detalle) < 6:
                detalle.append(f"token {i}: '{x}' ≠ '{y}'  [{' '.join(a[max(0, i - 4):i + 4])}]")
            continue
        if abs(fx - fy) <= _ulp32(max(abs(fx), abs(fy))) * 1.0000001:
            tolerados += 1
            if tolerados <= 3:
                detalle.append(f"token {i}: {x} ~ {y} (1 ulp de float32: último bit de libm)")
        else:
            fallas += 1
            if len(detalle) < 6:
                detalle.append(f"token {i}: {x} ≠ {y} (Δ {abs(fx - fy):.6g})  [{' '.join(a[max(0, i - 4):i + 4])}]")
    return fallas, tolerados, detalle


def _orden_ocgs(doc):
    cat = doc.pdf_catalog()
    tipo, val = doc.xref_get_key(cat, "OCProperties/D/Order")
    if tipo != "array":
        return []
    nombres = []
    toks = val.strip("[]").split()
    for i in range(0, len(toks) - 2, 3):          # "n g R" por referencia
        if toks[i].isdigit() and toks[i + 2] == "R":
            nombres.append(doc.xref_get_key(int(toks[i]), "Name")[1])
    return nombres


def _distintos(py_bytes, js_bytes, W, H):
    """La regla estructural de verificar_navegador_vista, vectorizada (numpy)."""
    import numpy as np
    a = np.frombuffer(py_bytes, dtype=np.uint8).reshape(H, W, 3).astype(np.int16)
    b = np.frombuffer(js_bytes, dtype=np.uint8).reshape(H, W, 3).astype(np.int16)
    d = np.abs(a - b)
    mask = d > 0
    distintos = int(mask.sum())
    peor = int(d.max()) if distintos else 0
    pad = np.pad(a, ((1, 1), (1, 1), (0, 0)), mode="edge")
    mx = a.copy(); mn = a.copy()
    for dy in (0, 1, 2):
        for dx in (0, 1, 2):
            v = pad[dy:dy + H, dx:dx + W, :]
            np.maximum(mx, v, out=mx); np.minimum(mn, v, out=mn)
    fuera = mask & ((mx - mn) < d)
    fuera[:, W - 1, :] = False
    fuera[H - 1, :, :] = False
    return distintos, int(fuera.sum()), peor


def _render(dpy, djs, lineas):
    fallas = 0
    ppy, pjs = dpy[0], djs[0]
    r = ppy.rect
    casos = []
    z_entera = min(100 / 72, ANCHO_MAX_PX / r.width)
    casos.append(("página entera", z_entera, None))
    if z_entera < 100 / 72:
        casos.append(("recorte ¼ a 100 dpi", 100 / 72, fitz.Rect(r.x0, r.y0, r.x0 + r.width / 4, r.y0 + r.height / 4)))
    for etiqueta, z, clip in casos:
        m = fitz.Matrix(z, z)
        a = ppy.get_pixmap(matrix=m, clip=clip, alpha=False)
        b = pjs.get_pixmap(matrix=m, clip=clip, alpha=False)
        if (a.width, a.height) != (b.width, b.height):
            lineas.append(f"  ✗ {etiqueta}: tamaño distinto {a.width}×{a.height} vs {b.width}×{b.height}")
            fallas += 1
            continue
        distintos, fuera, peor = _distintos(a.samples, b.samples, a.width, a.height)
        if fuera:
            lineas.append(f"  ✗ {etiqueta} ({a.width}×{a.height}): {fuera} píxel(es) distintos que NO son borde (peor salto {peor})")
            fallas += 1
        else:
            lineas.append(f"  ✓ {etiqueta} ({a.width}×{a.height}): {distintos} valores distintos de {len(a.samples)} (todos de borde/última fila)")
    return fallas


def comparar(ruta, tmp):
    import importar_dxf
    nombre = os.path.basename(ruta)
    lineas, fallas = [], 0
    t0 = time.time()
    pdf_py, res_py = importar_dxf.dxf_a_pdf(ruta)
    t_py = time.time() - t0
    out_pdf = os.path.join(tmp, nombre + ".js.pdf")
    out_json = os.path.join(tmp, nombre + ".js.json")
    t0 = time.time()
    r = subprocess.run(["node", NODE, ruta, out_pdf, out_json], capture_output=True, text=True, encoding="utf-8", cwd=AQUI)
    t_js = time.time() - t0
    if r.returncode != 0:
        return 1, [f"  ✗ el navegador falló: {r.stderr.strip()[-800:]}"]
    with open(out_json, encoding="utf-8") as f:
        res_js = json.load(f)
    omitidas = res_js.pop("_omitidas", [])
    res_js.pop("_segundos", None)
    if omitidas:
        lineas.append(f"  · el navegador omitió dentro de bloques: {omitidas}")
    # 1. resumen
    if res_py == res_js:
        lineas.append(f"  ✓ resumen igual: {res_py['piezas']} piezas, talles {res_py['talles']}")
    else:
        fallas += 1
        lineas.append("  ✗ resumen distinto:")
        for k in sorted(set(res_py) | set(res_js)):
            if res_py.get(k) != res_js.get(k):
                lineas.append(f"      {k}: Python={json.dumps(res_py.get(k), ensure_ascii=False)[:300]}")
                lineas.append(f"      {k}: JS    ={json.dumps(res_js.get(k), ensure_ascii=False)[:300]}")
    with fitz.open(stream=pdf_py) as dpy, fitz.open(out_pdf) as djs:
        # 2. página
        rp, rj = dpy[0].rect, djs[0].rect
        if dpy.page_count != djs.page_count or abs(rp.width - rj.width) > 1e-3 or abs(rp.height - rj.height) > 1e-3:
            fallas += 1
            lineas.append(f"  ✗ página distinta: {dpy.page_count} pág {rp.width}×{rp.height} vs {djs.page_count} pág {rj.width}×{rj.height}")
        else:
            lineas.append(f"  ✓ página {rp.width:.3f}×{rp.height:.3f} pt")
        # 3. capas
        op, oj = _orden_ocgs(dpy), _orden_ocgs(djs)
        if op != oj:
            fallas += 1
            lineas.append(f"  ✗ capas distintas: {op} vs {oj}")
        else:
            lineas.append(f"  ✓ {len(op)} capas OCG iguales y en el mismo orden")
        # 4. content-stream
        tp, tj = _tokens(dpy[0].read_contents()), _tokens(djs[0].read_contents())
        f, tol, det = _comparar_tokens(tp, tj)
        if f:
            fallas += 1
            lineas.append(f"  ✗ content-stream: {f} diferencia(s) en {len(tp)} tokens")
        else:
            lineas.append(f"  ✓ content-stream: {len(tp)} tokens iguales" + (f" ({tol} números tolerados a 1 ulp de float32)" if tol else " (exactos)"))
        for d in det:
            lineas.append("      " + d)
        # 5. dibujo
        fallas += _render(dpy, djs, lineas)
    lineas.append(f"  · Python {t_py:.1f} s · navegador {t_js:.1f} s (Node, con el arranque de mupdf.js)")
    return fallas, lineas


def main():
    import ezdxf  # noqa: F401  (el contrato escribe los sintéticos con ezdxf)
    tmp = tempfile.mkdtemp(prefix="verif_dxf_")
    entradas = []
    try:
        pedidas = [a for a in sys.argv[1:] if a.lower().endswith(".dxf")]
        if pedidas:
            for p in pedidas:
                dst = os.path.join(tmp, os.path.basename(p))
                shutil.copyfile(p, dst)
                entradas.append(dst)
        else:
            entradas += _escribir_sinteticos(tmp)
            vistos = set()
            for origen in (REAL, DESCARGA):
                if not os.path.isfile(origen):
                    print(f"  (no está {origen}: se saltea)")
                    continue
                h = hashlib.md5(open(origen, "rb").read()).hexdigest()
                if h in vistos:
                    print(f"  ({os.path.basename(origen)} es el MISMO archivo que el anterior: se compara una vez)")
                    continue
                vistos.add(h)
                dst = os.path.join(tmp, os.path.basename(origen))
                shutil.copyfile(origen, dst)
                entradas.append(dst)
        total = 0
        for ruta in entradas:
            print(f"▶ {os.path.basename(ruta)}")
            fallas, lineas = comparar(ruta, tmp)
            for l in lineas:
                print(l)
            total += fallas
        print()
        if total:
            print(f"FALLA: {total} diferencia(s) entre el importador de DXF del servidor y el del navegador")
            return 1
        print(f"TODO OK: el navegador importa los {len(entradas)} DXF igual que el servidor (resumen, página, capas, content-stream y dibujo)")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
