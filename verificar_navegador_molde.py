# -*- coding: utf-8 -*-
"""
CONTRATO: EL NAVEGADOR ARMA EL MOLDE IGUAL QUE EL SERVIDOR — `py verificar_navegador_molde.py [molde.ai ...]`

PLAN_NAVEGADOR.md, etapa 1. `frontend/src/motor/molde/contornos.js` traduce el alta del camino B
(`piezas_con_diseno.alta_molde_con_diseno`, la etapa de CONTORNOS): los talles, las piezas de cada
mesa y talle (recortes, marco, agrupar por solape, recorte con diseño, línea de corte), el orden del
talle de referencia (`canonizar_orden`), el registro («Pieza N», `pieza_idx`, `idx_mesa`, medidas,
ancla) y el visor de cada talle. Este contrato corre las dos cosas sobre los MISMOS archivos y
exige que den lo mismo:
  · por mesa, lo que va a `m{mesa}.json`: `orden`, `talles` (cada contorno, segmento por segmento),
    `marco`, `U`;
  · el resultado del alta: `talles`, `piezas`, `completos`, `registro`, `visor`, `piezas_detalle`,
    `problemas`.
Los números se comparan EXACTOS (mismo double). El servidor trabaja sobre una COPIA del molde en
un temporal: nada del usuario se toca.
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
NODE = os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "molde.mjs")


def _normal(v):
    if isinstance(v, (list, tuple)):
        return [_normal(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _normal(x) for k, x in v.items()}
    if isinstance(v, bool) or v is None or isinstance(v, str):
        return v
    if isinstance(v, (int, float)):
        return float(v)
    return v


def diferencias(a, b, ruta="", out=None, tope=8):
    """Las primeras `tope` diferencias entre dos estructuras (números exactos)."""
    if out is None:
        out = []
    if len(out) >= tope:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        if list(a.keys()) != list(b.keys()) and set(a.keys()) != set(b.keys()):
            out.append(f"{ruta}: claves {sorted(set(a) ^ set(b))[:6]}")
            return out
        for k in a:
            diferencias(a[k], b.get(k), f"{ruta}.{k}", out, tope)
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{ruta}: largo {len(a)} vs {len(b)}")
            return out
        for i, (x, y) in enumerate(zip(a, b)):
            diferencias(x, y, f"{ruta}[{i}]", out, tope)
        return out
    if a != b:
        out.append(f"{ruta}: servidor {str(a)[:120]!s} · navegador {str(b)[:120]!s}")
    return out


def comparar(path):
    import piezas_con_diseno as PD
    tmp = tempfile.mkdtemp(prefix="verif_nav_molde_")
    try:
        copia = os.path.join(tmp, "plantilla.ai")
        shutil.copy2(path, copia)
        t = time.time()
        alta = PD.alta_molde_con_diseno(copia, procesos=None, paginas=False)
        t_py = time.time() - t
        salida = os.path.join(tmp, "nav.json")
        r = subprocess.run(["node", "--max-old-space-size=8192", NODE, copia, salida],
                           capture_output=True, text=True, timeout=3600)
        if r.returncode != 0:
            return False, f"  Node falló: {r.stderr[-900:]}"
        nav = json.load(open(salida, encoding="utf-8"))
        lineas, fallas = [], 0
        lineas.append(f"  servidor {t_py:.1f} s · navegador(Node) {nav['segundos']:.1f} s")
        d = diferencias(_normal(alta["talles"]), _normal(nav["talles"]), "talles")
        for mesa in range(1, alta["mesas"] + 1):
            fj = os.path.join(tmp, "desplegado", f"m{mesa}.json")
            if not os.path.exists(fj):
                continue
            ref = json.load(open(fj, encoding="utf-8"))
            nm = nav["mesas"].get(str(mesa)) or {}
            for clave in ("orden", "talles", "marco", "U"):
                d += diferencias(_normal(ref.get(clave)), _normal(nm.get(clave)), f"m{mesa}.{clave}")
        for clave in ("mesas", "talles", "piezas", "completos", "registro", "visor", "piezas_detalle",
                      "problemas", "origen"):
            d += diferencias(_normal(alta.get(clave)), _normal(nav["alta"].get(clave)), f"alta.{clave}")
        if d:
            fallas += 1
            lineas.append(f"  ✗ {len(d)} diferencia(s) (se muestran las primeras):")
            lineas += [f"      {x}" for x in d[:12]]
        else:
            n_pz = sum(len(v) for v in alta["registro"].values())
            lineas.append(f"  ✓ idéntico: {alta['mesas']} mesa(s), {len(alta['talles'])} talles, "
                          f"{len(alta['registro'])} piezas ({n_pz} por talle), visor de {len(alta['visor'])} talles")
        return fallas == 0, "\n".join(lineas)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def moldes_por_defecto():
    out = [p for p in sorted(glob.glob(os.path.join(AQUI, "entrada", "*", "plantilla.ai")))
           if os.path.isdir(os.path.join(os.path.dirname(p), "desplegado"))]
    return out + sorted(glob.glob(os.path.join(AQUI, "laboratorio", "*.ai")))


PARECE = os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "parece.mjs")


def comparar_deteccion():
    """¿Trae el diseño adentro? El navegador tiene que decidir IGUAL que el servidor, porque de
    eso depende quién prepara el molde (Mis artículos y Configuración → Moldería aceptan cualquier
    molde; changelog 483). Se prueba con TODOS los moldes de entrada/, con y sin diseño."""
    import pymupdf as fitz
    import piezas_con_diseno as PD
    lineas, ok_todo = [], True
    for p in sorted(glob.glob(os.path.join(AQUI, "entrada", "*", "plantilla.ai"))):
        d = fitz.open(p)
        try:
            si_py, motivo_py = PD.parece_molde_con_diseno(d)
        finally:
            # 🔴 `_dibujos` cachea por `id(doc)`: sin `olvidar`, el siguiente molde que se abra puede
            # heredar los dibujos de éste (Python reusa la dirección) y la decisión sale de OTRO archivo.
            PD.olvidar(d)
            d.close()
        r = subprocess.run(["node", PARECE, p], capture_output=True, text=True, encoding="utf-8", timeout=600)
        if r.returncode != 0:
            ok_todo = False
            lineas.append(f"  ✗ {os.path.basename(os.path.dirname(p))}: Node falló: {r.stderr[-300:]}")
            continue
        nav = json.loads(r.stdout.strip().splitlines()[-1])
        igual = nav.get("si") == si_py and nav.get("motivo") == motivo_py
        ok_todo = ok_todo and igual
        lineas.append(f"  {'✓' if igual else '✗'} {os.path.basename(os.path.dirname(p))}: "
                      f"{'con' if si_py else 'sin'} diseño · servidor «{motivo_py}» · navegador «{nav.get('motivo')}»")
    return ok_todo, "\n".join(lineas)


if __name__ == "__main__":
    print("· ¿trae el diseño adentro? (el navegador decide igual que el servidor)")
    ok_todo, txt = comparar_deteccion()
    print(txt)
    for p in (sys.argv[1:] or moldes_por_defecto()):
        print(f"· {os.path.basename(p)} ({os.path.getsize(p) / 1e6:.1f} MB)")
        ok, txt = comparar(p)
        print(txt)
        ok_todo = ok_todo and ok
    print()
    print("✅ CONTRATO VERDE — el navegador arma el molde igual que el servidor" if ok_todo
          else "❌ CONTRATO ROTO — el molde del navegador difiere")
    sys.exit(0 if ok_todo else 1)
