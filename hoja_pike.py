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
            import procesos as _PR           # `spawn` en todos los sistemas: ver `procesos.contexto`
            propio = ejecutor = _PR.pool(min(procesos, len(pendientes)))
        except Exception:
            ejecutor = None
    svgs = {}
    en_procesos = ejecutor is not None
    if ejecutor is not None:
        # 🔴 LO QUE TERMINÓ SE CONSERVA Y NADA SE CONVIERTE ACÁ (2026-09-17). Antes, con UNA base
        # que no llegaba a tiempo se tiraban todas las convertidas y se hacían TODAS en este
        # proceso, con el GIL tomado: en el servidor publicado eso es el pedido entero clavado. Se
        # esperan todas juntas con UN tope, las que faltan se reintentan una vez en un pool nuevo
        # (si el pool es propio) y las que aun así faltan salen de la previa como `None`: la vista
        # previa es un adorno best-effort, la tizada no depende de ella.
        import procesos as _PR
        from concurrent.futures import wait as _esperar
        tope = _PR.tope_segundos("TIZADA_TOPE_SVG_S", 300)
        faltan = list(pendientes)
        for intento in (1, 2):
            try:
                futs = {k: ejecutor.submit(svg_de_pdf_bytes, docs_base(b).tobytes()) for k, b, _c, _r in faltan}
                _listos, _sin = _esperar(list(futs.values()), timeout=tope)
                for k, f in futs.items():
                    if f in _listos and f.exception() is None:
                        svgs[k] = f.result()
                    else:
                        try:
                            f.cancel()
                        except Exception:
                            pass
            except Exception as e:
                print(f"[preview] SVG de bases en paralelo falló ({type(e).__name__}: {e})", flush=True)
            faltan = [p for p in faltan if p[0] not in svgs]
            if not faltan:
                break
            print(f"[preview] {len(faltan)} base(s) sin SVG en el intento {intento} (tope {tope:.0f} s)", flush=True)
            if propio is not None:
                _PR.descartar(propio)        # uno trabado no se destraba: se mata
                propio = ejecutor = None
                if intento == 1:
                    try:
                        propio = ejecutor = _PR.pool(min(procesos, len(faltan)), que="los SVG de la previa")
                    except Exception as e:
                        print(f"[preview] sin procesos para reintentar los SVG ({type(e).__name__}: {e})", flush=True)
                        break
            else:
                break                        # el pool es ajeno (el del servidor): no se reintenta acá
        if propio is not None:
            propio.shutdown(wait=False)
    for k, b, carpeta, ruta in pendientes:
        svg = svgs.get(k)
        if svg is None:
            if en_procesos:
                out[k] = None                # la previa sale sin esta base; NO se convierte acá
                continue
            svg = docs_base(b)[0].get_svg_image()   # sin procesos (un script): acá, a propósito
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
                if crudos is not None and k in crudos:
                    # ya convertida (en paralelo, `svgs_de_bases`); `None` = los procesos no la
                    # terminaron: la previa sale SIN esa base antes que convertirla acá con el GIL
                    _raw = crudos[k]
                    sym = _svg_interior(_raw, sid + "_") if _raw is not None else ""
                else:
                    sym = svg_base_cacheado(b, docs_base, sid + "_")
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


# ── LA HOJA CON EL SELLO (2026-09-15) ────────────────────────────────────────────────────────
# `componer_hoja_pike` (arriba) mete el dibujo de la mesa ADENTRO de cada base: una copia por
# (pieza, talle), y en el camino A ni siquiera eso — cada colocación llevaba su copia entera.
# Medido sobre una tizada real: el **97 %** de cada colocación es el mismo dibujo (768 KB de 791),
# y la página de 8 m tenía **19,8 MB de contenido con sólo 3,5 MB distintos**.
#
# Acá el dibujo de cada mesa entra UNA sola vez a la hoja, como Form XObject de página, y cada
# pieza queda como: `q <matriz> <su recorte + su borde> /MESA Do <su nombre y número> Q`.
# Estructura final: **UN solo nivel de XObject** — exactamente la que ya deja `aplanar_rip` y la
# que el RIP del usuario procesó bien (changelog 456).
_RX_NOM = None


