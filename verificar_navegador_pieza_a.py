# -*- coding: utf-8 -*-
"""
CONTRATO: EL NAVEGADOR ARMA CADA PIEZA DEL CAMINO A IGUAL QUE EL MOTOR — `py verificar_navegador_pieza_a.py`

PLAN_NAVEGADOR.md, etapa 3 (camino A: el arte SEPARADO). `frontend/src/motor/pieza/caminoA.js`
traduce los ramales del arte separado de `_armar_base` (la mesa del arte sin guías ni placeholders
como XObject, encajada al contorno por la dimensión que manda; los editables movidos / con tamaño /
recoloreados —también figura por figura— redibujados aparte; la cruz de TPU/Bordado/DTF; «sin marca»;
los objetos agregados con su transform) y `pieza/estampar.js` la parte por prenda de `generar_pieza`
en modo separado (escala `sp`, texto plano, texto FIEL sobre una curva, pila de apariencias y trazo
a escala). Se arman las mismas piezas de los dos lados con el molde real del camino A
(`prod_20260820_095558_38bc`) y tres artes suyos (jugador, golero con fuente CID, refwerrf con
`#rango`, nombre curvo y escudo de cuatro figuras) y se exige:
  1. la MESA del arte elegida (`mesa_arte`), la BASE (`base_stream`) y el CLIP: la misma cadena,
     letra por letra (los nombres de XObject que inventa pikepdf se normalizan);
  2. el ESTAMPADO: la misma cadena, letra por letra;
  3. el PDF de la pieza DIBUJADO a 100 dpi por PyMuPDF: 0 píxeles distintos fuera de bordes.

⚠️ No toca nada del usuario: el molde, sus datos y los artes se COPIAN a un temporal, el objeto
agregado se fabrica ahí con pikepdf, y `db` es un doble (nada de MSSQL).
"""
import glob
import io
import json
import os
import re
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

import numpy as np                             # noqa: E402
import pikepdf                                 # noqa: E402
import pymupdf as fitz                         # noqa: E402
import motor_pedido as MP                      # noqa: E402

NODE = os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "pieza_a.mjs")
NODE_REPETIDO = os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "contexto_a_repetido.mjs")
FUENTES = os.environ.get("TIZADA_FUENTES") or os.path.join(AQUI, "catalogo_fuentes")
PID = "prod_20260820_095558_38bc"
ARTES = ["jugador", "golero", "refwerrf"]
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
    """(valores distintos, los que NO se explican por un borde): la regla de `verificar_navegador_vista.py`,
    vectorizada porque las piezas del camino A miden hasta 2600×3300 px a 100 dpi."""
    a = np.frombuffer(py, dtype=np.uint8).reshape(H, W, 3).astype(np.int16)
    b = np.frombuffer(js, dtype=np.uint8).reshape(H, W, 3).astype(np.int16)
    d = np.abs(a - b)
    distintos = int((d > 0).sum())
    if not distintos:
        return 0, 0
    # el salto máximo entre vecinos 3×3 de la imagen de Python: si es ≥ la diferencia, es borde
    pad = np.pad(a, ((1, 1), (1, 1), (0, 0)), mode="edge")
    mx = np.full_like(a, -32768); mn = np.full_like(a, 32767)
    for dy in (0, 1, 2):
        for dx in (0, 1, 2):
            v = pad[dy:dy + H, dx:dx + W]
            mx = np.maximum(mx, v); mn = np.minimum(mn, v)
    fuera = (d > 0) & ((mx - mn) < d)
    fuera[H - 1:, :, :] = False
    fuera[:, W - 1:, :] = False
    return distintos, int(fuera.sum())


