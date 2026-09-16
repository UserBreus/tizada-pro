# -*- coding: utf-8 -*-
"""CONTRATO: EL RECORTE DEL VISOR SE PINTA DESDE UN DISPLAY LIST, EN UN PROCESO APARTE, Y ES
PÍXEL-IDÉNTICO AL DIBUJO DIRECTO; LA MESA SUELTA QUEDA EN DISCO
`py verificar_visor_display_list.py [hoja.pdf]`

Reporte del usuario (2026-09-16, 20 camisetas + 16 shorts de un diseño pesado): *«el paso de
tizada demoró como 5 minutos en mostrar todo, se ve borroso y descargar una mesa ya va 5 min y no
se descargó»*. Cada recorte re-interpretaba la página entera (4-17 s, en serie) reteniendo el GIL:
el server no atendía ni el latido ni la descarga mientras tanto (changelog 468 del MAPA).

Lo que se prueba:
  1. `_dibujar_vista_mesa` pinta el recorte desde el display list y el PNG es IDÉNTICO, byte a
     byte, al `page.get_pixmap(clip=)` de siempre (LEY: nunca menos calidad); el display list
     queda en el caché del proceso y el documento NO queda abierto.
  2. El endpoint `mesa_img` manda el dibujo al pool del visor (procesos aparte del server y de
     la tizada) y el pool devuelve el mismo archivo.
  3. `descargar_mesa` arma la mesa suelta UNA vez en disco (`descarga_<hoja>_p<n>.pdf`) y la
     segunda vez la sirve de ahí, con el mismo contenido.
  4. La pantalla pide el recorte en píxeles REALES (`devicePixelRatio`) y con prioridad baja.

⚠️ Sólo LEE la hoja de un trabajo ya generado (se copia a un temporal). No toca la base.
"""
import inspect
import io
import os
import shutil
import sys
import tempfile
import time
import types

sys.stdout.reconfigure(encoding="utf-8")
_AQUI = os.path.dirname(os.path.abspath(__file__))
# ⚠️ El worker del pool (spawn) vuelve a correr este encabezado: tiene que caer en el MISMO
# temporal que el padre, o dibuja en una carpeta que el padre no mira.
_TMP = os.environ.get("VERIF_VISOR_TMP") or tempfile.mkdtemp(prefix="verif_visor_dl_")
os.environ["VERIF_VISOR_TMP"] = _TMP
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"
os.environ["TIZADA_PROCESOS_VISOR"] = "1"

_falso_db = types.ModuleType("db")
_falso_db.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(
    AssertionError(f"LA PRUEBA INTENTO TOCAR MSSQL (db.{n}) — revisar el aislamiento")))
sys.modules["db"] = _falso_db
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)

FALLOS = []


def ok(cond, msg):
    print(("    OK    " if cond else "    ❌    ") + msg)
    if not cond:
        FALLOS.append(msg)


def _hoja_de_prueba():
    """Una hoja de varias páginas de un trabajo ya generado (la más grande que haya)."""
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        return sys.argv[1]
    import fitz
    mejor, tam = None, 0
    base = os.path.join(_AQUI, "trabajos")
    for tid in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        d = os.path.join(base, tid)
        for n in os.listdir(d) if os.path.isdir(d) else []:
            if n.startswith("HOJA_") and n.endswith(".pdf"):
                r = os.path.join(d, n)
                s = os.path.getsize(r)
                if s > tam:
                    try:
                        with fitz.open(r) as doc:
                            if doc.page_count < 2:
                                continue
                    except Exception:
                        continue
                    mejor, tam = r, s
    return mejor


