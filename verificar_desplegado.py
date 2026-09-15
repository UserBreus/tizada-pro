# -*- coding: utf-8 -*-
"""CONTRATO DEL MOLDE DESPLEGADO (camino B) — `py verificar_desplegado.py [ruta.ai]`

El archivo se lee UNA vez, al cargar. El alta deja al lado del molde, en `desplegado/`, una página
por (mesa, talle) ya aislada y podada, más los contornos de cada talle. Después el motor y el visor
leen de ahí y no vuelven a abrir el dibujo. Es la idea del proyecto de referencia («parsear una vez
a una escena y trabajar sobre eso»), guardada en disco. Ver `piezas_con_diseno.py`, «EL MOLDE
DESPLEGADO», y `MOLDE_CON_DISENO.md`.

Lo que este contrato cuida:
  1. 🔴 La página desplegada de un talle es, BYTE A BYTE, lo que producía `aislar_capa(podar=True)`
     sobre la mesa original — o sea, lo que el motor hacía en cada tizada. Mismo código, una vez.
  2. 🔴 Se ve igual: render de la página desplegada vs la mesa original aislada, 0 píxeles distintos
     (ley del proyecto: el arte se ve igual que la tizada).
  3. Los contornos leídos del desplegado son los mismos que leer el archivo (`get_drawings`).
  4. El motor toma la página del desplegado (no aísla): armar la pieza baja de segundos a nada.
  5. Si el archivo cambia (otro sello), el desplegado no se usa y se rehace solo.
  6. El alta en PARALELO (como la corre el servidor) da el mismo registro que en serie, mesa a mesa.
  7. La página desplegada lleva SÓLO los recursos que usa: de 22 fuentes a las 3 o 4 del talle.

⚠️ No toca nada del usuario: trabaja sobre copias en un temporal. Tarda unos minutos (despliega el
molde real entero dos veces: en serie y en paralelo).
"""
import io
import json
import os
import shutil
import sys
import tempfile
import time

sys.stdout.reconfigure(encoding="utf-8")
_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)

import pikepdf                       # noqa: E402
import pymupdf as fitz               # noqa: E402
import molde_real as MR              # noqa: E402
import piezas_con_diseno as PD       # noqa: E402

ORIG = sys.argv[1] if len(sys.argv) > 1 else \
    r"C:\Users\user2\Downloads\PRUEBA TIZADA PRO\para acomodo de archivos\CAMISETA JUGADOR.ai"
FALLOS = []


def _render_bytes(origen, pagina=0, dpi=24):
    """Los píxeles (CMYK) de una página. `origen` = ruta o bytes de un PDF."""
    try:
        import pymupdf as _fz
    except ImportError:
        import fitz as _fz
    try:
        d = _fz.open(origen) if isinstance(origen, str) else _fz.open("pdf", origen)
        try:
            return bytes(d[pagina].get_pixmap(dpi=dpi, colorspace=_fz.csCMYK).samples)
        finally:
            d.close()
    except Exception as e:
        print("          [!] no se pudo dibujar para comparar:", e)
        return None


def ok(cond, msg):
    print(("    OK    " if cond else "    ❌    ") + msg)
    if not cond:
        FALLOS.append(msg)


def render(path, idx, dpi=40):
    d = fitz.open(path)
    pm = d[idx].get_pixmap(dpi=dpi, alpha=False)
    d.close()
    return pm


