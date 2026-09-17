# -*- coding: utf-8 -*-
"""
CONTRATO: EL NAVEGADOR LEE LAS INSTRUCCIONES DEL MOLDE IGUAL QUE EL SERVIDOR — `py verificar_navegador_contenido.py [molde.ai ...]`

PLAN_NAVEGADOR.md, etapa 0. El desplegado del camino B trabaja sobre el content-stream de cada
mesa: pikepdf lo parte en instrucciones y `molde_real` / `piezas_con_diseno` deciden cuáles
quedan. `frontend/src/motor/pdf/contenido.js` es el parser del navegador. Se compara:
  1. los BYTES del contenido (SHA-1): mupdf.js descomprime lo mismo que pikepdf;
  2. cada INSTRUCCIÓN, en orden: operador, cantidad y tipo de operandos (entero ≠ real), valores,
     nombres, textos byte a byte, arreglos y diccionarios.
Del lado del servidor se parsea TROZO POR TROZO (`cortar_capas.cortar`), como hace el
desplegado: el molde de 117 MB son 2,35 millones de instrucciones y enteras pesan 4,5 GB en Python.
"""
import decimal
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

import pikepdf

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import cortar_capas as CC  # noqa: E402

NODE = os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "contenido.mjs")


def norm(v):
    if v is None or isinstance(v, bool):
        return v
    if isinstance(v, int):
        return ["i", v]
    if isinstance(v, decimal.Decimal):
        return ["r", float(v)]
    if isinstance(v, float):
        return ["r", v]
    if isinstance(v, pikepdf.Name):
        return ["n", str(v)[1:]]
    if isinstance(v, pikepdf.String):
        return ["s", bytes(v).hex()]
    if isinstance(v, pikepdf.Array):
        return ["a", [norm(x) for x in v]]
    if isinstance(v, pikepdf.Dictionary):
        return ["d", [[k[1:], norm(v[k])] for k in sorted(v.keys())]]
    return ["?", repr(v)]


def norm_ins(ins):
    if isinstance(ins, pikepdf.ContentStreamInlineImage):
        d = ins.iimage.obj
        return {"op": "INLINE IMAGE", "dict": ["d", [[k[1:], norm(d[k])] for k in sorted(d.keys())]]}
    return {"op": str(ins.operator), "args": [norm(o) for o in ins.operands]}


def iguales(a, b):
    if a.get("op") == "INLINE IMAGE" and b.get("op") == "INLINE IMAGE":
        return a["dict"] == b["dict"]                 # los datos crudos de la imagen no se comparan acá
    return a == b


def comparar(path):
    carpeta = tempfile.mkdtemp(prefix="verif_cont_")
    r = subprocess.run(["node", NODE, path, carpeta], capture_output=True, text=True, timeout=3600)
    if r.returncode != 0:
        return False, f"  Node falló: {r.stderr[-800:]}"
    nav = json.load(open(os.path.join(carpeta, "resumen.json"), encoding="utf-8"))
    pdf = pikepdf.open(path)
    lineas, fallas = [], 0
    for i, pag in enumerate(pdf.pages):
        rn = nav["mesas"][i]
        t = time.time()
        crudo = CC.contenido_crudo(pag)
        if hashlib.sha1(crudo).hexdigest() != rn["sha1"]:
            fallas += 1
            lineas.append(f"  ✗ mesa {i + 1}: los bytes del contenido difieren ({len(crudo)} vs {rn['bytes']})")
            continue
        corte = CC.cortar(pag)
        trozos = [x[1] for x in corte["trozos"]] if corte else [crudo]
        n, distintos, ejemplo = 0, 0, None
        with open(os.path.join(carpeta, f"c{i + 1}.ndjson"), encoding="utf-8") as fh:
            for trozo in trozos:
                for ins in CC.instrucciones(trozo):
                    a = norm_ins(ins)
                    ln = fh.readline()
                    n += 1
                    if not ln:
                        distintos += 1
                        ejemplo = ejemplo or (n, a, "(el navegador terminó antes)")
                        continue
                    b = json.loads(ln)
                    if not iguales(a, b):
                        distintos += 1
                        ejemplo = ejemplo or (n, a, b)
            sobran = sum(1 for _ in fh)
        t_py = time.time() - t
        if distintos or sobran or n != rn["instrucciones"]:
            fallas += 1
            lineas.append(f"  ✗ mesa {i + 1}: {distintos} instrucciones distintas de {n} "
                          f"(navegador {rn['instrucciones']}, sobran {sobran})")
            if ejemplo:
                lineas.append(f"      primera (#{ejemplo[0]}):")
                lineas.append(f"        servidor  {str(ejemplo[1])[:300]}")
                lineas.append(f"        navegador {str(ejemplo[2])[:300]}")
        else:
            lineas.append(f"  ✓ mesa {i + 1}: {len(crudo) / 1e6:.1f} MB · {n} instrucciones idénticas · "
                          f"servidor {t_py:.1f} s (por trozos) · navegador {rn['segundos']:.1f} s")
    lineas.insert(0, f"  memoria del navegador (Node): {nav['memoria_mb']:.0f} MB")
    shutil.rmtree(carpeta, ignore_errors=True)
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
        print(f"· {os.path.basename(p)} ({os.path.getsize(p) / 1e6:.1f} MB)")
        ok, txt = comparar(p)
        print(txt)
        ok_todo = ok_todo and ok
    print()
    print("✅ CONTRATO VERDE — el navegador lee las mismas instrucciones que el servidor" if ok_todo
          else "❌ CONTRATO ROTO — el navegador no lee lo mismo")
    sys.exit(0 if ok_todo else 1)
