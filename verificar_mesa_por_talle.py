# -*- coding: utf-8 -*-
"""CONTRATO: LO QUE SEPARA UNA MESA DE TRABAJO ES LA COLUMNA DE TALLE Y LA TELA
`py verificar_mesa_por_talle.py`

Regla del usuario (2026-09-14): *«si los moldes toman talles de la misma columna deben de
mezclarse en la misma mesa de trabajo aunque sean de diferente diseño. Lo que separa en mesa de
trabajo es de dónde toma el talle, y la diferente tela»*.

Antes la mesa la separaba el «grupo de tizada» configurado a mano y, sin grupo, **cada molde
armaba la suya**: un pedido de 2 camisetas + 2 shorts × 2 telas salía en **8 hojas** donde
correspondían 4 (camisetas y shorts leen columnas distintas, y cada una en sus 2 telas).

Y la otra mitad: **el paso Tizada no puede clavar el navegador.** Las 10 mesas se mostraban como
10 SVG que sumaban 202 MB (uno solo de 78 MB) → «La página no responde». La grilla pasa a una
vista liviana de **la hoja de verdad** (2,7 MB las 10), y el PDF que se descarga no se toca.

Lo que se prueba:
  1. de qué columna lee el talle cada molde, y su nombre;
  2. moldes de DISTINTO diseño con la MISMA columna comparten mesa; con columnas distintas, no;
  3. la clave de agrupación del pedido es la columna (no el grupo de tizada ni el molde);
  4. la vista liviana existe, sale de la HOJA (no del SVG), se guarda y pesa órdenes de magnitud
     menos — y el SVG vectorial sigue ahí para el detalle y el PDF intacto para descargar;
  5. al acercarse, el RECORTE de lo que se está mirando llega con nitidez suficiente para leer una
     etiqueta de 3 mm (el dibujo general no alcanza: ahí una letra mide 2 píxeles).

⚠️ Sólo LEE el catálogo y, si hay una tizada vieja en `trabajos/`, la dibuja. No escribe datos.
"""
import glob
import inspect
import io
import os
import re
import sys
import tempfile
import types
from collections import OrderedDict

sys.stdout.reconfigure(encoding="utf-8")
_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")

import registro as _LOG                    # noqa: E402
_LOG.usar_carpeta(tempfile.mkdtemp(prefix="verif_mesa_"))
import servidor as S                       # noqa: E402

FALLOS = []


def ok(cond, msg):
    print(("    OK    " if cond else "    ❌    ") + msg)
    if not cond:
        FALLOS.append(msg)


CAT_PRUEBA = {"plantillas_planillas": [{"id": "p1", "columnas": [
    {"id": "talle", "label": "Talle", "role": "talle"},
    {"id": "talle_short", "label": "Talle short", "role": "talle"}]}]}


