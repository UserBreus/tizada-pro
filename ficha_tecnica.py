"""FICHA TÉCNICA — un PDF A4 (varias páginas si hace falta) que sale JUNTO con la tizada.

Arriba: la TABLA DE TALLES = la planilla del pedido tal cual la cargó el usuario (sus columnas y
sus filas). Abajo: el MOLDE GUÍA de un talle de referencia, con el diseño aplicado y cada pieza
nombrada, como una plantilla técnica.

Se dibuja con PyMuPDF (fitz), igual que el resto del sistema — sin dependencias nuevas. Los renders
de las piezas vienen como SVG (el MISMO que el visor y la tizada: arte = tizada) y se incrustan
VECTORIALES en la página. Es best-effort: si algo falla, la tizada igual queda (el llamador lo
envuelve en try/except).
"""
import os
import fitz

# A4 en puntos (72 dpi). Retrato.
A4_W, A4_H = 595.28, 841.89
MARGEN = 36                      # 0.5"
GRIS = (0.45, 0.45, 0.45)
NEGRO = (0.1, 0.1, 0.1)
LINEA = (0.75, 0.75, 0.75)
ACENTO = (0.0, 0.55, 0.62)
FONT = "helv"
FONT_B = "hebo"


def _texto(page, x, y, s, size=9, color=NEGRO, bold=False, max_w=None):
    """Escribe texto, recortándolo con «…» si no entra en `max_w`. Devuelve el ancho usado."""
    s = "" if s is None else str(s)
    fn = FONT_B if bold else FONT
    if max_w:
        while s and fitz.get_text_length(s, fontname=fn, fontsize=size) > max_w:
            s = s[:-1]
        if s and fitz.get_text_length(s + "…", fontname=fn, fontsize=size) <= max_w + 2 and s != str(s):
            pass
    page.insert_text((x, y), s, fontsize=size, fontname=fn, color=color)
    return fitz.get_text_length(s, fontname=fn, fontsize=size)


def _encabezado(page, titulo, subtitulo, npag, total):
    page.draw_rect(fitz.Rect(0, 0, A4_W, 54), fill=(0.97, 0.98, 0.98), color=None)
    _texto(page, MARGEN, 26, titulo, size=15, bold=True, color=NEGRO)
    if subtitulo:
        _texto(page, MARGEN, 44, subtitulo, size=9, color=GRIS)
    _texto(page, A4_W - MARGEN - 60, 44, f"Pág. {npag}/{total}", size=8, color=GRIS)
    page.draw_line(fitz.Point(MARGEN, 54), fitz.Point(A4_W - MARGEN, 54), color=ACENTO, width=1.4)


def _seccion(page, y, texto):
    _texto(page, MARGEN, y, texto, size=11, bold=True, color=ACENTO)
    return y + 8


# ── TABLA DE TALLES (la planilla del pedido tal cual) ─────────────────────────────────────────
def _dibujar_tabla(page, y, columnas, filas, y_max):
    """Dibuja tantas filas como entren desde `y` hasta `y_max`. Devuelve (y_final, filas_restantes):
    si sobran filas, el llamador abre otra página y sigue."""
    if not columnas:
        return y, []
    x0, x1 = MARGEN, A4_W - MARGEN
    ancho = x1 - x0
    w_col = ancho / len(columnas)
    alto_fila = 18
    # cabecera
    page.draw_rect(fitz.Rect(x0, y, x1, y + alto_fila), fill=(0.13, 0.15, 0.17), color=None)
    for i, c in enumerate(columnas):
        _texto(page, x0 + i * w_col + 6, y + 12, (c.get("label") or c.get("id") or "").upper(),
               size=8, bold=True, color=(1, 1, 1), max_w=w_col - 10)
    y += alto_fila
    restantes = []
    for r, fila in enumerate(filas):
        if y + alto_fila > y_max:
            restantes = filas[r:]
            break
        if r % 2:
            page.draw_rect(fitz.Rect(x0, y, x1, y + alto_fila), fill=(0.96, 0.97, 0.98), color=None)
        for i, c in enumerate(columnas):
            val = fila.get(c.get("id"), fila.get(c.get("label"), ""))
            _texto(page, x0 + i * w_col + 6, y + 12, val, size=8.5, color=NEGRO, max_w=w_col - 10)
        y += alto_fila
    # bordes verticales + marco
    for i in range(len(columnas) + 1):
        xx = x0 + i * w_col
        page.draw_line(fitz.Point(xx, (y - alto_fila * (len(filas) - len(restantes)) - alto_fila)),
                       fitz.Point(xx, y), color=LINEA, width=0.6)
    page.draw_rect(fitz.Rect(x0, y - alto_fila * (len(filas) - len(restantes)) - alto_fila, x1, y),
                   color=LINEA, width=0.8)
    return y, restantes


