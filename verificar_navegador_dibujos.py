# -*- coding: utf-8 -*-
"""
CONTRATO: EL NAVEGADOR VE EL MOLDE IGUAL QUE EL SERVIDOR — `py verificar_navegador_dibujos.py [molde.ai ...]`

PLAN_NAVEGADOR.md, etapa 0. Todo lo que encuentra las piezas de un molde lee
`page.get_cdrawings(extended=True)` de PyMuPDF. `frontend/src/motor/pdf/dibujos.js` es su
traducción para el navegador sobre mupdf.js (el mismo MuPDF compilado a WebAssembly). Este
contrato corre las dos cosas sobre los MISMOS archivos y exige que den lo mismo: la misma
cantidad de dibujos por mesa, en el mismo orden, con el mismo tipo, capa, nivel, `closePath`,
`seqno`, rectángulo/recorte y los mismos tramos, número a número.

Sin argumentos usa los moldes del camino B que haya en `entrada/` y los de `laboratorio/`.
Informa también el tiempo y la memoria de cada lado. No escribe nada del usuario: la salida del
navegador va a un temporal.
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
NODE_SCRIPT = os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "dibujos.mjs")
CLAVES = ("type", "dictkey_type", "layer", "level", "closePath", "even_odd", "seqno", "rect", "scissor", "items", "width")


def _normal(v):
    """tuplas → listas, floats tal cual (JSON), para comparar con lo que escribe Node."""
    if isinstance(v, (list, tuple)):
        return [_normal(x) for x in v]
    if isinstance(v, fitz.Rect):
        return [v.x0, v.y0, v.x1, v.y1]
    if isinstance(v, fitz.Point):
        return [v.x, v.y]
    return v


def _desvio(a, b):
    """El mayor desvío numérico entre dos estructuras iguales en forma; None si la forma difiere."""
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return abs(a - b)
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return None
        peor = 0.0
        for x, y in zip(a, b):
            d = _desvio(x, y)
            if d is None:
                return None
            peor = max(peor, d)
        return peor
    return 0.0 if a == b else None


def comparar(path):
    carpeta = tempfile.mkdtemp(prefix="verif_nav_")
    r = subprocess.run(["node", "--max-old-space-size=8192", NODE_SCRIPT, path, carpeta],
                       capture_output=True, text=True, timeout=3600)
    if r.returncode != 0:
        return False, f"Node falló: {r.stderr[-800:]}"
    nav = json.load(open(os.path.join(carpeta, "resumen.json"), encoding="utf-8"))
    lineas, fallas = [], 0
    doc = fitz.open(path)
    if len(nav["mesas"]) != doc.page_count:
        return False, f"  mesas: servidor {doc.page_count} · navegador {len(nav['mesas'])}"
    t_py = 0.0
    # mesa por mesa y dibujo por dibujo: nunca las dos listas enteras en memoria
    for i in range(doc.page_count):
        t = time.time()
        rm = doc[i].get_cdrawings(extended=True)
        t_py += time.time() - t
        peor, distintos, ejemplo, n_nav = 0.0, 0, None, 0
        with open(os.path.join(carpeta, f"m{i + 1}.ndjson"), encoding="utf-8") as fh:
            for k, ln in enumerate(fh):
                n_nav += 1
                if k >= len(rm):
                    continue
                a = {c: _normal(rm[k][c]) for c in CLAVES if c in rm[k]}
                b = json.loads(ln)
                b = {c: b[c] for c in CLAVES if c in b}
                ok_d = set(a) == set(b)
                dmax = 0.0
                if ok_d:
                    for c in a:
                        d = _desvio(a[c], b[c])
                        if d is None:
                            ok_d = False
                            break
                        dmax = max(dmax, d)
                if not ok_d or dmax > 0:
                    distintos += 1
                    if ejemplo is None:
                        ejemplo = (k, {c: str(a.get(c))[:160] for c in a}, {c: str(b.get(c))[:160] for c in b})
                if ok_d:
                    peor = max(peor, dmax)
        n_ref = len(rm)
        del rm
        if n_ref != n_nav:
            fallas += 1
            lineas.append(f"  ✗ mesa {i + 1}: servidor {n_ref} dibujos · navegador {n_nav}")
        if distintos:
            fallas += 1
            lineas.append(f"  ✗ mesa {i + 1}: {distintos} de {n_ref} dibujos distintos (peor desvío numérico {peor:g})")
            k, a, b = ejemplo
            lineas.append(f"      primero (#{k}):\n        servidor  {a}\n        navegador {b}")
        elif n_ref == n_nav:
            lineas.append(f"  ✓ mesa {i + 1}: {n_ref} dibujos idénticos")
    lineas.insert(0, f"  servidor {t_py:.2f} s · navegador(Node) {nav['segundos']:.2f} s (abrir {nav['abrir']:.2f} s, pico {nav['memoria_mb']:.0f} MB)")
    import shutil
    shutil.rmtree(carpeta, ignore_errors=True)
    return fallas == 0, "\n".join(lineas)


def moldes_por_defecto():
    out = []
    for p in sorted(glob.glob(os.path.join(AQUI, "entrada", "*", "plantilla.ai"))):
        if os.path.isdir(os.path.join(os.path.dirname(p), "desplegado")):
            out.append(p)
    out += sorted(glob.glob(os.path.join(AQUI, "laboratorio", "*.ai")))
    return out


if __name__ == "__main__":
    archivos = sys.argv[1:] or moldes_por_defecto()
    if not archivos:
        print("no hay moldes para comparar")
        sys.exit(2)
    todo_ok = True
    for p in archivos:
        print(f"· {os.path.relpath(p, AQUI)} ({os.path.getsize(p) / 1e6:.1f} MB)")
        ok, txt = comparar(p)
        print(txt)
        todo_ok = todo_ok and ok
    print()
    print("✅ CONTRATO VERDE — el navegador ve los mismos dibujos que el servidor" if todo_ok
          else "❌ CONTRATO ROTO — el navegador no ve lo mismo que el servidor")
    sys.exit(0 if todo_ok else 1)