def _objeto_agregado(carpeta):
    """Un PDF suelto como los que fabrica `objetos_agregados.normalizar_a_pdf`: un rectángulo y un
    rombo en CMYK sobre una página de 200×100 pt."""
    os.makedirs(carpeta, exist_ok=True)
    pdf = pikepdf.new()
    page = pdf.add_blank_page(page_size=(200, 100))
    page.Contents = pdf.make_stream(
        b"q 0.1 0.9 0.9 0 k 10 10 180 80 re f Q\n"
        b"q 0 0.8 0.2 0 k 100 15 m 185 50 l 100 85 l 15 50 l h f Q\n"
        b"q 0 0 0 1 K 4 w 20 20 m 180 80 l S Q\n")
    ruta = os.path.join(carpeta, "oa_1.pdf")
    pdf.save(ruta)
    return {"dir": carpeta, "objetos": [{"id": "oa_1", "nombre": "Sello", "archivo": "oa_1.pdf", "pieza": "Dorso 1",
                                        "w_cm": 6.0, "h_cm": 3.0, "tipo": "vector",
                                        "transforms": {"v_b": {"2XL": {"dx": 0.1, "dy": 0.2, "rot": 30, "scale": 0.8}}}}]}


def _prenda(talle, variante, piezas, nombre="PÉREZ", numero="10"):
    p = {"talle": talle, "nombre": nombre, "numero": numero,
         "personalizacion": {"nombre": nombre, "numero": numero, "talle": talle},
         "variante_piezas": piezas}
    if variante:
        p["variante_clave"] = variante
    return p


def _casos(tmp, pl, reg, artes):
    """Los tres artes con su configuración: qué prendas, qué editables, qué objetos agregados."""
    casos = []
    # ── jugador: escudo movido + con tamaño (v_a), TPU → cruz (v_b), recoloreado (v_c), sin marca
    #    (v_d), fila SIN variable (`_cfg_var`), objeto agregado en Dorso 1 (identidad y con transform)
    casos.append({
        "nombre": "jugador", "arte": artes["jugador"],
        "mapeo_arte": {"mapeo": MP.mapeo_por_nombre(artes["jugador"], reg), "por_variable": {}},
        "editables_cfg": {"v_a": {"escudo": {"M": {"dx": 0.08, "dy": -0.05, "rot": 15, "scale": 1.2}}},
                          "v_b": {}, "v_c": {}, "v_d": {}},
        "editables_tamano": {"escudo": {"M": {"apaisado": [8, 8], "vertical": [8, 8]}}},
        "editables_color": {"v_c": {"escudo": {"fill": [0.9, 0.1, 0.1, 0.0], "stroke": None}}},
        "editables_marca": {"v_b": {"escudo": "tpu"}},
        "editables_sin_marca": {"v_d": {"escudo": True}},
        "objetos_agregados": _objeto_agregado(os.path.join(tmp, "oa_jugador")),
        "prendas": [
            # «Tapa costura» no está mapeada a ninguna mesa del arte: pieza SIN diseño (sólo borde y etiqueta)
            _prenda("M", "v_a", ["Frente 1", "Dorso 1", "Manga corta derecha 1", "Cuello 1", "Tapa costura"]),
            _prenda("2XL", "v_b", ["Frente 1", "Dorso 1"], nombre="Gómez", numero="7"),
            _prenda("M", None, ["Frente 1"]),
            _prenda("2XL", "v_c", ["Frente 1"]),
            _prenda("M", "v_d", ["Frente 1"]),
            _prenda("2XL", "v_a", ["Frente 1", "Dorso 1"]),
        ]})
    # ── golero: la fuente CID (Anton-Regular) en nombre y número; editables sin configuración
    casos.append({
        "nombre": "golero", "arte": artes["golero"],
        "mapeo_arte": {"mapeo": MP.mapeo_por_nombre(artes["golero"], reg), "por_variable": {}},
        "editables_cfg": {}, "editables_tamano": None, "editables_color": None, "editables_marca": None,
        "editables_sin_marca": None, "objetos_agregados": None,
        "prendas": [_prenda("M", "v_a", ["Frente 1", "Dorso 1"], nombre="D'ALESSANDRO", numero="1")]})
    # ── refwerrf: mesas `#rango` (la variante exacta/rango manda sobre el mapeo), mapeo POR
    #    VARIABLE, nombre sobre una CURVA con trazo y pila de apariencias, escudo de 4 figuras con
    #    color POR FIGURA (`aislar_capa_objetos`)
    mapeo_r = MP.mapeo_por_nombre(artes["refwerrf"], reg)
    eds = MP.extraer_editables(artes["refwerrf"], con_thumb=False)
    esc15 = next((o for o in eds if o["mesa"] == 15 and MP._norm_nombre(o["nombre"]) == "escudo"), None)
    oids = [x["obj_id"] for x in (esc15 or {}).get("objetos") or []][:2]
    # el IDENT de una figura es «nombre + U+001F + obj_id» (`_EDIT_SEP` del servidor, `SEP` del motor)
    color_fig = {"v_a": {}}
    if len(oids) >= 2:
        color_fig["v_a"]["escudo" + oids[0]] = {"fill": [0.0, 0.6, 0.95, 0.0], "stroke": None}
        color_fig["v_a"]["escudo" + oids[1]] = {"fill": None, "stroke": [0.2, 0.9, 0.2, 0.1]}
    casos.append({
        "nombre": "refwerrf", "arte": artes["refwerrf"],
        "mapeo_arte": {"mapeo": {**mapeo_r, "Dorso 1": 23},
                       "por_variable": {"v_a": {**mapeo_r, "Dorso 1": 23, "Cuello 1": 2}}},
        "editables_cfg": {"v_a": {}}, "editables_tamano": None, "editables_color": color_fig,
        "editables_marca": None, "editables_sin_marca": None, "objetos_agregados": None,
        "prendas": [_prenda("M", "v_a", ["Frente 1", "Dorso 1", "Cuello 1"], nombre="Ñandú", numero="23"),
                    _prenda("8", None, ["Frente 1", "Dorso 1"], nombre="ZÚÑIGA", numero="4")]})
    return casos


