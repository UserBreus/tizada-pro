# -*- coding: utf-8 -*-
"""LA HOJA COMPARTIDA (camino B) — la tizada compuesta con pikepdf, con cada pieza UNA sola vez.

Por qué existe (2026-09-04, ver changelog 393 del mapa y `MOLDE_CON_DISENO.md` «LA HOJA
COMPARTIDA»): una tizada de 5 prendas tardaba 180 s porque CADA PRENDA repetía todo el trabajo —
la pieza se serializaba y se reabría por prenda, la hoja llevaba 45 copias enteras de la mesa
(una por colocación, 29 MB) y el aplanado para el RIP las des-anidaba inline (900.000 operadores,
87 s). Lineal en prendas: 100 camisetas eran más de 40 minutos.

La idea del usuario, formalizada: «primero se acomoda el contorno y después se le pone el diseño
adentro, guardando información». Se separa lo INVARIANTE de lo que cambia por prenda:

  · BASE  = una por (pieza, talle[, variante]): la página del molde desplegado metida ADENTRO por
    concatenación de bytes (la receta exacta de `aplanar_rip._flatten`: `q [Matrix cm] [BBox re
    W n] <contenido> Q`, ya verificada pixel-idéntica) + el clip al contorno + el borde de corte.
    Es UN Form XObject plano (profundidad 1), armado una vez y referenciado N veces.
  · COLOCACIÓN = `q <cm> /B_k Do Q` + `q <cm> <estampado> Q`, donde el estampado son los trazos
    chicos por prenda (nombre/número en curvas + etiqueta) que ya genera `generar_pieza`.

Lo que sale es 100 % vectorial, con los bytes del dibujo del usuario tal cual (no se re-serializa
ni un operador de la mesa), en CMYK exacto. El archivo queda con estructura «PDF/X-1a-like»:
XObjects de un solo nivel, sin capas, sin transparencia, fuentes embebidas o en curvas.

⚠️ pikepdf copia perezoso (`copy_foreign`): los PDF de las mesas desplegadas tienen que seguir
ABIERTOS hasta después del `save` — el que llama los tiene vivos en `b["despl"]`.
"""
import io
import math
import os
from math import ceil

import pikepdf
from pikepdf import Name

CM = 72 / 2.54
_MAX_SVG_CACHE = 400        # SVG de bases cacheados por arte o por molde desplegado (~1 MB cada uno)


def _contenido_pagina(pag):
    """Los bytes del content-stream de una página (uno o varios streams, unidos por '\\n')."""
    c = pag.obj.get("/Contents")
    if c is None:
        return b""
    if isinstance(c, pikepdf.Array):
        return b"\n".join(s.read_bytes() for s in c)
    return c.read_bytes()


def _num(v):
    t = f"{float(v):.6f}".rstrip("0").rstrip(".")
    return t if t not in ("", "-0") else "0"


