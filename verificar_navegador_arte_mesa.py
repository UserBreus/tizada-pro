# -*- coding: utf-8 -*-
"""
CONTRATO: LA MESA DEL ARTE QUE DIBUJA EL NAVEGADOR ES LA MISMA QUE LA DEL SERVIDOR — `py verificar_navegador_arte_mesa.py [arte.ai]`

PLAN_NAVEGADOR.md, etapa 3 (camino A, arte separado). El paso Arte muestra cada mesa como SVG:
antes lo hacía `/api/arte/mesa_img` (`get_svg_image` con las capas «guías» y «Editable …»
apagadas); ahora `frontend/src/motor/arte/mesa.js` lo hace en un hilo del navegador con el mismo
escritor SVG de MuPDF (`pruebas/arte_mesa.mjs` es esa tarea, corrida en Node). Los dos SVG tienen
que ser IGUALES salvo los contadores de `id` (mupdf.js numera fuentes y clipPath desde 0, PyMuPDF
desde 1). Sólo lee: no toca nada del usuario.
"""
import glob
import os
import re
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import motor_pedido as MP                     # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK    " if cond else "  FALLA ") + msg)


def elegir_arte():
    if len(sys.argv) > 1:
        return sys.argv[1]
    import pymupdf
    for a in sorted(glob.glob(os.path.join(AQUI, "entrada", "**", "arte.ai"), recursive=True)):
        if os.path.getsize(a) > 3 * 1024 * 1024:
            continue
        try:
            with pymupdf.open(a) as d:
                capas = [c.get("text") for c in d.layer_ui_configs()]
        except Exception:
            continue
        if any(MP._es_capa_guia(c) for c in capas) and any(MP._es_capa_editable(c) for c in capas):
            return a
    return None


_RE_ID = re.compile(r"(font_\d+_|clip_?\d+|id=\"[a-z_]*\d+\"|url\(#[a-z_]*\d+\))")
norm = lambda s: _RE_ID.sub("X", s)           # noqa: E731

arte = elegir_arte()
if not arte:
    print("⚠️ no hay un arte con capas guía y editables en entrada/: nada que comparar")
    sys.exit(0)
print(f"\nArte: {os.path.relpath(arte, AQUI)}")
out = tempfile.mkdtemp(prefix="verif_arte_mesa_")
r = subprocess.run(["node", os.path.join("src", "motor", "pruebas", "arte_mesa.mjs"), arte, out],
                   cwd=os.path.join(AQUI, "frontend"), capture_output=True, text=True, encoding="utf-8", timeout=600)
ok(r.returncode == 0, "el hilo del navegador dibujó las mesas" + ("" if r.returncode == 0 else f": {r.stderr[-300:]}"))
if r.returncode != 0:
    sys.exit(1)

print("\n1 · LAS CAPAS QUE NO SE IMPRIMEN QUEDAN APAGADAS")
import json                                    # noqa: E402
import pymupdf                                 # noqa: E402
res = json.loads(r.stdout.strip().splitlines()[-1])
with pymupdf.open(arte) as d:
    esperadas = [c.get("text") for c in d.layer_ui_configs() if MP._es_capa_guia(c.get("text")) or MP._es_capa_editable(c.get("text"))]
    ok(sorted(res["apagadas"]) == sorted(esperadas), f"apagadas {sorted(res['apagadas'])} = {sorted(esperadas)}")
    ok(res["mesas"] == d.page_count, f"{res['mesas']} mesas")
    for c in d.layer_ui_configs():
        if MP._es_capa_guia(c.get("text")) or MP._es_capa_editable(c.get("text")):
            d.set_layer_ui_config(c["number"], action=2)
    print("\n2 · CADA MESA ES EL MISMO SVG (salvo los contadores de id)")
    iguales = 0
    for i in range(d.page_count):
        py = d[i].get_svg_image()
        js = open(os.path.join(out, f"{i + 1}.svg"), encoding="utf-8").read()
        if norm(py) == norm(js):
            iguales += 1
        else:
            print(f"    mesa {i + 1}: distinto ({len(py)} vs {len(js)} bytes)")
    ok(iguales == d.page_count, f"{iguales}/{d.page_count} mesas iguales")

print()
if FALLOS:
    print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
    for f in FALLOS:
        print("   · " + f)
    sys.exit(1)
print("✅ CONTRATO VERDE — la mesa del arte del navegador es la del servidor")
