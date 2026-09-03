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
        iguales = 0
        for tl in (talles[0], TALLE, talles[-1]):
            src = pikepdf.open(COPIA)
            pg = src.pages[MESA - 1]
            MR.aislar_capa(src, pg, tl, podar=True)
            a = pg.Contents.read_bytes()
            b = d.pages[talles.index(tl)].Contents.read_bytes()
            iguales += a == b
            src.close()
        ok(iguales == 3, "contenido idéntico a `aislar_capa(podar=True)` en 3 talles")
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
        ref = os.path.join(tmp, "ref.pdf")
        src.save(ref)
        src.close()
        p1 = render(ref, MESA - 1)
        p2 = render(fp, talles.index(TALLE))
        mismo = (p1.width, p1.height) == (p2.width, p2.height) and p1.samples == p2.samples
        dif = None if mismo else sum(1 for i in range(0, len(p1.samples), 3) if p1.samples[i:i+3] != p2.samples[i:i+3])
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
        n_arch = len(os.listdir(os.path.join(tmp, PD.DESPLEGADO)))
        ok(n_arch == 2 * n_mesas, f"alta con 4 procesos: {t_p:.0f}s · {n_arch} archivos en desplegado/")
        ok(alta_p["registro"] and alta_p["visor"] and not alta_p["problemas"],
           f"{len(alta_p['registro'])} piezas · visor de {len(alta_p['visor'])} talles · sin problemas")
        # en serie, sólo la mesa 1 (el molde entero en serie son minutos): los contornos que dejó el
        # proceso hijo tienen que ser los mismos que da este proceso
        par = json.load(open(os.path.join(tmp, PD.DESPLEGADO, f"m{MESA}.json"), encoding="utf-8"))["talles"]
        conts_serie = PD.desplegar_mesa(COPIA, MESA, talles)
        ok(json.dumps(conts_serie) == json.dumps(par), "la mesa 1 en serie da los mismos contornos que en paralelo")
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
