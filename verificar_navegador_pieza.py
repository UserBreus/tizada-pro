# -*- coding: utf-8 -*-
"""
CONTRATO: EL NAVEGADOR ARMA CADA PIEZA IGUAL QUE EL MOTOR — `py verificar_navegador_pieza.py [molde.ai]`

PLAN_NAVEGADOR.md, etapa 3 (camino B). `frontend/src/motor/pieza/base.js` traduce `_armar_base`
(el contorno como clip, la mesa desplegada como XObject, el borde de corte, la línea de corte del
archivo) y `pieza/estampar.js` traduce la parte por prenda de `generar_pieza` (nombre, número,
talle en su placeholder; la etiqueta del sistema recta, sobre el borde o por zonas). Acá se arma la
misma pieza de los dos lados con prendas de MUESTRA («NOMBRE» / «00», como la vista previa del
Arte) y se exige:
  1. la BASE (`base_stream`) y el CLIP: la misma cadena de operadores, letra por letra;
  2. el ESTAMPADO: la misma cadena, letra por letra (cuando `texto/curvas.js` está);
  3. el PDF de la pieza DIBUJADO a 100 dpi por PyMuPDF: 0 píxeles distintos fuera de bordes
     (misma regla estructural que `verificar_navegador_vista.py`).

⚠️ No toca nada del usuario: el molde se COPIA a un temporal y `db` es un doble (nada de MSSQL).
"""
import glob
import re
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"
_falso = types.ModuleType("db")
_falso.__getattr__ = lambda n: (lambda *a, **k: None)
_falso.get_doc = lambda c, default=None: default
_falso.leer_registro = lambda pid: None
sys.modules["db"] = _falso

import pymupdf as fitz                         # noqa: E402
import motor_pedido as MP                      # noqa: E402
import piezas_con_diseno as PD                 # noqa: E402

NODE = os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "pieza.mjs")
FUENTES = os.environ.get("TIZADA_FUENTES") or os.path.join(AQUI, "catalogo_fuentes")
BORDE = {"activo": True, "ancho_mm": 2.0, "color": [0.75, 0.68, 0.67, 0.90], "alineacion": "fuera"}
ETIQUETA = {"activo": True, "mostrar": {"talle": True, "pieza": True, "numero": True}, "separador": "-",
            "posicion": {"rx": 0.5, "ry": 0.92}, "posiciones": {}, "align": "centro", "size_mm": 3.0,
            "color": [0.15, 0.15, 0.15, 0.30], "borde_activo": True,
            "borde_color": [0.01, 0.01, 0.01, 0.05], "borde_mm": 1.0}
FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK    " if cond else "  FALLA ") + msg)