def xobject_base(pdf, b, memo):
    """El Form XObject de UNA base, dentro de `pdf`: la mesa desplegada inline + clip + borde.

    `b` es lo que devuelve `_armar_base` del motor (camino B): `base_stream` (str: borde +
    `q cm q <clip> W n <nom> Do Q Q`), `despl` = (pdf_fuente, índice_de_página), `nom` (el nombre
    del XObject de la mesa en ese stream), `W`, `H`, `Hp`, `B`. `memo` cachea por id(b).
    """
    k = id(b)
    hit = memo.get(k)
    if hit is not None:
        return hit
    src, idx = b["despl"][0], b["despl"][1]
    try:
        pag = src.pages[idx]
    except Exception:
        # el motor cerró el PDF de la mesa (cerrar_abiertos): se reabre por su ruta y se deja
        # vivo hasta después del save (copy_foreign es perezoso)
        src = pikepdf.open(b["despl"][2])
        memo.setdefault("__abiertos__", []).append(src)
        pag = src.pages[idx]
    # La misma lectura que hace el motor: `as_form_xobject()` sólo para saber cómo hay que
    # posicionar la mesa (Matrix) y recortarla (BBox). No se copia ese objeto: la mesa entra
    # INLINE, que es lo que el aplanado para el RIP hacía después con cada copia.
    xo_tmp = pag.as_form_xobject()
    mtx = xo_tmp.get("/Matrix")
    bbox = xo_tmp.get("/BBox")
    partes = [b"q\n"]
    if mtx is not None:
        partes.append((" ".join(_num(float(x)) for x in mtx) + " cm\n").encode("ascii"))
    if bbox is not None:
        x0, y0, x1, y1 = [float(v) for v in bbox]
        partes.append(f"{_num(min(x0, x1))} {_num(min(y0, y1))} {_num(abs(x1 - x0))} {_num(abs(y1 - y0))} re\nW\nn\n".encode("ascii"))
    partes.append(_contenido_pagina(pag))
    partes.append(b"\nQ\n")
    inline = b"".join(partes)
    base = b["base_stream"].encode("latin-1")
    ref = f"{b['nom']} Do".encode("ascii")
    if base.count(ref) != 1:
        raise RuntimeError(f"la base de {b.get('pieza')} no referencia la mesa una sola vez ({base.count(ref)})")
    contenido = base.replace(ref, inline)
    # Los recursos son los de la página desplegada (fuentes embebidas, ICC, imágenes…). Se
    # conservan las fuentes: un texto vivo del diseño que no sea placeholder tiene que salir en
    # la hoja igual que se ve en el Arte (ley del proyecto; antes `_barrer_fuentes` lo borraba).
    res_src = xo_tmp.get("/Resources")
    # `copy_foreign` sólo acepta objetos INDIRECTOS: los recursos de la página vienen directos.
    # Volverlos indirectos en el PDF de la mesa (en memoria, nunca se guarda) los deja copiables
    # y deduplicados: dos talles de la misma mesa comparten fuentes e ICC en la hoja.
    res = pdf.copy_foreign(src.make_indirect(res_src)) if res_src is not None else pikepdf.Dictionary()
    xo = pdf.make_stream(contenido)
    xo["/Type"] = Name("/XObject")
    xo["/Subtype"] = Name("/Form")
    xo["/BBox"] = pikepdf.Array([0, 0, float(b["W"]) + 2 * float(b["B"]), float(b["Hp"])])
    xo["/Resources"] = res
    # Marca propia: la base viene de una página desplegada (sin marcadores de capa, con todas
    # sus fuentes declaradas, balanceada por contrato) → el aplanado para el RIP y la validación
    # no tienen que volver a parsear sus 20.000 operadores. Una clave privada en un XObject es
    # PDF válido; los lectores la ignoran.
    xo["/TizadaBase"] = True
    memo[k] = xo
    return xo


def matriz_colocacion(c, m, s, alto_pag, W, H, signo=1):
    """La `cm` que deja la base (BBox 0 0 W H, y hacia arriba) donde `componer_pdf_contorno` la
    ponía con `show_pdf_page(rect, doc, 0, rotate=ang)`: el rect es la caja del contorno ROTADO
    (`bw`×`bh`), centrada en (cx, cy) en coordenadas de la hoja con el origen arriba a la
    izquierda. En PDF (origen abajo) el centro es (x, alto − y). `signo` es el sentido de giro
    que reproduce a PyMuPDF: +1, calibrado contra `show_pdf_page` con rotación libre (2026-09-04:
    con −1 las piezas giradas salían para el otro lado; 1,6 M de píxeles distintos)."""
    cx = (m["izq"] * CM + c["cx"]) * s
    cy = alto_pag * s - (m["sup"] * CM + c["cy"]) * s
    th = math.radians(signo * c["ang"])
    ca, sa = math.cos(th), math.sin(th)
    a, b_, c_, d = s * ca, s * sa, -s * sa, s * ca
    # trasladar el centro de la base (W/2, H/2) al centro de la colocación
    e = cx - (a * W / 2 + c_ * H / 2)
    f = cy - (b_ * W / 2 + d * H / 2)
    # 6 decimales también en la traslación: con 3, las piezas giradas caían hasta medio punto
    # más allá que en `show_pdf_page` y el render difería en los bordes (0,14 % de píxeles).
    return f"{a:.6f} {b_:.6f} {c_:.6f} {d:.6f} {e:.6f} {f:.6f} cm"