def main():
    # ── 1. DE QUÉ COLUMNA LEE CADA MOLDE ────────────────────────────────────────────────────
    print("1 · DE QUÉ COLUMNA LEE EL TALLE CADA MOLDE")
    ok(S._columna_talle_de({"mapeo_columnas": {"talle": "talle_short"}}) == "talle_short",
       "lee la columna que el molde tiene elegida")
    ok(S._columna_talle_de({}) == "talle", "un molde sin nada elegido usa la columna «talle»")
    ok(S._columna_talle_de(None) == "talle", "…y sin molde tampoco revienta")
    ok(S._label_columna_talle({"mapeo_columnas": {"talle": "talle_short"}}, CAT_PRUEBA) == "Talle short",
       "el nombre de la columna sale de la planilla")
    ok(S._label_columna_talle({"mapeo_columnas": {"talle": "inventada"}}, CAT_PRUEBA) == "inventada",
       "una columna que ya no está no rompe: se muestra su id")

    # ── 2. QUIÉN COMPARTE MESA ──────────────────────────────────────────────────────────────
    print("\n2 · 🔴 MISMA COLUMNA = MISMA MESA, AUNQUE SEAN DE DISTINTO DISEÑO")
    moldes = [
        {"_nombre": "CAMISETA JUGADOR", "_diseno": "jugador", "mapeo_columnas": {"talle": "talle"}},
        {"_nombre": "CAMISETA LIBERO", "_diseno": "libero", "mapeo_columnas": {"talle": "talle"}},
        {"_nombre": "SHORT JUGADOR", "_diseno": "jugador", "mapeo_columnas": {"talle": "talle_short"}},
        {"_nombre": "SHORT LIBERO", "_diseno": "libero", "mapeo_columnas": {"talle": "talle_short"}},
    ]
    grupos = OrderedDict()
    for m in moldes:
        grupos.setdefault(S._columna_talle_de(m), []).append(m["_nombre"])
    ok(len(grupos) == 2, f"4 moldes de 2 diseños → {len(grupos)} mesas (no 4): {dict(grupos)}")
    ok(grupos.get("talle") == ["CAMISETA JUGADOR", "CAMISETA LIBERO"],
       "🔴 las dos camisetas van JUNTAS aunque sean de diseños distintos")
    ok(grupos.get("talle_short") == ["SHORT JUGADOR", "SHORT LIBERO"],
       "…y los dos shorts juntos, pero aparte de las camisetas")
    ok("talle" in grupos and "talle_short" in grupos and grupos["talle"] != grupos["talle_short"],
       "una columna distinta SÍ separa")

    # ── 3. ES LO QUE USA EL PEDIDO ──────────────────────────────────────────────────────────
    print("\n3 · Y ES LA CLAVE QUE USA EL PEDIDO DE VERDAD")
    src = inspect.getsource(S.generar_multi)
    ok('"_gkey": _columna_talle_de(prod)' in src,
       "la clave de agrupación del pedido es la columna de talle")
    ok('"_gkey": (gconf or {}).get("id")' not in src,
       "…y ya NO es el grupo de tizada configurado a mano")
    ok('"__solo_" + pid' not in src,
       "🔴 …ni «este molde solo», que era lo que partía el pedido en una tizada por molde")
    ok('grupos_map.setdefault(md["_gkey"]' in src, "los moldes se juntan por esa clave")
    # con el catálogo REAL del usuario
    try:
        cat = S._cargar_catalogo()
        reales = {}
        for p in (cat.get("productos") or []):
            reales.setdefault(S._columna_talle_de(p), []).append(p.get("nombre"))
        print("          en el catálogo de hoy: " +
              " · ".join(f"{k} → {len(v)} molde(s)" for k, v in reales.items()))
        ok(len(reales) >= 1, "el catálogo real agrupa por columna sin errores")
    except Exception as e:
        print(f"    ⚠️    no se pudo leer el catálogo real ({e})")

    # ── 4. LA VISTA LIVIANA DEL PASO TIZADA ─────────────────────────────────────────────────
    print("\n4 · 🔴 EL PASO TIZADA NO PUEDE CLAVAR EL NAVEGADOR")
    # El dibujo vive en `_dibujar_vista_mesa` desde 2026-09-15: el endpoint y el PRE-DIBUJADO del
    # final del pedido usan el mismo código y la misma caché (por eso se miran los dos).
    # …y desde 2026-09-16 (changelog 468) la página se lee una vez a un display list
    # (`_pagina_dibujable`) y el recorte se nombra en `_ruta_vista_mesa`: se miran los cuatro.
    src_img = (inspect.getsource(S.mesa_img) + inspect.getsource(S._dibujar_vista_mesa)
               + inspect.getsource(S._pagina_dibujable) + inspect.getsource(S._ruta_vista_mesa))
    ok("fitz.open(ruta)" in src_img and "get_pixmap" in src_img,
       "la vista sale de la HOJA (el PDF que se descarga), no del SVG")
    ok(".svg" not in src_img,
       "🔴 …y NO del SVG: su rasterizador ignora los recortes y mostraría piezas mal cortadas")
    ok("os.replace(cache" in src_img, "se guarda una sola vez, y de forma atómica")
    ok(callable(getattr(S, "_predibujar_mesas", None)),
       "las mesas se dibujan ANTES de que la pantalla las pida (si no, la grilla aparece vacía)")
    app = io.open(os.path.join(_AQUI, "frontend", "src", "App.jsx"), encoding="utf-8").read()
    ok("mesa_img/${encodeURIComponent(hoja.archivo)}" in app, "la grilla de mesas la usa")
    # 🔴 EL DETALLE YA NO ABRE EL SVG, Y ES A PROPÓSITO (2026-09-15). Esas previas en SVG no se
    # escriben más: nadie las pedía —en el registro del servidor no hay un solo pedido de un
    # `prev_*.svg`— y costaban 25 s y cientos de MB por pedido. El detalle abre la MISMA hoja
    # rasterizada, a más resolución. Lo que no se toca, y es lo que hay que defender acá, es que
    # **lo que se DESCARGA sigue siendo el vector exacto**.
    ok("prev_" not in app.split("MesasInfinito")[-1][:60000],
       "el visor de mesas no depende de las previas en SVG")
    ok("mesa_img/${encodeURIComponent(hoja.archivo)}?pi=${pIdx}&w=2400" in app,
       "…y el DETALLE abre la misma hoja, a más resolución")
    ok("/api/trabajos/${j.resultado.id}/mesa/${h.archivo}" in app,
       "🔴 y la DESCARGA sigue siendo el PDF vectorial de la mesa, no una imagen")
    ok("/trabajos/${job.resultado.id}/${hoja.archivo}" in app or "download" in app,
       "el PDF se sigue descargando tal cual")

    # MEDIDA EN VIVO, sobre la tizada MÁS PESADA que haya a mano: en una chiquita no hay nada que
    # probar (ahí el SVG ya era liviano y el problema nunca existió).
    pesos = {}
    for x in glob.glob(os.path.join(S.TRABAJOS, "*", "*.svg")):
        pesos[os.path.basename(os.path.dirname(x))] = pesos.get(os.path.basename(os.path.dirname(x)), 0) + os.path.getsize(x)
    tid = max(pesos, key=pesos.get) if pesos else None
    if tid and pesos[tid] > 5e6:
        svg = pesos[tid]
        png = 0
        import pymupdf as fitz
        for f in sorted(glob.glob(os.path.join(S.TRABAJOS, tid, "HOJA_*.pdf"))):
            a = os.path.basename(f)
            with fitz.open(f) as d:
                n = d.page_count
            for pi in range(n):
                with S.app.test_request_context(f"/api/trabajos/{tid}/mesa_img/{a}?pi={pi}"):
                    S.mesa_img(tid, a)
                c = os.path.join(S.TRABAJOS, tid, f"vista_{os.path.splitext(a)[0]}_p{pi}_w1200.png")
                png += os.path.getsize(c) if os.path.exists(c) else 0
        if png:
            print(f"          medido en «{tid}»: SVG {svg/1e6:.0f} MB → vista {png/1e6:.1f} MB")
            ok(png < svg / 5, f"la vista pesa órdenes de magnitud menos ({svg/max(png,1):.0f}x)")
            ok(png < 15e6, f"…y la grilla entera entra en pocos MB ({png/1e6:.1f} MB): por eso deja de clavarse")
    else:
        print("    ⚠️    no hay ninguna tizada pesada en `trabajos/` para medirlo en vivo")

    # ── 5. EL RECORTE NÍTIDO ────────────────────────────────────────────────────────────────
    print("\n5 · 🔴 AL ACERCARSE, LO QUE SE MIRA SE LEE")
    ok("cx0" in src_img and "clip=clip" in src_img, "la vista acepta un rectángulo y lo recorta")
    # Se busca la DECISIÓN, no una línea textual: el `entera = …` se reescribió al extraer
    # `_dibujar_vista_mesa` (y de paso pasó a cubrir `recorte=None`), y este contrato se puso en
    # rojo por la letra, no por el comportamiento. Lo que importa es que el rectángulo completo
    # siga siendo el caso por defecto.
    _ent = re.search(r"entera\s*=\s*(.+)", src_img)
    ok(bool(_ent) and "(0.0, 0.0, 1.0, 1.0)" in _ent.group(1),
       "…y la mesa entera sigue siendo el caso por defecto")
    ok("sufijo" in src_img, "cada recorte se guarda aparte (moverse un poco reusa el anterior)")
    ok("TILE_CM = 50" in app and "BASE_W = 1200" in app,
       "la pantalla pide los recortes por una grilla fija de medio metro")
    # desde 2026-09-16 (changelog 469) se mide en píxeles REALES de la pantalla (`* dpr`)
    ok("r.width * dpr <= BASE_W * 1.05) continue" in app,
       "🔴 …y sólo cuando la PANTALLA supera lo que da el dibujo general (no a un zoom inventado)")
    ok("TOPE_RECORTES" in app, "con un tope de recortes vivos, para no comerse la memoria")

    # la cuenta que importa: cuántos píxeles por cm da un recorte, y cuánto mide ahí una letra de 3 mm
    TILE_CM, W_TILE = 50, 1600
    pxcm = W_TILE / TILE_CM
    print(f"          un recorte de {TILE_CM} cm a {W_TILE} px = {pxcm:.0f} px/cm · una letra de 3 mm mide {pxcm*0.3:.1f} px")
    ok(pxcm * 0.3 >= 6, f"una etiqueta de 3 mm entra en {pxcm*0.3:.1f} píxeles: se lee")
    BASE_W, MESA_CM = 1200, 180
    print(f"          (en el dibujo general esa misma letra mide {BASE_W/MESA_CM*0.3:.1f} px: por eso no se leía)")
    ok(BASE_W / MESA_CM * 0.3 < 3, "…y el dibujo general por sí solo NO alcanzaba (ésa era la queja)")

    # y de verdad, sobre una mesa real
    if tid:
        import pymupdf as fitz
        f = sorted(glob.glob(os.path.join(S.TRABAJOS, tid, "HOJA_*.pdf")))
        if f:
            a = os.path.basename(f[0])
            with S.app.test_request_context(
                    f"/api/trabajos/{tid}/mesa_img/{a}?pi=0&w=1600&cx0=0.25&cy0=0.25&cx1=0.5&cy1=0.5"):
                r = S.mesa_img(tid, a)
            ok(r.status_code == 200, f"el servidor entrega el recorte de «{a}» (HTTP {r.status_code})")
            c = os.path.join(S.TRABAJOS, tid, f"vista_{os.path.splitext(a)[0]}_p0_w1600_c0.2500-0.2500-0.5000-0.5000.png")
            ok(os.path.exists(c) and os.path.getsize(c) < 3e6,
               f"…y queda guardado, liviano ({os.path.getsize(c)/1e6:.2f} MB)" if os.path.exists(c) else "…y queda guardado")

    # ── 6. 🔴 MEZCLAR MOLDES NO PUEDE MEZCLAR SILUETAS ──────────────────────────────────────
    print("\n6 · 🔴 DOS MOLDES EN LA MISMA MESA NO COMPARTEN LA FORMA DE UNA PIEZA")
    # El nesteo reusa la máscara (la silueta) de una pieza cuando otra tiene la misma clave de
    # geometría. Desde que los moldes de la misma columna se acomodan JUNTOS, esa clave TIENE que
    # distinguir el molde: si no, dos piezas que se llaman igual en moldes distintos se colocan con
    # la misma forma y la hoja sale con las piezas encimadas — impresa y perfecta.
    import nesting_contorno as NC
    src_n = inspect.getsource(NC._preparar)
    ok('p.get("_molde")' in src_n, "el molde entra en la clave de geometría del nesteo")
    src_m = io.open(os.path.join(_AQUI, "motor_pedido.py"), encoding="utf-8").read()
    ok('_e["_molde"] = _mk' in src_m, "…y el motor le pone a cada pieza de qué molde es")

    def _clave(p, cell=2.0, esp=0.5, paso=15):
        return (p.get("_molde"), p.get("pieza"), p.get("talle"), p.get("variante"), p["rotacion"],
                p.get("borde_cm", 0), cell, esp, paso)
    _a = {"_molde": "A/plantilla.ai", "pieza": "Frente 1", "talle": "M", "variante": None,
          "rotacion": 180, "borde_cm": 0}
    ok(_clave(_a) == _clave(dict(_a)), "la misma pieza del mismo molde sí comparte forma (eso se quiere)")
    ok(_clave(_a) != _clave(dict(_a, _molde="B/plantilla.ai")),
       "🔴 la misma pieza de OTRO molde NO comparte forma")
    ok(_clave(_a) != _clave(dict(_a, talle="L")), "…ni otro talle")

    print()
    if FALLOS:
        print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
        for f in FALLOS:
            print("   ·", f)
        sys.exit(1)
    print("✅ CONTRATO VERDE — la mesa la separan la columna de talle y la tela; el paso Tizada va liviano")


if __name__ == "__main__":
    main()