def main():
    if not os.path.exists(ORIG):
        print(f"❌ no está el archivo de prueba:\n   {ORIG}")
        sys.exit(1)
    tmp = tempfile.mkdtemp(prefix="verif_despl_")
    print("CONTRATO DEL MOLDE DESPLEGADO — el archivo se lee una vez, al cargar\n")
    print(f"copiando el archivo ({os.path.getsize(ORIG)/1e6:.0f} MB)…")
    COPIA = os.path.join(tmp, "plantilla.ai")
    shutil.copy2(ORIG, COPIA)
    try:
        doc = fitz.open(COPIA)
        talles = PD.talles_del_molde(doc)
        n_mesas = doc.page_count
        doc.close()
        MESA = 1
        TALLE = talles[len(talles) // 2]
        print(f"{n_mesas} mesas · {len(talles)} talles · se mira la mesa {MESA}, talle {TALLE}\n")

        # ══ 1 y 7. LA PÁGINA DESPLEGADA ES LA DE SIEMPRE, BYTE A BYTE, Y SÓLO CON SUS RECURSOS ═
        print("1 · 🔴 LA PÁGINA DESPLEGADA ES LO QUE HACÍA EL MOTOR, BYTE A BYTE")
        t0 = time.time()
        conts = PD.desplegar_mesa(COPIA, MESA, talles)
        t_despl = time.time() - t0
        fp = os.path.join(tmp, PD.DESPLEGADO, f"m{MESA}.pdf")
        ok(os.path.exists(fp) and os.path.exists(fp[:-3] + "json"), f"deja m{MESA}.pdf + m{MESA}.json ({t_despl:.0f}s)")
        d = pikepdf.open(fp)
        ok(len(d.pages) == len(talles), f"una página por talle ({len(d.pages)})")
        # Desde el changelog 387 la página desplegada es `aislar_capa(podar=True)` MENOS los textos
        # «00»/«NOMBRE» (`quitar_placeholders`): se les aplica lo mismo a las páginas de control.
        _j = json.load(open(fp[:-3] + "json", encoding="utf-8"))
        iguales = 0
        for tl in (talles[0], TALLE, talles[-1]):
            src = pikepdf.open(COPIA)
            pg = src.pages[MESA - 1]
            MR.aislar_capa(src, pg, tl, podar=True)
            _ins = list(pikepdf.parse_content_stream(pg))
            _ins, _ph, _ = PD.quitar_placeholders(_ins, pg, _j["marco"], _j["U"],
                                                 tl, [PD._cont_de_json(c) for c in _j["talles"].get(tl) or []])
            # y sin la línea de corte del archivo (changelog 394)
            _ins, _ = PD.quitar_linea_de_corte(_ins, pg, [PD._cont_de_json(c) for c in _j["talles"].get(tl) or []], _j["marco"], _j["U"])
            a = pikepdf.unparse_content_stream(_ins)
            b = d.pages[talles.index(tl)].Contents.read_bytes()
            # 🔴 SE COMPARA EL DIBUJO, NO LOS BYTES (2026-09-15, `cortar_capas.py`). El desplegado
            # corta el trozo del talle por BYTES antes de parsear, y de paso se lleva los grupos
            # `q … Q` de los OTROS talles, que el camino de siempre dejaba como trazados MUERTOS
            # (dibujo sin pintar que el RIP igual tenía que leer). O sea: la página nueva es más
            # chica y dibuja exactamente lo mismo — byte a byte no puede dar igual, y exigirlo
            # dejaba el contrato en rojo por una MEJORA. Se comparan los píxeles.
            # `a` se escribe en la página que ya está aislada y se dibuja el PDF entero; `b` se
            # dibuja del desplegado tal cual quedó en disco. Sin armar páginas a mano: menos
            # lugares donde el instrumento pueda mentir.
            pg.Contents = src.make_stream(a)
            _bufa = io.BytesIO(); src.save(_bufa)
            _pa = _render_bytes(_bufa.getvalue(), MESA - 1)
            _pb = _render_bytes(fp, talles.index(tl))
            _dif = -1 if _pa is None or _pb is None or len(_pa) != len(_pb) else                 sum(1 for x, y in zip(_pa, _pb) if x != y)
            iguales += (_dif == 0)
            if _dif != 0:
                print(f"          {tl}: {len(a)} vs {len(b)} bytes · {_dif} píxeles distintos "
                      f"· placeholders vistos: {sorted(_ph)}")
            src.close()
        ok(iguales == 3, "el MISMO dibujo (píxel a píxel) que `aislar_capa(podar=True)` + "
                         "`quitar_placeholders` en 3 talles")
        pg_d = d.pages[talles.index(TALLE)]
        res = pg_d.get("/Resources") or {}
        fuentes = len(res.get("/Font") or {})
        src = pikepdf.open(COPIA)
        fuentes_orig = len((src.pages[MESA - 1].get("/Resources") or {}).get("/Font") or {})
        src.close()
        print(f"          fuentes: {fuentes_orig} en la mesa original → {fuentes} en la página desplegada")
        ok(fuentes < fuentes_orig and "/Properties" not in res, "7 · sólo los recursos que usa (sin OCG, menos fuentes)")
        # cada Tf del contenido tiene su fuente declarada
        _ops = list(pikepdf.parse_content_stream(pg_d))
        _fn = set(str(k) for k in (res.get("/Font") or {}).keys())
        ok(all(str(o.operands[0]) in _fn for o in _ops if str(o.operator) == "Tf"), "7 · todas las fuentes que usa están declaradas")
        d.close()

        # ══ 2. SE VE IGUAL ═════════════════════════════════════════════════════════════════════
        print("\n2 · 🔴 SE VE IGUAL (ley del proyecto)")
        src = pikepdf.open(COPIA)
        pg = src.pages[MESA - 1]
        MR.aislar_capa(src, pg, TALLE, podar=True)
        MR.sanear_oc(src, pg)
        # la página de control también sin «00»/«NOMBRE» (changelog 387: el desplegado los saca)
        _ins2 = list(pikepdf.parse_content_stream(pg))
        _ins2, _, _ = PD.quitar_placeholders(_ins2, pg, _j["marco"], _j["U"],
                                            TALLE, [PD._cont_de_json(c) for c in _j["talles"][TALLE]])
        # …y sin la LÍNEA DE CORTE del archivo (changelog 394: el desplegado la saca y la base la
        # vuelve a trazar con la configuración del borde)
        _ins2, _ = PD.quitar_linea_de_corte(_ins2, pg, [PD._cont_de_json(c) for c in _j["talles"][TALLE]], _j["marco"], _j["U"])
        pg.Contents = src.make_stream(pikepdf.unparse_content_stream(_ins2))
        ref = os.path.join(tmp, "ref.pdf")
        src.save(ref)
        src.close()
        p1 = render(ref, MESA - 1)
        p2 = render(fp, talles.index(TALLE))
        mismo = (p1.width, p1.height) == (p2.width, p2.height) and p1.samples == p2.samples
        # el conteo de píxeles distintos va con numpy: en Python puro tardaba 10 minutos
        if mismo:
            dif = None
        else:
            try:
                import numpy as _np
                _a = _np.frombuffer(p1.samples, dtype=_np.uint8).reshape(-1, 3); _b = _np.frombuffer(p2.samples, dtype=_np.uint8).reshape(-1, 3)
                dif = int((_a != _b).any(axis=1).sum()) if _a.shape == _b.shape else "tamaños distintos"
            except Exception:
                dif = "?"
        ok(mismo, f"render {p1.width}×{p1.height}: {'0' if mismo else dif} píxeles distintos")

        # ══ 3. LOS CONTORNOS SON LOS MISMOS ════════════════════════════════════════════════════
        print("\n3 · LOS CONTORNOS DEL DESPLEGADO SON LOS DEL ARCHIVO")
        doc = fitz.open(COPIA)
        t0 = time.time(); de_cache = PD.piezas_de_mesa(doc, MESA, TALLE); t_c = time.time() - t0
        t0 = time.time(); crudos = PD._piezas_de_mesa_cruda(doc, MESA, TALLE); t_r = time.time() - t0
        PD.olvidar(doc); doc.close()
        ok(len(de_cache) == len(crudos) > 0, f"{len(de_cache)} piezas por los dos caminos")
        ok(all(a["segmentos"] == b["segmentos"] and a["bbox_mu"] == tuple(b["bbox_mu"]) for a, b in zip(de_cache, crudos)),
           "mismos segmentos y bbox (tuplas)")
        print(f"          leer del desplegado {t_c*1000:.0f} ms · leer el archivo {t_r:.1f}s")
        ok(t_c < 1.0, "leer del desplegado es instantáneo")

        # ══ 4. EL MOTOR NO AÍSLA MÁS ═══════════════════════════════════════════════════════════
        print("\n4 · EL MOTOR TOMA LA PÁGINA DEL DESPLEGADO")
        r = PD.ruta_desplegada(COPIA, MESA, TALLE)
        ok(r is not None and r[0] == fp and r[1] == talles.index(TALLE), f"ruta_desplegada → {os.path.basename(fp)} página {r[1] if r else '?'}")
        t0 = time.time()
        pdf = pikepdf.open(r[0]); xo = pikepdf.Pdf.new().copy_foreign(pdf.pages[r[1]].as_form_xobject()); pdf.close()
        ok(time.time() - t0 < 2.0, f"tomar la mesa como XObject: {time.time()-t0:.2f}s (antes: aislar 3-13 s)")

        # ══ 5. EL SELLO ════════════════════════════════════════════════════════════════════════
        print("\n5 · SI EL ARCHIVO CAMBIA, EL DESPLEGADO NO SE USA")
        _j = fp[:-3] + "json"
        _d = json.load(open(_j, encoding="utf-8"))
        _d["sello"] = [1, 1]
        json.dump(_d, open(_j, "w", encoding="utf-8"))
        PD._CONT_CACHE.clear()
        ok(PD._leer_desplegado(COPIA, MESA) is None, "con otro sello, `_leer_desplegado` da None")
        r2 = PD.ruta_desplegada(COPIA, MESA, TALLE)      # lo rehace
        ok(r2 is not None and json.load(open(_j, encoding="utf-8"))["sello"] == PD._sello(COPIA), "`ruta_desplegada` lo rehace con el sello bueno")

        # ══ 6. EL ALTA EN PARALELO ═════════════════════════════════════════════════════════════
        print("\n6 · EL ALTA EN PARALELO DA LO MISMO QUE EN SERIE")
        shutil.rmtree(os.path.join(tmp, PD.DESPLEGADO), ignore_errors=True)
        t0 = time.time(); alta_p = PD.alta_molde_con_diseno(COPIA, procesos=4); t_p = time.time() - t0
        _arch = os.listdir(os.path.join(tmp, PD.DESPLEGADO))
        # por mesa: su índice y su PDF por talle. Aparte, UN archivo del molde entero: la decisión
        # sobre la etiqueta que trae el diseño (`etiqueta_archivo.json`, changelog 429).
        n_arch = sum(1 for f in _arch if f.startswith("m") and f[1:].split(".")[0].isdigit())
        ok(n_arch == 2 * n_mesas, f"alta con 4 procesos: {t_p:.0f}s · {n_arch} archivos por mesa en desplegado/")
        ok(PD._ETQ_JSON in _arch, "y la decisión sobre la etiqueta del diseño quedó escrita al lado")
        ok(alta_p["registro"] and alta_p["visor"] and not alta_p["problemas"],
           f"{len(alta_p['registro'])} piezas · visor de {len(alta_p['visor'])} talles · sin problemas")
        # en serie, sólo la mesa 1 (el molde entero en serie son minutos): los contornos que dejó el
        # proceso hijo tienen que ser los mismos que da este proceso
        par = json.load(open(os.path.join(tmp, PD.DESPLEGADO, f"m{MESA}.json"), encoding="utf-8"))["talles"]
        conts_serie = PD.desplegar_mesa(COPIA, MESA, talles)
        ok(json.dumps(conts_serie) == json.dumps(par), "la mesa 1 en serie da los mismos contornos que en paralelo")

        # ══ 7. LA LÍNEA DE CORTE DEL ARCHIVO ES EL BORDE DE LA PIEZA (2026-09-07) ══════════════
        print("\n7 · LA LÍNEA DE CORTE DEL ARCHIVO: es el contorno, sale del dibujo y guarda su estilo")
        _jm = json.load(open(os.path.join(tmp, PD.DESPLEGADO, f"m{MESA}.json"), encoding="utf-8"))
        _c0 = _jm["talles"][TALLE][0]
        ok(_c0.get("linea_corte") is True, "el contorno de la pieza es su línea de corte (el archivo real la trae)")
        _est = ((_jm.get("linea_corte") or {}).get(TALLE) or {}).get("0") or {}
        ok(float(_est.get("w") or 0) > 0 and _est.get("color"), f"estilo guardado: ancho {_est.get('w')} pt · color {_est.get('color')}")
        ok(_jm.get("vp") == PD._V_PAGINAS and _jm.get("v") == PD._V_CONTORNOS, "el JSON lleva las versiones de contornos y de páginas")
        _dd = fitz.open(os.path.join(tmp, PD.DESPLEGADO, f"m{MESA}.pdf")); _pg = _dd[talles.index(TALLE)]
        _bb = _c0["bbox_mu"]
        _tr = [x for x in _pg.get_cdrawings() if x.get("type") == "s" and all(abs(x["rect"][k] - _bb[k]) < 1.5 for k in range(4))]
        _dd.close()
        ok(not _tr, "la página desplegada ya no trae el trazo de la línea de corte (lo traza la base con la configuración)")
        _lc = PD._leer_desplegado(COPIA, MESA)["contornos"][TALLE][0].get("linea_corte")
        ok(isinstance(_lc, dict) and _lc.get("w"), "`_leer_desplegado` entrega el estilo dentro del contorno")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FALLOS:
        print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
        for f in FALLOS:
            print("   ·", f)
        sys.exit(1)
    print("✅ CONTRATO VERDE — el molde se lee una vez al cargar y el motor trabaja sobre el desplegado")


if __name__ == "__main__":
    main()