def main():
    import registro as _LOG
    _LOG.usar_carpeta(os.path.join(_TMP, "logs"))
    import fitz
    import servidor as S

    orig = _hoja_de_prueba()
    if not orig:
        print("    ⚠️    no hay ninguna hoja de varias páginas en trabajos/: no se puede probar en vivo")
        return 0
    tid, hoja = "20990101-000000-test", os.path.basename(orig)
    os.makedirs(os.path.join(S.TRABAJOS, tid), exist_ok=True)
    ruta = os.path.join(S.TRABAJOS, tid, hoja)
    shutil.copy2(orig, ruta)
    print(f"hoja de prueba: {orig} ({os.path.getsize(orig) / 1e6:.1f} MB)\n")

    # ── 1. PÍXEL-IDÉNTICO Y SIN DEJAR EL DOCUMENTO ABIERTO ─────────────────────────────────
    print("1 · 🔴 EL RECORTE DESDE EL DISPLAY LIST ES EL MISMO DIBUJO DE SIEMPRE")
    rec = (0.25, 0.0625, 0.5, 0.125)
    with fitz.open(ruta) as d:
        pg = d[1]
        r = pg.rect
        clip = fitz.Rect(r.x0 + r.width * rec[0], r.y0 + r.height * rec[1],
                         r.x0 + r.width * rec[2], r.y0 + r.height * rec[3])
        z = 1600 / clip.width
        t0 = time.time()
        directo = pg.get_pixmap(matrix=fitz.Matrix(z, z), clip=clip, alpha=False)
        t_directo = time.time() - t0
        ref = (directo.width, directo.height, directo.samples)
    t0 = time.time()
    png = S._dibujar_vista_mesa(tid, hoja, 1, 1600, rec)
    t_primero = time.time() - t0
    ok(png and os.path.exists(png), f"se dibujó el recorte → {os.path.basename(png or '')}")
    pix = fitz.Pixmap(png)
    ok((pix.width, pix.height, pix.samples) == ref,
       f"🔴 píxel-idéntico al `get_pixmap(clip=)` directo ({pix.width}×{pix.height})")
    ok(len(S._DL_CACHE) == 1, "la página quedó en el caché de display lists del proceso")
    rec2 = (0.5, 0.0625, 0.75, 0.125)
    t0 = time.time()
    png2 = S._dibujar_vista_mesa(tid, hoja, 1, 1600, rec2)
    t_segundo = time.time() - t0
    ok(png2 and os.path.exists(png2) and t_segundo < max(1.0, t_directo / 2),
       f"el segundo recorte no vuelve a leer la página (directo {t_directo:.2f}s · 1º {t_primero:.2f}s · 2º {t_segundo:.2f}s)")
    # el documento no queda abierto: la carpeta del trabajo se tiene que poder borrar entera
    try:
        os.rename(ruta, ruta + ".mov")
        os.rename(ruta + ".mov", ruta)
        libre = True
    except OSError:
        libre = False
    ok(libre, "la hoja NO queda abierta (el display list vive solo; la carpeta se puede borrar)")

    # ── 2. EL ENDPOINT PASA POR EL POOL DEL VISOR ──────────────────────────────────────────
    print("\n2 · 🔴 LA PANTALLA NO DIBUJA EN EL HILO DEL SERVER")
    src = inspect.getsource(S.mesa_img)
    ok("_dibujar_vista_mesa_en_pool(" in src and "_dibujar_vista_mesa(tid" not in src,
       "`mesa_img` manda el recorte al pool del visor")
    rec3 = (0.0, 0.0625, 0.25, 0.125)
    t0 = time.time()
    png3 = S._dibujar_vista_mesa_en_pool(tid, hoja, 1, 900, rec3)
    ok(png3 and os.path.exists(png3), f"el pool devolvió el recorte ({time.time() - t0:.1f}s con el arranque del proceso)")
    ok(S._VISOR_POOL is not None, "…y es un pool propio del visor (aparte del de la tizada)")
    with fitz.open(ruta) as d:
        pg = d[1]
        r = pg.rect
        clip = fitz.Rect(r.x0, r.y0 + r.height * rec3[1], r.x0 + r.width * rec3[2], r.y0 + r.height * rec3[3])
        z = 900 / clip.width
        d3 = pg.get_pixmap(matrix=fitz.Matrix(z, z), clip=clip, alpha=False)
    p3 = fitz.Pixmap(png3)
    ok((p3.width, p3.height, p3.samples) == (d3.width, d3.height, d3.samples),
       "lo que dibuja el worker es píxel-idéntico también")
    try:
        S._VISOR_POOL.shutdown(wait=True)      # sin procesos huérfanos al terminar
    except Exception:
        pass

    # ── 3. LA MESA SUELTA QUEDA EN DISCO ───────────────────────────────────────────────────
    print("\n3 · LA MESA SUELTA SE ARMA UNA VEZ")
    with S.app.test_request_context(f"/api/trabajos/{tid}/mesa/{hoja}?pi=1&nombre=Mesa%202"):
        resp = S.descargar_mesa(tid, hoja)
        cuerpo1 = b"".join(resp.iter_encoded()) if hasattr(resp, "iter_encoded") else resp.get_data()
        resp.close()
    cache = os.path.join(S.TRABAJOS, tid, f"descarga_{os.path.splitext(hoja)[0]}_p1.pdf")
    ok(resp.status_code == 200 and os.path.exists(cache), f"quedó `{os.path.basename(cache)}` al lado del trabajo")
    ok(cuerpo1[:5] == b"%PDF-" and len(cuerpo1) == os.path.getsize(cache), "y lo que se mandó es ese archivo")
    with fitz.open(cache) as d:
        ok(d.page_count == 1, "de UNA página")
    m1 = os.stat(cache).st_mtime_ns
    with S.app.test_request_context(f"/api/trabajos/{tid}/mesa/{hoja}?pi=1&nombre=Mesa%202"):
        resp2 = S.descargar_mesa(tid, hoja)
        cuerpo2 = b"".join(resp2.iter_encoded())
        resp2.close()
    ok(os.stat(cache).st_mtime_ns == m1 and cuerpo2 == cuerpo1, "la segunda descarga sale del disco, igual byte a byte")

    # ── 4. LA PANTALLA ─────────────────────────────────────────────────────────────────────
    print("\n4 · LA PANTALLA PIDE NÍTIDO DE VERDAD")
    app = io.open(os.path.join(_AQUI, "frontend", "src", "App.jsx"), encoding="utf-8").read()
    ok("const necesario = (r.width / nx) * 1.25 * dpr;" in app and "devicePixelRatio" in app,
       "el ancho del recorte se pide en píxeles reales (devicePixelRatio)")
    ok('fetchPriority="low"' in app, "los recortes van con prioridad baja: la descarga y la app primero")

    # ── 5. LOS RECORTES YA ESTÁN CUANDO ALGUIEN HACE ZOOM (changelog 469) ─────────────────
    print("\n5 · 🔴 LOS RECORTES SE DEJAN DIBUJADOS AL TERMINAR EL PEDIDO, CON EL MISMO NOMBRE QUE PIDE LA PANTALLA")
    ok(S._js4(1 / 32) == 0.0313 and S._js4(0.25) == 0.25 and S._js4(1 / 14) == 0.0714,
       "la fracción se redondea como `toFixed(4)` de JS (1/32 → 0.0313, mitad para arriba)")
    recs = S._recortes_de_pagina(180.0, 799.1)
    ok(len(recs) == 4 * 16 and recs[0] == (0.0, 0.0, 0.25, 0.0625) and recs[-1] == (0.75, 0.9375, 1.0, 1.0),
       f"una mesa de 180 × 799 cm son 4 × 16 recortes de medio metro ({len(recs)}), en el orden de la pantalla")
    ok(S._RECORTE_W == (800, 1600) and "TOPE_RECORTES = { 800: 24, 1600: 12 }" in app
       and "const wpx = necesario <= 800 ? 800 : 1600;" in app,
       "los dos escalones del servidor (800 y 1600 px) son exactamente los que pide la pantalla")
    srv = io.open(os.path.join(_AQUI, "servidor.py"), encoding="utf-8").read()
    ok(srv.count('_predibujar_recortes_fondo(tid, res.get("hojas") or [])') == 2,
       "el pre-dibujado arranca cuando el pedido queda «listo», en `generar` y en `generar_multi`")
    ok("if len(pendientes) >= 2:" in inspect.getsource(S._predibujar_recortes_fondo),
       "…de a dos por vez: un recorte pedido por la pantalla no espera la cola entera")
    ok("r.width * dpr <= BASE_W * 1.05" in app, "el detalle arranca cuando la PANTALLA (en px reales) supera el dibujo general")

    # ── 6. LA FICHA TÉCNICA: INSTANTÁNEA, CON «NOMBRE» / «00» Y FONDO DETRÁS DEL OBJETO ────
    print("\n6 · 🔴 LA FICHA TÉCNICA")
    ok("_dibujar_vista_mesa_en_pool(tid, archivo, pi, int(round(_A4_PT * z)))" in inspect.getsource(S.pagina_img),
       "`pagina_img` dibuja por el mismo camino que las mesas (display list, pool del visor)")
    ok('"archivo": "FICHA_TECNICA.pdf"' in srv and "w=_FICHA_W, etiqueta=\"ficha\"" in srv,
       "…y la ficha se deja dibujada al final del pedido (no al abrir la pestaña)")
    _g = inspect.getsource(S._molde_guia_ficha)
    ok('"nombre": "NOMBRE", "numero": "00"' in _g and 'fila[_cid] = "NOMBRE"' in _g and ".get(\"muestra\")" not in _g,
       "el molde guía lleva «NOMBRE» y «00» como el paso Arte, nunca el nombre/número de una fila del pedido")
    ok("pers = MP.extraer_personalizacion(pl if _cbf else arte)" in _g,
       "…y con la personalización real del arte (con `pers` vacío la pieza quedaba SIN número)")
    ft = io.open(os.path.join(_AQUI, "ficha_tecnica.py"), encoding="utf-8").read()
    ok("pg.draw_rect(caja, color=LINEA, width=0.6, fill=(0.58, 0.60, 0.63))" in ft,
       "el objeto que no se sublima (TPU / bordado / DTF) va sobre un fondo gris: uno blanco se ve")
    ok('mg.get("ejemplo")' not in ft, "la ficha ya no dice «ejemplo: …» (no se estampa ninguna fila)")

    # ── 7. «EDITAR DISEÑO» AL INSTANTE ──────────────────────────────────────────────────────
    print("\n7 · «EDITAR DISEÑO» AL INSTANTE")
    ok("_cr = _editables_cacheados(" in inspect.getsource(S.get_editables)
       and "MP.extraer_editables(" not in inspect.getsource(S.get_editables),
       "`/api/productos/editables` no recorre el arte en cada apertura: lo pesado viene del caché")
    ok("_precalentar_editables(pid, sub)" in inspect.getsource(S.fuentes_estado),
       "…y se calienta al entrar al paso Arte (`fuentes_estado`)")

    # ── 8. «NUEVO PEDIDO» ───────────────────────────────────────────────────────────────────
    print("\n8 · «NUEVO PEDIDO»: SIEMPRE A «¿CÓMO VAS A ARMAR ESTE TRABAJO?», CON CARTEL BLOQUEANTE")
    ok("setBorrandoPedido('Borrando el pedido anterior…');" in app and 'role="alert" aria-busy="true"' in app,
       "un cartel tapa toda la pantalla mientras el servidor borra lo anterior")
    ok("setActivoTab('pedidos'); setVistaDiseno(null); setMapeandoOperario(false);" in app,
       "y se vuelve a la pantalla de Pedidos con las dos tarjetas, desde donde sea")
    ok("clearTimeout(_fin);\n        setBorrandoPedido(null);" in app, "el cartel se va cuando terminaron las tres limpiezas")

    print()
    if FALLOS:
        print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
        for f in FALLOS:
            print("   ·", f)
        return 1
    print("✅ CONTRATO VERDE — el recorte se pinta desde el display list, aparte del server, y es el mismo dibujo")
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        shutil.rmtree(_TMP, ignore_errors=True)
    sys.exit(rc)