def componer_hoja_pike(colocaciones, cfg, path_salida, signo_rotacion=1):
    """Escribe la hoja (una página por mesa física) y devuelve `(consumo_cm, alturas_cm)`, igual
    que `nesting_contorno.componer_pdf_contorno`. Cada `c["pieza"]` trae `base` y `estampado`."""
    m = cfg["margenes_cm"]
    ancho_pag = cfg["ancho_cm"] * CM
    pdf = pikepdf.new()
    memo = {}
    consumo_cm, alturas_cm = 0.0, []
    for hoja in colocaciones:
        if not hoja:
            continue
        alto_usado = max(c["cy"] + c["bh"] / 2 for c in hoja)
        alto_pag = alto_usado + (m["sup"] + m["inf"]) * CM
        # Mesas de más de 5,08 m: /UserUnit, como en el compositor de siempre (ver ahí).
        uu = max(1, ceil(max(ancho_pag, alto_pag) / 14400.0))
        s = 1.0 / uu
        page = pdf.add_blank_page(page_size=(ancho_pag * s, alto_pag * s))
        if uu > 1:
            page.obj["/UserUnit"] = int(uu)
        xobjs = pikepdf.Dictionary()
        nombres = {}
        partes = []
        for c in hoja:
            pz = c["pieza"]
            b = pz["base"]
            xo = xobject_base(pdf, b, memo)
            nm = nombres.get(id(xo))
            if nm is None:
                nm = f"/B{len(nombres) + 1}"
                nombres[id(xo)] = nm
                xobjs[nm] = xo
            W = float(b["W"]) + 2 * float(b["B"])
            H = float(b["Hp"])
            cm = matriz_colocacion(c, m, s, alto_pag, W, H, signo_rotacion)
            partes.append(f"q\n{cm}\n{nm} Do\nQ\n".encode("ascii"))
            est = pz.get("estampado") or ""
            if est:
                partes.append(f"q\n{cm}\n".encode("ascii") + est.encode("latin-1") + b"Q\n")
        page.obj["/Contents"] = pdf.make_stream(b"".join(partes))
        page.obj["/Resources"] = pikepdf.Dictionary({"/XObject": xobjs})
        alturas_cm.append(round(alto_pag / CM, 1))
        consumo_cm += alto_pag / CM
    # Sin comprimir: esta hoja es intermedia — el aplanado para el RIP la vuelve a escribir (y
    # ahí sí comprime). Deflatear 27 mesas de 1,6 MB acá costaba 5 s por nada.
    pdf.save(path_salida, compress_streams=False)
    pdf.close()
    for d in memo.get("__abiertos__", []):
        try:
            d.close()
        except Exception:
            pass
    return consumo_cm, alturas_cm


# ── VISTA PREVIA LIVIANA ─────────────────────────────────────────────────────────────────────
def _svg_interior(svg, prefijo=""):
    """Lo que hay adentro del `<svg …>…</svg>` que devuelve PyMuPDF (sin la envoltura).

    `prefijo`: PyMuPDF numera sus recortes y máscaras (`id="cp0"`, `url(#cp0)`) desde cero en
    CADA documento. Metidos varios en un mismo SVG, los ids chocan y el recorte de una pieza se
    aplica a otra (2026-09-04: el preview mostraba las mesas enteras sin recortar). Se les pone
    un prefijo por símbolo."""
    i = svg.find("<svg")
    if i >= 0:
        j = svg.index(">", i) + 1
        k = svg.rfind("</svg>")
        svg = svg[j:k if k > 0 else len(svg)]
    if prefijo:
        svg = (svg.replace('id="', f'id="{prefijo}')
                  .replace("url(#", f"url(#{prefijo}")
                  .replace('href="#', f'href="#{prefijo}'))
    return svg


def _svg_de_ops(W, H, ops_bytes, fitz, prefijo=""):
    """Un pedazo de content-stream (los trazos del estampado de una prenda) convertido a SVG por
    PyMuPDF, en coordenadas de página (pt, y hacia abajo). Sin recursos: son sólo trazados."""
    pdf = pikepdf.new()
    pg = pdf.add_blank_page(page_size=(W, H))
    pg.obj["/Contents"] = pdf.make_stream(ops_bytes)
    buf = io.BytesIO()
    pdf.save(buf)
    pdf.close()
    d = fitz.open("pdf", buf.getvalue())
    svg = d[0].get_svg_image()
    d.close()
    return _svg_interior(svg, prefijo)


def svg_de_pdf_bytes(pdf_bytes):
    """WORKER (proceso): el SVG de la primera página de un PDF en memoria. Sólo PyMuPDF."""
    import pymupdf as fitz
    d = fitz.open("pdf", pdf_bytes)
    try:
        return d[0].get_svg_image()
    finally:
        d.close()


