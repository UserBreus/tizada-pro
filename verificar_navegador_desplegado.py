# -*- coding: utf-8 -*-
"""
CONTRATO: EL NAVEGADOR DESPLIEGA EL MOLDE IGUAL QUE EL SERVIDOR — `py verificar_navegador_desplegado.py [molde.ai ...]`

PLAN_NAVEGADOR.md, etapa 1. `frontend/src/motor/molde/desplegar.js` hace, en el navegador, lo que
`piezas_con_diseno.alta_molde_con_diseno(paginas=True)` deja en `desplegado/`:
  · `m{mesa}.json` — contornos, marco, U, placeholders «00»/«NOMBRE», línea de corte, etiqueta del
    archivo que se sacó, hash de la decisión;
  · `m{mesa}.pdf` — una página por talle con SÓLO ese talle;
  · `etiqueta_archivo.json` — la decisión por familia;
  · y el resultado del alta (registro, visor, resumen).
Se compara TODO: los JSON número a número (salvo el `sello`, que el servidor pone al guardar) y los
PDF página por página — el content-stream byte a byte, las claves de la página y cada recurso
(fuentes, XObjects, colores) resuelto hasta el fondo, con los streams comparados por su contenido.

El servidor trabaja sobre una COPIA en un temporal y en serie. ⚠️ La decisión de la etiqueta parsea
cada mesa ENTERA en Python (como en el servidor): con los moldes de 60 MB de contenido eso son varios
GB de memoria durante un minuto. Correrlo de a un molde.
"""
import glob
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
NODE = os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "desplegar.mjs")
from verificar_navegador_molde import _normal, diferencias  # noqa: E402


def _num(x):
    try:
        return float(x)
    except Exception:
        return None


def iguales_pdf(a, b, ruta, out, vistos):
    """Compara dos objetos de pikepdf resueltos (de dos PDF distintos). Anota diferencias en `out`."""
    if len(out) >= 10:
        return
    if isinstance(a, pikepdf.Object) and a.is_indirect and isinstance(b, pikepdf.Object) and b.is_indirect:
        k = (a.objgen, b.objgen)
        if k in vistos:
            return
        vistos.add(k)
    if isinstance(a, pikepdf.Stream) or isinstance(b, pikepdf.Stream):
        if not (isinstance(a, pikepdf.Stream) and isinstance(b, pikepdf.Stream)):
            out.append(f"{ruta}: uno es stream y el otro no")
            return
        da = {k: a.stream_dict[k] for k in a.stream_dict.keys() if k not in ("/Length", "/Filter", "/DecodeParms")}
        db = {k: b.stream_dict[k] for k in b.stream_dict.keys() if k not in ("/Length", "/Filter", "/DecodeParms")}
        if set(da) != set(db):
            out.append(f"{ruta}: claves del stream {sorted(set(da) ^ set(db))}")
            return
        for k in da:
            iguales_pdf(da[k], db[k], f"{ruta}{k}", out, vistos)
        try:
            ba, bb = a.read_bytes(), b.read_bytes()
        except Exception:
            ba, bb = None, None
        if ba is None or bb is None:
            if str(a.stream_dict.get("/Filter")) == str(b.stream_dict.get("/Filter")):
                ba, bb = a.read_raw_bytes(), b.read_raw_bytes()
        if ba != bb:
            out.append(f"{ruta}: contenido del stream distinto ({len(ba or b'')} vs {len(bb or b'')} bytes)")
        return
    if isinstance(a, pikepdf.Dictionary) and isinstance(b, pikepdf.Dictionary):
        ka = set(k for k in a.keys() if k != "/Parent")
        kb = set(k for k in b.keys() if k != "/Parent")
        if ka != kb:
            out.append(f"{ruta}: claves {sorted(ka ^ kb)}")
            return
        for k in sorted(ka):
            iguales_pdf(a[k], b[k], f"{ruta}{k}", out, vistos)
        return
    if isinstance(a, pikepdf.Array) and isinstance(b, pikepdf.Array):
        if len(a) != len(b):
            out.append(f"{ruta}: largo {len(a)} vs {len(b)}")
            return
        for i, (x, y) in enumerate(zip(a, b)):
            iguales_pdf(x, y, f"{ruta}[{i}]", out, vistos)
        return
    na, nb = _num(a), _num(b)
    if na is not None and nb is not None and not isinstance(a, (pikepdf.Name, pikepdf.String)):
        if na != nb:
            out.append(f"{ruta}: {a} vs {b}")
        return
    if isinstance(a, pikepdf.String) and isinstance(b, pikepdf.String):
        if bytes(a) != bytes(b):
            out.append(f"{ruta}: texto {bytes(a)[:40]!r} vs {bytes(b)[:40]!r}")
        return
    if str(a) != str(b) or type(a) is not type(b):
        out.append(f"{ruta}: {str(a)[:60]} vs {str(b)[:60]}")