def _distintos(py, js, W, H):
    distintos = fuera = 0
    for k in range(min(len(py), len(js))):
        a, b = py[k], js[k]
        if a == b:
            continue
        distintos += 1
        d = abs(a - b)
        px, py_ = (k // 3) % W, (k // 3) // W
        if px >= W - 1 or py_ >= H - 1:
            continue
        canal = k % 3
        vals = [py[(y * W + x) * 3 + canal] for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                for x, y in [(px + dx, py_ + dy)] if 0 <= x < W and 0 <= y < H]
        if vals and (max(vals) - min(vals)) >= d:
            continue
        fuera += 1
    return distintos, fuera


def molde_por_defecto():
    c = [p for p in sorted(glob.glob(os.path.join(AQUI, "entrada", "*", "plantilla.ai")))
         if os.path.exists(os.path.join(os.path.dirname(p), "desplegado", "m1.pdf"))]
    return min(c, key=os.path.getsize) if c else None


def main(orig):
    tmp = tempfile.mkdtemp(prefix="verif_pieza_")
    try:
        carpeta = os.path.join(tmp, "molde")
        os.makedirs(carpeta)
        shutil.copy2(orig, os.path.join(carpeta, "plantilla.ai"))
        shutil.copytree(os.path.join(os.path.dirname(orig), "desplegado"), os.path.join(carpeta, "desplegado"))
        for extra in ("molde.origen",):
            if os.path.exists(os.path.join(os.path.dirname(orig), extra)):
                shutil.copy2(os.path.join(os.path.dirname(orig), extra), os.path.join(carpeta, extra))
        pl = os.path.join(carpeta, "plantilla.ai")
        print(f"molde: {os.path.basename(os.path.dirname(orig))} ({os.path.getsize(pl) / 1e6:.1f} MB)")

        print("\n1 · EL MOTOR ARMA LAS PIEZAS DE MUESTRA")
        alta = PD.alta_molde_con_diseno(pl, procesos=None, paginas=False)
        registro = alta["registro"]
        talles = list(alta["talles"])
        pers = PD.personalizacion_guardada(pl, armar=False)
        ok(bool(registro) and bool(talles), f"registro con {len(registro)} piezas y {len(talles)} talles")
        # sólo los talles que TODAS las piezas tienen (una capa que no es talle, o un talle con
        # huecos, no sirve para armar la muestra)
        comunes = [t for t in talles if all(t in v for v in registro.values())]
        elegidos = [comunes[0], comunes[len(comunes) // 2]] if len(comunes) > 1 else comunes[:1]
        prendas = [{"talle": t, "nombre": "NOMBRE", "numero": "00",
                    "personalizacion": {"nombre": "NOMBRE", "numero": "00", "talle": t}} for t in elegidos]
        fuentes = {"carpetas": [FUENTES], "alias": {}}
        salida = os.path.join(tmp, "salida")
        os.makedirs(salida)
        por_tela = MP.generar_pedido(pl, None, registro, pers, prendas, fuentes, salida,
                                     mapeo_arte=None, solo_piezas=True, borde_corte=BORDE, etiqueta=ETIQUETA)
        ents = [e for lst in por_tela.values() for e in lst]
        ok(len(ents) > 0, f"{len(ents)} piezas estampadas en {len(elegidos)} talle(s)")

        # el fixture para el navegador
        catalogo = [{"ruta": r, **i} for r, i in MP.catalogo_fuentes(fuentes).items()]
        piezas = []
        for nro_i, e in enumerate(ents):
            b = e["base"]
            mesa = b["mesa"]
            with open(os.path.join(carpeta, "desplegado", f"m{mesa}.json"), encoding="utf-8") as fh:
                orden = json.load(fh).get("orden") or []
            info = b["info"]
            piezas.append({"pieza": e["pieza"], "talle": e["talle"], "mesa": mesa,
                           "idx_mesa": info.get("idx_mesa", info["pieza_idx"]), "pagina": orden.index(e["talle"]),
                           "nro": int(e["etiqueta"]), "persona": prendas[int(e["etiqueta"]) - 1]["personalizacion"],
                           "info": {k: v for k, v in info.items() if k in ("ancla", "pieza_idx", "idx_mesa", "mesa")},
                           "py": {"base_stream": b["base_stream"], "clip": b["clip"], "estampado": e["estampado"],
                                  "W": b["W"], "H": b["H"], "B": b["B"], "S": b["S"]}})
        fixture = {"desplegado": os.path.join(carpeta, "desplegado"), "borde": BORDE, "etiqueta": ETIQUETA,
                   "pers": pers, "catalogo": catalogo, "alias": {}, "piezas": piezas}
        fx = os.path.join(tmp, "fixture.json")
        with open(fx, "w", encoding="utf-8") as fh:
            json.dump(fixture, fh, ensure_ascii=False)

        print("\n2 · EL NAVEGADOR ARMA LAS MISMAS PIEZAS")
        pdfs = os.path.join(tmp, "pdfs")
        os.makedirs(pdfs)
        sal = os.path.join(tmp, "nav.json")
        r = subprocess.run(["node", "--max-old-space-size=4096", NODE, fx, sal, pdfs],
                           capture_output=True, text=True, encoding="utf-8", timeout=1800)
        ok(r.returncode == 0, "el motor del navegador terminó" + ("" if r.returncode == 0 else f": {r.stderr[-800:]}"))
        if r.returncode != 0:
            return
        nav = json.load(open(sal, encoding="utf-8"))
        ok(nav.get("con_fuentes"), "con las tipografías (texto/curvas.js)")
        # el nombre del XObject lo inventa pikepdf (`add_resource(prefix="A")` → `/AH75AQ…`) y en
        # el navegador es `/A0`; la hoja lo renombra igual al componer (`_remapear`): se normaliza
        _xo = re.compile(r"/A[A-Za-z0-9_-]+ Do")
        _norm_xo = lambda t: _xo.sub("/A Do", t or "")
        iguales_base = iguales_clip = iguales_est = 0
        for p, n in zip(piezas, nav["piezas"]):
            if _norm_xo(p["py"]["base_stream"]) == _norm_xo(n["base_stream"]):
                iguales_base += 1
            elif iguales_base == 0 and p is piezas[0]:
                _a, _b = _norm_xo(p["py"]["base_stream"]).splitlines(), _norm_xo(n["base_stream"]).splitlines()
                for i, (x, y) in enumerate(zip(_a, _b)):
                    if x != y:
                        print(f"      1ª diferencia en la base de {p['pieza']}/{p['talle']}, línea {i}: py «{x[:70]}» · nav «{y[:70]}»")
                        break
            iguales_clip += p["py"]["clip"] == n["clip"]
            if nav.get("con_fuentes"):
                if p["py"]["estampado"] == n["estampado"]:
                    iguales_est += 1
                elif iguales_est == 0:
                    _a, _b = p["py"]["estampado"].splitlines(), (n["estampado"] or "").splitlines()
                    for i, (x, y) in enumerate(zip(_a, _b)):
                        if x != y:
                            print(f"      1ª diferencia en el estampado de {p['pieza']}/{p['talle']}, línea {i}: py «{x[:70]}» · nav «{y[:70]}»")
                            break
                    if len(_a) != len(_b):
                        print(f"      largo del estampado: py {len(_a)} líneas · nav {len(_b)}")
        ok(iguales_base == len(piezas), f"🔴 la BASE es letra por letra la misma en {iguales_base}/{len(piezas)} piezas")
        ok(iguales_clip == len(piezas), f"y el CLIP también ({iguales_clip}/{len(piezas)})")
        if nav.get("con_fuentes"):
            ok(iguales_est == len(piezas), f"🔴 el ESTAMPADO (nombre, número, talle, etiqueta) es letra por letra el mismo ({iguales_est}/{len(piezas)})")

        print("\n3 · DIBUJADAS, SON LA MISMA PIEZA")
        peor = 0
        for p, n, e in zip(piezas, nav["piezas"], ents):
            b = e["base"]
            # sin tipografías del lado del navegador, se compara SÓLO la base (el XObject y el borde)
            b["cstream"].write((b["base_stream"] + (e["estampado"] if nav.get("con_fuentes") else "")).encode())
            buf = io.BytesIO()
            b["out"].save(buf)
            dpy = fitz.open("pdf", buf.getvalue())
            djs = fitz.open(n["pdf"])
            z = 100 / 72
            ppy = dpy[0].get_pixmap(matrix=fitz.Matrix(z, z), alpha=False, colorspace=fitz.csRGB)
            pjs = djs[0].get_pixmap(matrix=fitz.Matrix(z, z), alpha=False, colorspace=fitz.csRGB)
            if (ppy.width, ppy.height) != (pjs.width, pjs.height):
                ok(False, f"{p['pieza']}/{p['talle']}: tamaño {ppy.width}x{ppy.height} vs {pjs.width}x{pjs.height}")
                continue
            distintos, fuera = _distintos(ppy.samples, pjs.samples, ppy.width, ppy.height)
            peor = max(peor, fuera)
            if fuera:
                ok(False, f"{p['pieza']}/{p['talle']}: {fuera} píxeles distintos que no son borde ({distintos} en total)")
        ok(peor == 0, f"las {len(piezas)} piezas dibujadas a 100 dpi: 0 píxeles distintos fuera de bordes")
    finally:
        MP.cerrar_abiertos() if hasattr(MP, "cerrar_abiertos") else None
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    orig = sys.argv[1] if len(sys.argv) > 1 else molde_por_defecto()
    if not orig:
        print("  (no hay un molde del camino B con desplegado: se saltea)")
        sys.exit(0)
    main(orig)
    print()
    if FALLOS:
        print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
        for f in FALLOS:
            print("   · " + f)
        sys.exit(1)
    print("✅ CONTRATO VERDE — el navegador arma cada pieza igual que el motor")