def _ruta_cache_svg(b):
    """`(carpeta, ruta)` del SVG cacheado de una base del camino B (al lado del desplegado), o
    `(None, None)` si la base no viene de un molde desplegado (camino A: no hay dónde)."""
    import hashlib
    import re as _re
    try:
        if b.get("despl"):
            carpeta = os.path.join(os.path.dirname(b["despl"][2]), "svg")
            _cuerpo = b["base_stream"].replace(str(b.get("nom") or "\x00"), "@XO")
            _mesa = os.path.basename(str(b["despl"][2]))
            clave = hashlib.sha1((_cuerpo + "|" + _mesa + "|" + str(b["despl"][1])).encode("latin-1")).hexdigest()[:20]
            return carpeta, os.path.join(carpeta, f"{clave}.svg")
        if b.get("svg_cache"):
            # CAMINO A (2026-09-07): la caché vive al lado del arte (`svg_cache/`). La clave es el
            # `base_stream` con los nombres AL AZAR de los XObjects (`/A…`, `/E…`, `/OA…`, 22
            # caracteres que pone `page.add_resource`) reemplazados, más la firma del arte y de la
            # plantilla (fecha y tamaño): cambia el arte, el contorno, el borde o un editable →
            # otra clave.
            carpeta, firma = b["svg_cache"]
            _cuerpo = _re.sub(r"/[A-Z]{1,2}[A-Za-z0-9_-]{20,24}\b", "/@XO", b["base_stream"])
            clave = hashlib.sha1((_cuerpo + "|" + str(firma)).encode("latin-1")).hexdigest()[:20]
            return carpeta, os.path.join(carpeta, f"{clave}.svg")
    except Exception:
        pass
    return None, None


def svgs_de_bases(bases, docs_base, procesos=None):
    """`{id(base): svg crudo}` de todas las bases de una tizada, de una vez.

    Lo caro de la preview es convertir cada base a SVG: PyMuPDF recorre el arte entero de la mesa
    recortado a la pieza (~0,3-0,4 s por base en el camino A, cuyo arte no está podado). Con 5
    prendas de 5 talles son 45 bases distintas: 13 s en serie, que eran 13 de los 15 s de la
    tizada (2026-09-07). Acá: (1) las que están en la caché de disco (camino B) se leen; (2) las
    demás se convierten en PARALELO si `procesos` es un ejecutor (el pool de render del servidor)
    o un número > 1 (pool propio, sólo desde un script con guardián `__main__`); None = en serie.
    Los documentos de las bases se serializan acá (bytes, ~20 ms cada uno) y viajan al worker."""
    out, pendientes = {}, []
    for b in bases:
        k = id(b)
        if k in out or k in {p[0] for p in pendientes}:
            continue
        carpeta, ruta = _ruta_cache_svg(b)
        if ruta and os.path.exists(ruta):
            try:
                with open(ruta, encoding="utf-8") as fh:
                    out[k] = fh.read()
                continue
            except Exception:
                pass
        pendientes.append((k, b, carpeta, ruta))
    if not pendientes:
        return out
    ejecutor, propio = None, None
    if procesos is not None and hasattr(procesos, "submit"):
        ejecutor = procesos
    elif isinstance(procesos, int) and procesos > 1 and len(pendientes) > 1:
        try:
            from concurrent.futures import ProcessPoolExecutor
            propio = ejecutor = ProcessPoolExecutor(max_workers=min(procesos, len(pendientes)))
        except Exception:
            ejecutor = None
    svgs = {}
    if ejecutor is not None:
        try:
            futs = {k: ejecutor.submit(svg_de_pdf_bytes, docs_base(b).tobytes()) for k, b, _c, _r in pendientes}
            for k, f in futs.items():
                svgs[k] = f.result(timeout=300)
        except Exception as e:
            print(f"[preview] SVG de bases en paralelo falló ({e}); sigo en serie", flush=True)
            svgs = {}
        finally:
            if propio is not None:
                propio.shutdown(wait=False)
    for k, b, carpeta, ruta in pendientes:
        svg = svgs.get(k)
        if svg is None:
            svg = docs_base(b)[0].get_svg_image()
        out[k] = svg
        if ruta:
            try:
                os.makedirs(carpeta, exist_ok=True)
                with open(ruta + ".tmp", "w", encoding="utf-8") as fh:
                    fh.write(svg)
                os.replace(ruta + ".tmp", ruta)
            except Exception:
                pass
    # la caché no crece sin límite: cada arte/desplegado guarda a lo sumo `_MAX_SVG_CACHE`
    # bases (las más viejas se van). Un molde de 20 talles × 9 piezas son 180.
    for carpeta in {c for _k, _b, c, _r in pendientes if c}:
        try:
            svgs_disco = [os.path.join(carpeta, f) for f in os.listdir(carpeta) if f.endswith(".svg")]
            if len(svgs_disco) > _MAX_SVG_CACHE:
                svgs_disco.sort(key=os.path.getmtime)
                for viejo in svgs_disco[:len(svgs_disco) - _MAX_SVG_CACHE]:
                    os.remove(viejo)
        except Exception:
            pass
    return out