# ── MOLDE GUÍA (piezas del talle de referencia, con diseño y nombre) ──────────────────────────
def _svg_a_pdf(svg):
    """SVG (texto) → documento PDF de 1 página, para incrustarlo vectorial. None si falla."""
    try:
        d = fitz.open("svg", svg.encode("utf-8"))
        pdfbytes = d.convert_to_pdf()
        d.close()
        return fitz.open("pdf", pdfbytes)
    except Exception:
        return None


def _dibujar_piezas(doc, page, y, piezas, y_max, cols=3):
    """Coloca las piezas en una grilla; devuelve (y_final, restantes). Cada celda: el render de la
    pieza (escalado a caja, respetando proporción) + nombre + medida."""
    x0 = MARGEN
    ancho = A4_W - 2 * MARGEN
    w_cel = ancho / cols
    h_cel = 150                          # alto de cada celda (imagen + rótulo)
    h_img = h_cel - 26
    restantes = []
    fila_y = y
    i = 0
    while i < len(piezas):
        if fila_y + h_cel > y_max:
            restantes = piezas[i:]
            break
        for c in range(cols):
            if i >= len(piezas):
                break
            pz = piezas[i]; i += 1
            cx = x0 + c * w_cel
            caja = fitz.Rect(cx + 6, fila_y + 4, cx + w_cel - 6, fila_y + 4 + h_img)
            page.draw_rect(caja, color=(0.85, 0.85, 0.85), width=0.6, fill=(0.99, 0.99, 0.99))
            src = _svg_a_pdf(pz.get("svg") or "")
            if src is not None:
                try:
                    r0 = src[0].rect
                    esc = min((caja.width - 8) / r0.width, (caja.height - 8) / r0.height) if r0.width and r0.height else 1
                    aw, ah = r0.width * esc, r0.height * esc
                    dst = fitz.Rect(caja.x0 + (caja.width - aw) / 2, caja.y0 + (caja.height - ah) / 2,
                                    caja.x0 + (caja.width + aw) / 2, caja.y0 + (caja.height + ah) / 2)
                    page.show_pdf_page(dst, src, 0)
                except Exception:
                    pass
                finally:
                    src.close()
            nom = pz.get("nombre") or "—"
            med = f"{pz.get('w_cm', '')}×{pz.get('h_cm', '')} cm" if pz.get("w_cm") else ""
            _texto(page, cx + 8, fila_y + h_img + 16, nom, size=9, bold=True, color=NEGRO, max_w=w_cel - 16)
            if med:
                _texto(page, cx + 8, fila_y + h_img + 26, med, size=7.5, color=GRIS)
        fila_y += h_cel
    return fila_y, restantes


def generar_ficha(salida, titulo, subtitulo, planilla, moldes_guia, nombre_archivo="FICHA_TECNICA.pdf"):
    """Arma el PDF. `planilla` = {columnas:[{id,label}], filas:[{colId: valor}]}.
    `moldes_guia` = [{nombre, talle, piezas:[{nombre,w_cm,h_cm,svg}]}]. Devuelve la ruta o None."""
    doc = fitz.open()
    columnas = (planilla or {}).get("columnas") or []
    filas = (planilla or {}).get("filas") or []

    # Se arma primero la lista de "bloques" a dibujar; el nº de páginas se sabe al final, así que se
    # rellena el «Pág. x/y» en una segunda pasada.
    def nueva_pagina():
        return doc.new_page(width=A4_W, height=A4_H)

    # 1) TABLA (arriba). Puede ocupar más de una página si hay muchas filas.
    pg = nueva_pagina()
    y = _seccion(pg, 78, "TABLA DE TALLES")
    y += 6
    y, restan = _dibujar_tabla(pg, y, columnas, filas, A4_H - MARGEN)
    while restan:
        pg = nueva_pagina()
        y = _seccion(pg, 78, "TABLA DE TALLES (continuación)")
        y += 6
        y, restan = _dibujar_tabla(pg, y, columnas, restan, A4_H - MARGEN)

    # 2) MOLDE GUÍA (abajo — sigue en la misma página si entra, si no, página nueva).
    for mg in (moldes_guia or []):
        piezas = mg.get("piezas") or []
        if y + 200 > A4_H - MARGEN:        # no entra ni el título + una fila → página nueva
            pg = nueva_pagina(); y = 78
        else:
            y += 24
        y = _seccion(pg, y, f"MOLDE GUÍA · {mg.get('nombre', '')}"
                     + (f"  ·  talle {mg.get('talle')}" if mg.get("talle") else ""))
        y += 10
        y, rest = _dibujar_piezas(doc, pg, y, piezas, A4_H - MARGEN)
        while rest:
            pg = nueva_pagina(); y = 78
            y = _seccion(pg, y, f"MOLDE GUÍA · {mg.get('nombre', '')} (continuación)")
            y += 10
            y, rest = _dibujar_piezas(doc, pg, y, rest, A4_H - MARGEN)

    total = doc.page_count
    for i, pg in enumerate(doc):
        _encabezado(pg, titulo, subtitulo, i + 1, total)

    ruta = os.path.join(salida, nombre_archivo)
    doc.save(ruta, garbage=3, deflate=True)
    doc.close()
    return ruta