def main():
    tmp = tempfile.mkdtemp(prefix="verif_pieza_a_")
    try:
        entrada = os.path.join(AQUI, "entrada", PID)
        datos = os.path.join(AQUI, "datos", "productos", PID)
        carpeta = os.path.join(tmp, "molde")
        os.makedirs(carpeta)
        shutil.copy2(os.path.join(entrada, "plantilla.ai"), os.path.join(carpeta, "plantilla.ai"))
        for f in ("piezas.json", "emparejado_talles.json"):
            shutil.copy2(os.path.join(datos, f), os.path.join(carpeta, f))
        artes = {}
        for d in ARTES:
            os.makedirs(os.path.join(carpeta, d))
            artes[d] = os.path.join(carpeta, d, "arte.ai")
            shutil.copy2(os.path.join(entrada, "disenos", d, "arte.ai"), artes[d])
        pl = os.path.join(carpeta, "plantilla.ai")
        print(f"molde: {PID} ({os.path.getsize(pl) / 1e6:.1f} MB) · artes: " +
              ", ".join(f"{d} ({os.path.getsize(artes[d]) / 1e6:.1f} MB)" for d in ARTES))

        print("\n1 · EL MOTOR ARMA LAS PIEZAS")
        # el registro del molde con el nombrado visual del usuario (piezas.json → talle guía M)
        pz = json.load(open(os.path.join(carpeta, "piezas.json"), encoding="utf-8"))
        emp = json.load(open(os.path.join(carpeta, "emparejado_talles.json"), encoding="utf-8"))
        asign = [{"idx": int(p["ancla"]["idx"]), "nombre": p["clave"]}
                 for p in pz["piezas"] if (p.get("ancla") or {}).get("talle") == "M"]
        alta = MP.alta_plantilla_manual(pl, asign, 1, "M", emparejado=emp)
        reg = alta["registro"]
        ok(len(reg) >= 30 and not alta["problemas"], f"registro con {len(reg)} piezas (nombrado visual, guía M)")
        vorden = MP.talles_orden_archivo(pl, sorted({t for v in reg.values() for t in v}))
        fuentes = {"carpetas": [FUENTES], "alias": {}}
        catalogo = [{"ruta": r, **i} for r, i in MP.catalogo_fuentes(fuentes).items()]
        casos = _casos(tmp, pl, reg, artes)
        fx_casos = []
        entradas = []
        for c in casos:
            pers = MP.extraer_personalizacion(c["arte"])
            salida = os.path.join(tmp, "salida_" + c["nombre"])
            os.makedirs(salida)
            por_tela = MP.generar_pedido(pl, c["arte"], reg, pers, c["prendas"], fuentes, salida,
                                         mapeo_arte=c["mapeo_arte"], solo_piezas=True, borde_corte=BORDE,
                                         etiqueta=ETIQUETA, referencia="alto",
                                         editables_cfg=c["editables_cfg"], editables_tamano=c["editables_tamano"],
                                         editables_color=c["editables_color"], editables_marca=c["editables_marca"],
                                         editables_sin_marca=c["editables_sin_marca"],
                                         objetos_agregados=c["objetos_agregados"], marcas_como_cruz=True)
            ents = [e for lst in por_tela.values() for e in lst]
            esperadas = sum(len(p["variante_piezas"]) for p in c["prendas"])
            ok(len(ents) == esperadas, f"{c['nombre']}: {len(ents)} piezas estampadas en {len(c['prendas'])} prendas")
            piezas = []
            for e in ents:
                b = e["base"]
                info = b["info"]
                nro = int(e["etiqueta"])
                piezas.append({"pieza": e["pieza"], "talle": e["talle"], "variante": e.get("variante"),
                               "nro": nro, "persona": c["prendas"][nro - 1]["personalizacion"],
                               "info": {k: v for k, v in info.items() if k in ("ancla", "pieza_idx", "idx_mesa", "mesa")},
                               "cont": b["cont"], "mesa_a": b["_mesa_a"],
                               "py": {"base_stream": b["base_stream"], "clip": b["clip"], "estampado": e["estampado"],
                                      "W": b["W"], "H": b["H"], "B": b["B"], "S": b["S"],
                                      "xo": sorted(b["fuentes_xo"].keys())}})
            fx_casos.append({"nombre": c["nombre"], "arte": c["arte"], "pers": pers,
                             "mapeo_arte": c["mapeo_arte"],
                             "mapeo_var": MP.mapeo_variantes_arte(c["arte"], reg, vorden),
                             "editables": MP.extraer_editables(c["arte"], con_thumb=False),
                             "editables_cfg": c["editables_cfg"], "editables_tamano": c["editables_tamano"],
                             "editables_color": c["editables_color"], "editables_marca": c["editables_marca"],
                             "editables_sin_marca": c["editables_sin_marca"],
                             "objetos_agregados": ({"dir": c["objetos_agregados"]["dir"],
                                                    "objetos": c["objetos_agregados"]["objetos"]}
                                                   if c["objetos_agregados"] else None),
                             "referencia": "alto", "marcas_como_cruz": True, "piezas": piezas})
            entradas.append(ents)
        # lo que el motor decidió redibujar aparte (por nombre) tiene que estar en la salida
        con_e = sum(1 for cs in fx_casos for p in cs["piezas"] if any(k.startswith("/E") for k in p["py"]["xo"]))
        con_oa = sum(1 for cs in fx_casos for p in cs["piezas"] if any(k.startswith("/OA") for k in p["py"]["xo"]))
        con_cruz = sum(1 for cs in fx_casos for p in cs["piezas"] if "0 0 0 1 K" in p["py"]["base_stream"])
        # jugador: v_a (movido + tamaño) en M y 2XL, v_c (recoloreado); la fila SIN variable cae a la
        # única variable configurada de cada cosa (`_cfg_var`): marca v_b + sin marca v_d → nada.
        # refwerrf: el escudo de 4 figuras con color por figura (M) y, por eso, también en el talle 8.
        ok(con_e >= 5, f"el motor redibujó editables aparte en {con_e} piezas")
        ok(con_oa >= 2 and con_cruz >= 1, f"objetos agregados en {con_oa} piezas · cruz de proceso en {con_cruz}")
        fixture = {"borde": BORDE, "etiqueta": ETIQUETA, "catalogo": catalogo, "alias": {}, "casos": fx_casos,
                   # para §4 (el hilo de trabajo real con el contexto rearmado)
                   "plantilla": pl, "registro": reg, "orden_var": vorden}
        fx = os.path.join(tmp, "fixture.json")
        with open(fx, "w", encoding="utf-8") as fh:
            json.dump(fixture, fh, ensure_ascii=False)

        print("\n2 · EL NAVEGADOR ARMA LAS MISMAS PIEZAS")
        pdfs = os.path.join(tmp, "pdfs")
        os.makedirs(pdfs)
        sal = os.path.join(tmp, "nav.json")
        r = subprocess.run(["node", "--max-old-space-size=4096", NODE, fx, sal, pdfs],
                           capture_output=True, text=True, encoding="utf-8", timeout=1800)
        ok(r.returncode == 0, "el motor del navegador terminó" + ("" if r.returncode == 0 else f": {r.stderr[-1200:]}"))
        if r.returncode != 0:
            return
        nav = json.load(open(sal, encoding="utf-8"))
        ok(nav.get("con_fuentes"), "con las tipografías (texto/curvas.js)")
        # los nombres de XObject los inventa pikepdf (`add_resource(prefix=…)`): /A…, /E…, /OA…
        _xo = re.compile(r"/(OA|A|E)[A-Za-z0-9_-]+ Do")
        _norm_xo = lambda t: _xo.sub(r"/\1 Do", t or "")
        total = ig_mesa = ig_base = ig_clip = ig_est = 0
        for cs, ncs in zip(fx_casos, nav["casos"]):
            for p, n in zip(cs["piezas"], ncs["piezas"]):
                total += 1
                ig_mesa += (p["mesa_a"] == n["mesa_a"])
                if _norm_xo(p["py"]["base_stream"]) == _norm_xo(n["base_stream"]):
                    ig_base += 1
                else:
                    _a, _b = _norm_xo(p["py"]["base_stream"]).splitlines(), _norm_xo(n["base_stream"]).splitlines()
                    for i, (x, y) in enumerate(zip(_a, _b)):
                        if x != y:
                            print(f"      base de {cs['nombre']}/{p['pieza']}/{p['talle']}/{p['variante']}, línea {i}: py «{x[:70]}» · nav «{y[:70]}»")
                            break
                    if len(_a) != len(_b):
                        print(f"      largo de la base de {cs['nombre']}/{p['pieza']}/{p['talle']}: py {len(_a)} líneas · nav {len(_b)}")
                ig_clip += p["py"]["clip"] == n["clip"]
                if nav.get("con_fuentes"):
                    if p["py"]["estampado"] == n["estampado"]:
                        ig_est += 1
                    else:
                        _a, _b = p["py"]["estampado"].splitlines(), (n["estampado"] or "").splitlines()
                        for i, (x, y) in enumerate(zip(_a, _b)):
                            if x != y:
                                print(f"      estampado de {cs['nombre']}/{p['pieza']}/{p['talle']}, línea {i}: py «{x[:70]}» · nav «{y[:70]}»")
                                break
                        if len(_a) != len(_b):
                            print(f"      largo del estampado de {cs['nombre']}/{p['pieza']}/{p['talle']}: py {len(_a)} líneas · nav {len(_b)}")
        ok(ig_mesa == total, f"la MESA del arte de cada pieza es la misma ({ig_mesa}/{total}: #rango, por variable, base)")
        ok(ig_base == total, f"🔴 la BASE es letra por letra la misma en {ig_base}/{total} piezas")
        ok(ig_clip == total, f"y el CLIP también ({ig_clip}/{total})")
        if nav.get("con_fuentes"):
            ok(ig_est == total, f"🔴 el ESTAMPADO (nombre, número, talle, etiqueta) es letra por letra el mismo ({ig_est}/{total})")

        print("\n3 · DIBUJADAS, SON LA MISMA PIEZA")
        peor = 0
        hechas = 0
        for cs, ncs, ents in zip(fx_casos, nav["casos"], entradas):
            for p, n, e in zip(cs["piezas"], ncs["piezas"], ents):
                b = e["base"]
                b["cstream"].write((b["base_stream"] + (e["estampado"] if nav.get("con_fuentes") else "")).encode())
                buf = io.BytesIO()
                b["out"].save(buf)
                dpy = fitz.open("pdf", buf.getvalue())
                djs = fitz.open(n["pdf"])
                z = 100 / 72
                ppy = dpy[0].get_pixmap(matrix=fitz.Matrix(z, z), alpha=False, colorspace=fitz.csRGB)
                pjs = djs[0].get_pixmap(matrix=fitz.Matrix(z, z), alpha=False, colorspace=fitz.csRGB)
                if (ppy.width, ppy.height) != (pjs.width, pjs.height):
                    ok(False, f"{cs['nombre']}/{p['pieza']}/{p['talle']}: tamaño {ppy.width}x{ppy.height} vs {pjs.width}x{pjs.height}")
                    continue
                distintos, fuera = _distintos(ppy.samples, pjs.samples, ppy.width, ppy.height)
                peor = max(peor, fuera)
                hechas += 1
                if fuera:
                    ok(False, f"{cs['nombre']}/{p['pieza']}/{p['talle']}/{p['variante']}: {fuera} píxeles distintos que no son borde ({distintos} en total)")
        ok(peor == 0 and hechas == total, f"las {hechas} piezas dibujadas a 100 dpi: 0 píxeles distintos fuera de bordes")

        print("\n4 · UN ARTE NUEVO CON EL VISOR YA MOSTRANDO EL ANTERIOR (el hilo de trabajo real)")
        # Reporte 2026-09-18 «tarda en cargar un arte»: el hilo rearmaba el contexto del arte pero
        # seguía usando las piezas armadas con el anterior (documentos ya destruidos) → «cannot find
        # page tree» / «invalid page number» → la pantalla le tiraba todos los talles al servidor.
        sal4 = os.path.join(tmp, "repetido.json")
        r4 = subprocess.run(["node", "--max-old-space-size=4096", NODE_REPETIDO, fx, sal4],
                            capture_output=True, text=True, encoding="utf-8", timeout=900)
        ok(r4.returncode == 0, "el hilo de trabajo terminó" + ("" if r4.returncode == 0 else f": {r4.stderr[-1200:]}"))
        if r4.returncode == 0:
            rep = json.load(open(sal4, encoding="utf-8"))
            for p in rep["pasos"]:
                ok(p["ok"], f"{p['nombre']} ({rep.get('pieza')})" + ("" if p["ok"] else f": {p.get('error')}"))
            ok(rep.get("iguales"), "🔴 y sale IGUAL las tres veces (nada de la base vieja se cuela)")
    finally:
        MP.cerrar_abiertos() if hasattr(MP, "cerrar_abiertos") else None
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    for req in (os.path.join(AQUI, "entrada", PID, "plantilla.ai"),
                os.path.join(AQUI, "datos", "productos", PID, "piezas.json")):
        if not os.path.exists(req):
            print(f"  (falta {req}: se saltea)")
            sys.exit(0)
    main()
    print()
    if FALLOS:
        print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
        for f in FALLOS:
            print("   · " + f)
        sys.exit(1)
    print("✅ CONTRATO VERDE — el navegador arma cada pieza del camino A igual que el motor")