def svg_base_cacheado(b, docs_base, prefijo):
    """El SVG de una base, cacheado EN DISCO al lado del desplegado del molde
    (`desplegado/svg/<clave>.svg`). La clave es el contenido de la base (mesa, talle, contorno,
    borde y su config): cambia el borde → otra clave. Armar el documento de la base y convertirlo
    costaba ~0,4 s por base y por tizada (8 s en un pedido de 5 prendas): con la caché, la segunda
    tizada del mismo molde lo lee en milisegundos."""
    import hashlib
    try:
        carpeta = os.path.join(os.path.dirname(b["despl"][2]), "svg")
        # ⚠️ `base_stream` nombra la mesa con el nombre que le puso `page.add_resource`, y pikepdf
        # lo genera AL AZAR (`/A3f9c…`): con él adentro la clave cambiaba en cada tizada y la caché
        # no acertaba nunca (medido: 27 SVG nuevos por corrida, 7 s). Se lo saca de la clave.
        _cuerpo = b["base_stream"].replace(str(b.get("nom") or "\x00"), "@XO")
        # …y la MESA va en la clave: dos piezas de mesas distintas con el mismo contorno (cuello
        # derecho / izquierdo) tendrían el mismo `base_stream` y compartirían el SVG equivocado.
        _mesa = os.path.basename(str(b["despl"][2]))
        clave = hashlib.sha1((_cuerpo + "|" + _mesa + "|" + str(b["despl"][1])).encode("latin-1")).hexdigest()[:20]
        ruta = os.path.join(carpeta, f"{clave}.svg")
        if os.path.exists(ruta):
            with open(ruta, encoding="utf-8") as fh:
                return _svg_interior(fh.read(), prefijo)
    except Exception:
        ruta = None
    d = docs_base(b)
    svg = d[0].get_svg_image()
    if ruta:
        try:
            os.makedirs(carpeta, exist_ok=True)
            with open(ruta + ".tmp", "w", encoding="utf-8") as fh:
                fh.write(svg)
            os.replace(ruta + ".tmp", ruta)
        except Exception:
            pass
    return _svg_interior(svg, prefijo)


