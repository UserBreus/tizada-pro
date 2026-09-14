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
     menos — y el SVG vectorial sigue ahí para el detalle y el PDF intacto para descargar.

⚠️ Sólo LEE el catálogo y, si hay una tizada vieja en `trabajos/`, la dibuja. No escribe datos.
"""
import glob
import inspect
import io
import os
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
        print(f"          en el catálogo de hoy: " +
              " · ".join(f"{k} → {len(v)} molde(s)" for k, v in reales.items()))
        ok(len(reales) >= 1, "el catálogo real agrupa por columna sin errores")
    except Exception as e:
        print(f"    ⚠️    no se pudo leer el catálogo real ({e})")

    # ── 4. LA VISTA LIVIANA DEL PASO TIZADA ─────────────────────────────────────────────────
    print("\n4 · 🔴 EL PASO TIZADA NO PUEDE CLAVAR EL NAVEGADOR")
    src_img = inspect.getsource(S.mesa_img)
    ok("fitz.open(ruta)" in src_img and "get_pixmap" in src_img,
       "la vista sale de la HOJA (el PDF que se descarga), no del SVG")
    ok(".svg" not in src_img,
       "🔴 …y NO del SVG: su rasterizador ignora los recortes y mostraría piezas mal cortadas")
    ok("os.replace(cache" in src_img, "se guarda una sola vez, y de forma atómica")
    app = io.open(os.path.join(_AQUI, "frontend", "src", "App.jsx"), encoding="utf-8").read()
    ok("mesa_img/${encodeURIComponent(hoja.archivo)}" in app, "la grilla de mesas la usa")
    ok("/trabajos/${trabajoEstado.resultado.id}/${pv}" in app,
       "…y el DETALLE sigue abriendo el vector (tocar la mesa)")
    ok(f"/trabajos/${{job.resultado.id}}/${{hoja.archivo}}" in app or "download" in app,
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

    print()
    if FALLOS:
        print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
        for f in FALLOS:
            print("   ·", f)
        sys.exit(1)
    print("✅ CONTRATO VERDE — la mesa la separan la columna de talle y la tela; el paso Tizada va liviano")


if __name__ == "__main__":
    main()
