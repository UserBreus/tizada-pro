# -*- coding: utf-8 -*-
"""
CONTRATO: EL NAVEGADOR ARMA LA FICHA TÉCNICA IGUAL QUE EL SERVIDOR — `py verificar_navegador_ficha.py`

PLAN_NAVEGADOR.md, etapa 4, punto 4. `frontend/src/motor/ficha/ficha.js` traduce `ficha_tecnica.py`
(PyMuPDF) sobre mupdf.js. Acá se arma LA MISMA ficha de los dos lados —una planilla de 30 filas que
pasa a una segunda página, un molde guía con piezas reales del motor (camino B), tipografías y un
objeto que no se sublima— y se exige: mismas páginas y tamaños, el mismo TEXTO por página
(`get_text`), y el dibujo a 100 dpi con 0 píxeles distintos fuera de bordes (regla estructural de
`verificar_navegador_vista.py`).

⚠️ No toca nada del usuario: el molde se COPIA a un temporal y `db` es un doble (nada de MSSQL).
"""
import base64
import glob
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
import ficha_tecnica as FT                     # noqa: E402

NODE = os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "ficha.mjs")
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
    caja = [W, H, 0, 0]          # dónde caen los píxeles que no son borde (para saber QUÉ difiere)
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
        caja = [min(caja[0], px), min(caja[1], py_), max(caja[2], px), max(caja[3], py_)]
    _distintos.caja = caja
    return distintos, fuera


def molde_por_defecto():
    c = [p for p in sorted(glob.glob(os.path.join(AQUI, "entrada", "*", "plantilla.ai")))
         if os.path.exists(os.path.join(os.path.dirname(p), "desplegado", "m1.pdf"))]
    return min(c, key=os.path.getsize) if c else None