def preview_svg(hoja, cfg, alto_pag, simbolos, docs_base, signo_rotacion=1, crudos=None):
    """El SVG de UNA página de la hoja: `<symbol>` por base (una sola vez, cacheado en `simbolos`
    por id(base)) y `<use>` por colocación, más el estampado de cada prenda como trazos.

    Hasta 2026-09-04 el preview era `page.get_svg_image()` de la hoja entera: PyMuPDF expande cada
    colocación → 64 MB por hoja de 5 prendas, 1,3 GB a 100. Con símbolos reutilizados, cada base
    pesa una vez. Es vectorial y sale del MISMO documento de base que va a la hoja (ley «se ve =
    sale»); el visor (`<img src=prev_*.svg>`) lo muestra tal cual.
    `docs_base(b)` devuelve un `fitz.Document` de la base sola (sin estampado)."""
    import pymupdf as fitz
    m = cfg["margenes_cm"]
    ancho_pag = cfg["ancho_cm"] * CM
    defs, cuerpo, ids = [], [], {}
    # Los estampados de TODAS las prendas de la hoja se convierten a SVG de UNA vez (un documento
    # con todos, en coordenadas de página): a 100 prendas eran 900 idas y vueltas por PyMuPDF
    # (183 s); ahora es una por hoja.
    ops_est = []
    for c in hoja:
        pz = c["pieza"]
        b = pz["base"]
        W = float(b["W"]) + 2 * float(b["B"])
        H = float(b["Hp"])
        k = id(b)
        # 🔴 EL PREFIJO ES DE LA BASE, NO DE SU POSICIÓN EN LA PÁGINA.
        # El contenido de cada símbolo se cachea en `simbolos` ENTRE PÁGINAS y lleva el prefijo
        # escrito adentro (`B7_clip_1`, …). Si el número se sacara de `len(ids)`, que arranca de
        # cero en cada página, en la hoja 2 una base distinta recibiría un prefijo que otra ya
        # usó: dos `clipPath` con el MISMO id. En un navegador gana el primero, así que la pieza
        # se recorta con la silueta de OTRA — una tira sale con la loma de una manga adentro y
        # media blanca. Reportado por el usuario (2026-09-10) como «piezas cortadas y el diseño
        # del arte en piezas que no van». No falla nada: sólo se ve mal, y es lo que él mira para
        # aprobar el trabajo. Contrato: `verificar_previa_recortes.py`.
        _sids = simbolos.setdefault("__sid__", {})   # id(base) → prefijo, estable en toda la hoja
        sid = _sids.get(k)
        if sid is None:
            sid = f"B{len(_sids) + 1}"
            _sids[k] = sid
        if k not in ids:                              # primera vez EN ESTA PÁGINA: va su <symbol>
            ids[k] = sid
            sym = simbolos.get(k)
            if sym is None:
                _raw = (crudos or {}).get(k)          # ya convertida (en paralelo, `svgs_de_bases`)
                sym = _svg_interior(_raw, sid + "_") if _raw is not None else svg_base_cacheado(b, docs_base, sid + "_")
                simbolos[k] = sym
            defs.append(f'<symbol id="{sid}" viewBox="0 0 {W:.3f} {H:.3f}" overflow="visible">{sym}</symbol>')
        cx = m["izq"] * CM + c["cx"]
        cy = m["sup"] * CM + c["cy"]                     # y hacia abajo, como el SVG
        # en SVG (y hacia abajo) el mismo giro que en PDF (y hacia arriba) lleva el signo opuesto
        tr = f'translate({cx:.3f} {cy:.3f}) rotate({-signo_rotacion * c["ang"]:.3f}) translate({-W/2:.3f} {-H/2:.3f})'
        cuerpo.append(f'<use href="#{sid}" x="0" y="0" width="{W:.3f}" height="{H:.3f}" transform="{tr}"/>')
        est = pz.get("estampado") or ""
        if est.strip():
            cm_pdf = matriz_colocacion(c, m, 1.0, alto_pag, W, H, signo_rotacion)
            ops_est.append(("q\n" + cm_pdf + "\n").encode("ascii") + est.encode("latin-1") + b"Q\n")
    if ops_est:
        # ── MESAS DE MÁS DE 5,08 m EN LA VISTA PREVIA ────────────────────────────────────────
        # 🔴 El estampado se traduce a SVG dibujándolo en una página temporal del tamaño de la
        # hoja, y NINGUNA página PDF puede pasar de 14400 unidades (508 cm). La hoja de verdad ya
        # lo resolvía con /UserUnit (ver `componer_hoja_pike`); esto no, así que una mesa larga
        # tiraba «Page size must be between 3 and 14400 PDF units» — y como el preview NO estaba
        # protegido, se caía el pedido ENTERO después de haber armado bien la tizada
        # (reporte del usuario 2026-09-09, con el tope de mesa en 50 m).
        # Se dibuja todo dividido por `uu` en una página que sí entra, y el grupo se devuelve
        # multiplicado por `uu`: mismas coordenadas, mismo vector, sin perder un solo trazo.
        uu = max(1, ceil(max(ancho_pag, alto_pag) / 14400.0))
        s_uu = 1.0 / uu
        ops = b"".join(ops_est)
        if uu > 1:
            ops = f"q\n{s_uu:.8f} 0 0 {s_uu:.8f} 0 0 cm\n".encode("ascii") + ops + b"Q\n"
        _svg_est = _svg_de_ops(ancho_pag * s_uu, alto_pag * s_uu, ops, fitz, "est_")
        cuerpo.append(f'<g transform="scale({uu:g})">{_svg_est}</g>' if uu > 1
                      else '<g>' + _svg_est + '</g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'viewBox="0 0 {ancho_pag:.3f} {alto_pag:.3f}" width="{ancho_pag:.3f}pt" height="{alto_pag:.3f}pt">'
            f'<rect width="100%" height="100%" fill="#ffffff"/><defs>{"".join(defs)}</defs>{"".join(cuerpo)}</svg>')


def altos_de_hojas(colocaciones, cfg):
    """El alto (pt) de cada página, con la misma cuenta que `componer_hoja_pike`."""
    m = cfg["margenes_cm"]
    out = []
    for hoja in colocaciones:
        if not hoja:
            continue
        out.append(max(c["cy"] + c["bh"] / 2 for c in hoja) + (m["sup"] + m["inf"]) * CM)
    return out