def comparar_pdf(pa, pb):
    A, B = pikepdf.open(pa), pikepdf.open(pb)
    out = []
    try:
        if len(A.pages) != len(B.pages):
            return [f"páginas {len(A.pages)} vs {len(B.pages)}"]
        for i, (x, y) in enumerate(zip(A.pages, B.pages)):
            ca = x.obj.Contents.read_bytes()
            cb = y.obj.Contents.read_bytes()
            if ca != cb:
                k = next((j for j in range(min(len(ca), len(cb))) if ca[j] != cb[j]), min(len(ca), len(cb)))
                out.append(f"pág {i + 1}: contenido distinto en el byte {k} de {len(ca)}/{len(cb)}: "
                           f"{ca[max(0, k - 30):k + 30]!r} vs {cb[max(0, k - 30):k + 30]!r}")
            ka = {k for k in x.obj.keys() if k not in ("/Contents", "/Parent")}
            kb = {k for k in y.obj.keys() if k not in ("/Contents", "/Parent")}
            if ka != kb:
                out.append(f"pág {i + 1}: claves {sorted(ka ^ kb)}")
                continue
            vistos = set()
            for k in sorted(ka):
                iguales_pdf(x.obj[k], y.obj[k], f"pág {i + 1} {k}", out, vistos)
            if len(out) >= 10:
                break
    finally:
        A.close()
        B.close()
    return out


def comparar(path):
    import piezas_con_diseno as PD
    tmp = tempfile.mkdtemp(prefix="verif_nav_despl_")
    try:
        copia = os.path.join(tmp, "srv", "plantilla.ai")
        os.makedirs(os.path.dirname(copia))
        shutil.copy2(path, copia)
        t = time.time()
        alta = PD.alta_molde_con_diseno(copia, procesos=None, paginas=True)
        t_py = time.time() - t
        nav_dir = os.path.join(tmp, "nav")
        r = subprocess.run(["node", "--max-old-space-size=8192", NODE, copia, nav_dir],
                           capture_output=True, text=True, timeout=7200)
        if r.returncode != 0:
            return False, f"  Node falló: {r.stderr[-1200:]}"
        tiempos = json.load(open(os.path.join(nav_dir, "tiempos.json"), encoding="utf-8"))
        srv_dir = os.path.join(tmp, "srv", "desplegado")
        d = []
        # el alta
        nav_alta = json.load(open(os.path.join(nav_dir, "alta.json"), encoding="utf-8"))
        for k in ("mesas", "talles", "piezas", "completos", "registro", "visor", "piezas_detalle", "problemas"):
            d += diferencias(_normal(alta.get(k)), _normal(nav_alta.get(k)), f"alta.{k}")
        # la decisión de la etiqueta
        ref = json.load(open(os.path.join(srv_dir, "etiqueta_archivo.json"), encoding="utf-8"))
        nav = json.load(open(os.path.join(nav_dir, "etiqueta_archivo.json"), encoding="utf-8"))
        for k in ("v", "piezas", "familias", "manual"):
            d += diferencias(_normal(ref.get(k)), _normal(nav.get(k)), f"etiqueta.{k}")
        # cada mesa
        paginas = 0
        for fj in sorted(glob.glob(os.path.join(srv_dir, "m*.json"))):
            nombre = os.path.basename(fj)
            ref = json.load(open(fj, encoding="utf-8"))
            nj = os.path.join(nav_dir, nombre)
            if not os.path.exists(nj):
                d.append(f"{nombre}: falta en el navegador")
                continue
            nav = json.load(open(nj, encoding="utf-8"))
            ref.pop("sello", None)
            nav.pop("sello", None)
            d += diferencias(_normal(ref), _normal(nav), nombre[:-5])
            fp = fj[:-5] + ".pdf"
            if os.path.exists(fp):
                dp = comparar_pdf(fp, os.path.join(nav_dir, nombre[:-5] + ".pdf"))
                d += [f"{nombre[:-5]}.pdf {x}" for x in dp]
                paginas += len(pikepdf.open(fp).pages)
        lineas = [f"  servidor {t_py:.1f} s · navegador(Node) {tiempos['total']:.1f} s "
                  f"(contornos {tiempos.get('contornos', 0):.1f} · etiquetas {tiempos.get('etiquetas', 0):.1f} · "
                  f"páginas {tiempos.get('paginas', 0):.1f}; {tiempos['memoria_mb']:.0f} MB)"]
        if d:
            lineas.append(f"  ✗ {len(d)} diferencia(s) (las primeras):")
            lineas += [f"      {x}" for x in d[:14]]
            return False, "\n".join(lineas)
        lineas.append(f"  ✓ idéntico: {alta['mesas']} mesa(s), {len(alta['talles'])} talles, {paginas} páginas por talle, "
                      f"{len(alta['registro'])} piezas")
        return True, "\n".join(lineas)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def moldes_por_defecto():
    out = [p for p in sorted(glob.glob(os.path.join(AQUI, "entrada", "*", "plantilla.ai")))
           if os.path.isdir(os.path.join(os.path.dirname(p), "desplegado"))]
    return out + sorted(glob.glob(os.path.join(AQUI, "laboratorio", "*.ai")))


if __name__ == "__main__":
    ok_todo = True
    for p in (sys.argv[1:] or moldes_por_defecto()):
        print(f"· {os.path.basename(p)} ({os.path.getsize(p) / 1e6:.1f} MB)", flush=True)
        ok, txt = comparar(p)
        print(txt, flush=True)
        ok_todo = ok_todo and ok
    print()
    print("✅ CONTRATO VERDE — el navegador despliega el molde igual que el servidor" if ok_todo
          else "❌ CONTRATO ROTO — el desplegado del navegador difiere")
    sys.exit(0 if ok_todo else 1)