def piezas_reales(orig, tmp):
    """Dos piezas de muestra armadas por el motor (el mismo PDF que nestea la hoja)."""
    carpeta = os.path.join(tmp, "molde")
    os.makedirs(carpeta)
    shutil.copy2(orig, os.path.join(carpeta, "plantilla.ai"))
    shutil.copytree(os.path.join(os.path.dirname(orig), "desplegado"), os.path.join(carpeta, "desplegado"))
    if os.path.exists(os.path.join(os.path.dirname(orig), "molde.origen")):
        shutil.copy2(os.path.join(os.path.dirname(orig), "molde.origen"), os.path.join(carpeta, "molde.origen"))
    pl = os.path.join(carpeta, "plantilla.ai")
    alta = PD.alta_molde_con_diseno(pl, procesos=None, paginas=False)
    registro, talles = alta["registro"], list(alta["talles"])
    comunes = [t for t in talles if all(t in v for v in registro.values())]
    talle = comunes[len(comunes) // 2]
    pers = PD.personalizacion_guardada(pl, armar=False)
    prendas = [{"talle": talle, "nombre": "NOMBRE", "numero": "00",
                "personalizacion": {"nombre": "NOMBRE", "numero": "00", "talle": talle}}]
    salida = os.path.join(tmp, "salida")
    os.makedirs(salida)
    por_tela = MP.generar_pedido(pl, None, registro, pers, prendas, {"carpetas": [FUENTES], "alias": {}}, salida,
                                 mapeo_arte=None, solo_piezas=True, borde_corte=BORDE, etiqueta=ETIQUETA)
    piezas = []
    for tela, lst in por_tela.items():
        for e in lst:
            b = e["base"]
            b["cstream"].write((b["base_stream"] + e["estampado"]).encode())
            buf = io.BytesIO()
            b["out"].save(buf)
            piezas.append({"nombre": e["pieza"], "w_cm": round(e["w"] / MP.CM, 1), "h_cm": round(e["h"] / MP.CM, 1),
                           "pdf": buf.getvalue(), "tela": str(tela)})
    piezas.sort(key=lambda p: str(p["nombre"]))
    return piezas


def main(orig):
    tmp = tempfile.mkdtemp(prefix="verif_ficha_")
    try:
        print("\n1 · LA MISMA ENTRADA PARA LOS DOS")
        piezas = piezas_reales(orig, tmp)
        ok(len(piezas) >= 1, f"{len(piezas)} piezas reales del motor (camino B)")
        columnas = [{"id": "cantidad", "label": "Cantidad"}, {"id": "talle", "label": "Talle"},
                    {"id": "nombre", "label": "Nombre"}, {"id": "numero", "label": "Número"}, {"id": "manga", "label": "Manga"}]
        filas = [{"cantidad": 1 + (i % 3), "talle": ["XS", "S", "M", "L", "XL"][i % 5],
                  "nombre": ["PÉREZ", "GONZÁLEZ", "MUÑOZ", "J. LÓPEZ", "Ñandú"][i % 5] + f" {i + 1}",
                  "numero": f"{(i * 7) % 99:02d}", "manga": ["corta", "larga"][i % 2]} for i in range(30)]
        # un objeto que no se sublima: un PDF chico (el navegador lo recibe como PDF; ver ficha.js)
        obj = fitz.open()
        pg = obj.new_page(width=60, height=40)
        pg.draw_rect(fitz.Rect(5, 5, 55, 35), fill=(0.2, 0.4, 0.9), color=(0, 0, 0), width=1.5)
        obj_pdf = obj.tobytes()
        obj.close()
        # ⚠️ El objeto va como MINIATURA (PNG) de los dos lados: el servidor lo dibuja desde un SVG
        # que convierte el lector de SVG de MuPDF, y ese lector NO está en mupdf.js. Medido: el mismo
        # rectángulo por SVG y por PDF difiere en 1479 píxeles del recuadro (trazo y antialias del
        # conversor). En el camino B no hay objetos editables, así que ese ramal no se usa.
        _pm = fitz.open("pdf", obj_pdf)[0].get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
        thumb_png = _pm.tobytes("png")
        proceso = {"nombre": "Escudo", "proceso": "Bordado", "pieza": "Frente", "sin_marca": False,
                   "w_cm": 8.0, "h_cm": 5.3, "medidas": [{"talles": "XS a M", "texto": "8 × 5,3 cm"}, {"talles": "L a XL", "texto": "9 × 6 cm"}],
                   "nota": "Centrado sobre el pecho"}
        guia = {"nombre": "Buzo medio cierre", "diseno": "Principal", "variante": "Manga corta",
                "opciones": "Manga: corta + larga", "ejemplo": None, "piezas": piezas,
                "fuentes": [{"campo": "nombre", "fuente": "Anton Regular", "pedida": "ClubAmerica2021-2022", "sustituida": True},
                            {"campo": "numero", "fuente": "Bungee Regular", "pedida": "Bungee Regular", "sustituida": False}],
                "procesos": [proceso]}
        planilla = {"columnas": columnas, "filas": filas}
        titulo, subtitulo = "Ficha técnica", "Buzo medio cierre · 17/09/2026"

        print("\n2 · EL SERVIDOR ARMA LA FICHA")
        py_dir = os.path.join(tmp, "py")
        os.makedirs(py_dir)
        g_py = json.loads(json.dumps(guia, default=lambda o: None))
        g_py["piezas"] = piezas
        g_py["procesos"] = [{**proceso, "thumb": base64.b64encode(thumb_png).decode()}]
        ruta_py = FT.generar_ficha(py_dir, titulo, subtitulo, planilla, [g_py])
        ok(ruta_py and os.path.exists(ruta_py), "ficha del servidor escrita")

        print("\n3 · EL NAVEGADOR ARMA LA MISMA FICHA")
        fx = {"titulo": titulo, "subtitulo": subtitulo, "planilla": planilla,
              "moldes_guia": [{**guia, "piezas": [{**p, "pdf": base64.b64encode(p["pdf"]).decode()} for p in piezas],
                               "procesos": [{**proceso, "thumb": base64.b64encode(thumb_png).decode()}]}]}
        fxp = os.path.join(tmp, "fixture.json")
        with open(fxp, "w", encoding="utf-8") as fh:
            json.dump(fx, fh, ensure_ascii=False)
        ruta_js = os.path.join(tmp, "nav.pdf")
        r = subprocess.run(["node", NODE, fxp, ruta_js], capture_output=True, text=True, encoding="utf-8", timeout=600)
        ok(r.returncode == 0, "el motor del navegador terminó" + ("" if r.returncode == 0 else f": {r.stderr[-900:]}"))
        if r.returncode != 0:
            return
        dpy, djs = fitz.open(ruta_py), fitz.open(ruta_js)
        ok(dpy.page_count == djs.page_count and dpy.page_count >= 2,
           f"mismas páginas: {dpy.page_count} = {djs.page_count} (la planilla sigue en una segunda)")
        for i in range(min(dpy.page_count, djs.page_count)):
            a, b = dpy[i], djs[i]
            ok(abs(a.rect.width - b.rect.width) < 0.01 and abs(a.rect.height - b.rect.height) < 0.01, f"página {i + 1}: mismo tamaño A4")
            ta, tb = a.get_text(), b.get_text()
            if ta != tb:
                la, lb = ta.splitlines(), tb.splitlines()
                dif = next(((x, y) for x, y in zip(la, lb) if x != y), (len(la), len(lb)))
                ok(False, f"página {i + 1}: el texto difiere: {dif!r}")
            else:
                ok(True, f"página {i + 1}: el mismo texto ({len(ta)} caracteres)")
            # el objeto que no se sublima va como PDF en el navegador y como SVG convertido en el
            # servidor: el dibujo es el mismo rectángulo, pero MuPDF lo trazará con antialias propio.
            z = 100 / 72
            pa = a.get_pixmap(matrix=fitz.Matrix(z, z), alpha=False, colorspace=fitz.csRGB)
            pb = b.get_pixmap(matrix=fitz.Matrix(z, z), alpha=False, colorspace=fitz.csRGB)
            if (pa.width, pa.height) != (pb.width, pb.height):
                ok(False, f"página {i + 1}: tamaño del dibujo {pa.width}x{pa.height} vs {pb.width}x{pb.height}")
                continue
            distintos, fuera = _distintos(pa.samples, pb.samples, pa.width, pa.height)
            ok(fuera == 0, f"página {i + 1}: dibujo a 100 dpi: {fuera} píxeles distintos que no son borde ({distintos} en total)"
               + ("" if fuera == 0 else f" · zona x {_distintos.caja[0]}-{_distintos.caja[2]}, y {_distintos.caja[1]}-{_distintos.caja[3]} px (de {pa.width}x{pa.height})"))
    finally:
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
    print("✅ CONTRATO VERDE — el navegador arma la ficha técnica igual que el servidor")