def _remapear(stream, ren):
    """Cambia los nombres de XObject del `base_stream` por los globales de la hoja."""
    import re
    global _RX_NOM
    if not ren:
        return stream
    if _RX_NOM is None:
        # 🔴 EL JUEGO DE CARACTERES COMPLETO DE UN NOMBRE PDF. `page.add_resource` genera nombres
        # al azar del estilo `/Ax_-73ZjlLXUbUuqaylXI2g`: con un patrón de sólo letras y dígitos
        # el remapeo no acertaba ninguno y la hoja salía con «cannot find XObject resource».
        _RX_NOM = re.compile(r"/([^\s/\[\]<>(){}%]+)(?=\s+Do(?![A-Za-z0-9]))")
    return _RX_NOM.sub(lambda m: ren.get("/" + m.group(1), "/" + m.group(1)), stream)


def componer_hoja_sello(colocaciones, cfg, path_salida, signo_rotacion=1, progreso=None):
    """Escribe la hoja con el dibujo de cada mesa UNA sola vez. Devuelve `(consumo_cm, alturas_cm)`,
    igual que `nesting_contorno.componer_pdf_contorno`.

    Cada `c["pieza"]` trae `base` (con `base_stream` y `fuentes_xo`) y `estampado`.
    """
    m = cfg["margenes_cm"]
    ancho_pag = cfg["ancho_cm"] * CM
    pdf = pikepdf.new()
    consumo_cm, alturas_cm = 0.0, []
    xobjs = pikepdf.Dictionary()
    ren_por_base = {}          # id(base) → {nombre_local: nombre_global}
    # objgen del objeto de origen → [(objeto, nombre global)]. 🔴 El objgen SOLO NO ALCANZA: es el
    # número del objeto DENTRO DE SU ARCHIVO, y dos artes distintos (JUGADOR y GOLERO del mismo
    # molde, salidos de la misma plantilla de Illustrator) pueden tener el mismo número: la hoja
    # le ponía a uno el dibujo del otro. Se compara también el dueño (`same_owner_as`).
    por_fuente = {}
    abiertos = []

    def _global(fuente, del_molde=False):
        """El nombre global de un dibujo de origen; lo copia a la hoja la primera vez."""
        try:
            k = fuente.objgen
            if k == (0, 0):                 # objeto directo: no tiene número propio
                k = ("id", id(fuente))
        except Exception:
            k = ("id", id(fuente))
        nm = None
        for _f0, _nm0 in por_fuente.get(k, ()):
            try:
                if _f0 is fuente or _f0.same_owner_as(fuente):
                    nm = _nm0
                    break
            except Exception:
                continue
        if nm is None:
            xo = pdf.copy_foreign(fuente)
            if "/OC" in xo:
                del xo["/OC"]
            if "/Group" in xo:
                del xo["/Group"]
            # 🔴 LA MESA DEL MOLDE DESPLEGADO YA VIENE LIMPIA. Nace de una página que el alta dejó
            # sin marcadores de capa, con sus fuentes declaradas y balanceada (contrato del
            # desplegado): marcarla le ahorra a `aplanar_rip` volver a parsear y re-serializar sus
            # ~118.000 operadores. Es la MISMA marca que ya usaba la hoja compartida del camino B
            # (changelog 393: aplanado 15 → 4 s), y se pone SÓLO si no anida otros dibujos adentro.
            if del_molde and "/XObject" not in (xo.get("/Resources") or {}):
                xo["/TizadaBase"] = True
            nm = f"/S{len(xobjs)}"
            por_fuente.setdefault(k, []).append((fuente, nm))
            xobjs[nm] = xo
        return nm

    def _ren(b):
        r = ren_por_base.get(id(b))
        if r is None:
            _dm = bool(b.get("despl"))
            r = {nom: _global(src, _dm) for nom, src in (b.get("fuentes_xo") or {}).items()}
            ren_por_base[id(b)] = r
        return r

    paginas = []
    por_pagina = []           # (página, nombres de dibujo que usa)
    for hoja in colocaciones:
        if not hoja:
            continue
        alto_usado = max(c["cy"] + c["bh"] / 2 for c in hoja)
        alto_pag = alto_usado + (m["sup"] + m["inf"]) * CM
        uu = max(1, ceil(max(ancho_pag, alto_pag) / 14400.0))
        s = 1.0 / uu
        page = pdf.add_blank_page(page_size=(ancho_pag * s, alto_pag * s))
        paginas.append(page)
        if uu > 1:
            page.obj["/UserUnit"] = int(uu)
        partes = []
        usados = set()
        for c in hoja:
            pz = c["pieza"]
            b = pz["base"]
            W = float(b["W"]) + 2 * float(b["B"])
            H = float(b["Hp"])
            mtx = matriz_colocacion(c, m, s, alto_pag, W, H, signo_rotacion)
            ren = _ren(b)
            usados.update(ren.values())
            # 🔴 EL RECORTE A LA CAJA DE LA PIEZA. En el compositor de siempre cada pieza es una
            # PÁGINA que se muestra con `show_pdf_page`, y eso recorta a su MediaBox; acá el
            # contenido se pega inline, así que el recorte hay que ponerlo. Sin él, lo que la
            # pieza dibujara un pelo afuera de su caja salía en la hoja: ~0,05 % de píxeles
            # distintos, repartidos por todos los bordes. (Es la misma receta que usa
            # `aplanar_rip._flatten` al des-anidar: `q [Matrix cm] [BBox re W n] … Q`.)
            partes.append(f"q\n{mtx}\n0 0 {_num(W)} {_num(H)} re\nW\nn\n".encode("ascii"))
            partes.append(_remapear(b["base_stream"], ren).encode("latin-1"))
            est = pz.get("estampado") or ""
            if est:
                partes.append(est.encode("latin-1"))
            partes.append(b"Q\n")
        page.obj["/Contents"] = pdf.make_stream(b"".join(partes))
        por_pagina.append((page, usados))
        alturas_cm.append(round(alto_pag / CM, 1))
        consumo_cm += alto_pag / CM
        if progreso:
            progreso("escribir el PDF", f"mesa {len(alturas_cm)}", None)
    # 🔴 LOS RECURSOS SE ASIGNAN AL FINAL, Y CADA PÁGINA CON SU PROPIA TABLA. Dos motivos:
    # (a) el diccionario de dibujos sigue creciendo mientras se recorren las mesas — asignarlo
    #     página por página guardaría una copia con lo que hubiera hasta ese momento y las
    #     primeras quedarían en blanco;
    # (b) la tabla NO puede ser el mismo objeto para todas: `aplanar_rip` limpia los huérfanos
    #     página por página, y con una tabla compartida la limpieza de la primera se lleva los
    #     dibujos que usan las otras. Los STREAMS sí se comparten (que es donde está el peso):
    #     lo que se duplica es la lista de nombres, unos bytes.
    for pg, usados in por_pagina:
        pg.obj["/Resources"] = pikepdf.Dictionary(
            {"/XObject": pikepdf.Dictionary({n: xobjs[n] for n in sorted(usados)})})
    # Sin comprimir: el aplanado para el RIP la vuelve a escribir (y ahí sí comprime).
    pdf.save(path_salida, compress_streams=False)
    pdf.close()
    for d in abiertos:
        try:
            d.close()
        except Exception:
            pass
    return consumo_cm, alturas_cm
