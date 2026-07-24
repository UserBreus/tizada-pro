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
import re
import fitz


def _generico(nombre):
    """Nombre de la pieza SIN el número final: «Frente 1» → «Frente». En la ficha se muestra el
    nombre general de la pieza, no el número de instancia."""
    return re.sub(r"\s+\d+\s*$", "", str(nombre or "")).strip() or str(nombre or "")

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
def _dibujar_tabla(page, y, columnas, filas, y_max, fila0=0):
    """Dibuja tantas filas como entren desde `y` hasta `y_max`. Devuelve (y_final, filas_restantes,
    fila0_siguiente). La 1ª columna es «#» con el NÚMERO DE FILA (estilo columna de títulos), para
    identificar cada fila. `fila0` = índice de la 1ª fila de esta página (continúa la numeración)."""
    if not columnas:
        return y, [], fila0
    x0, x1 = MARGEN, A4_W - MARGEN
    W_NUM = 28                                    # ancho de la columna de números
    w_col = (x1 - x0 - W_NUM) / len(columnas)     # el resto se reparte entre las columnas reales
    alto_fila = 18

    def _cx(i):                                   # x de la columna i (0 = la de números)
        return x0 if i == 0 else x0 + W_NUM + (i - 1) * w_col

    def _cw(i):
        return W_NUM if i == 0 else w_col

    # cabecera (incluye el «#»)
    page.draw_rect(fitz.Rect(x0, y, x1, y + alto_fila), fill=(0.13, 0.15, 0.17), color=None)
    _texto(page, x0 + 7, y + 12, "#", size=8, bold=True, color=(1, 1, 1))
    for i, c in enumerate(columnas):
        _texto(page, _cx(i + 1) + 6, y + 12, (c.get("label") or c.get("id") or "").upper(),
               size=8, bold=True, color=(1, 1, 1), max_w=w_col - 10)
    y += alto_fila
    restantes = []
    dibujadas = 0
    for r, fila in enumerate(filas):
        if y + alto_fila > y_max:
            restantes = filas[r:]
            break
        if r % 2:
            page.draw_rect(fitz.Rect(x0 + W_NUM, y, x1, y + alto_fila), fill=(0.96, 0.97, 0.98), color=None)
        # celda de número: fondo distinguido (como columna de títulos) + el número de fila
        page.draw_rect(fitz.Rect(x0, y, x0 + W_NUM, y + alto_fila), fill=(0.90, 0.92, 0.94), color=None)
        _texto(page, x0 + 7, y + 12, str(fila0 + r + 1), size=8, bold=True, color=(0.25, 0.28, 0.32))
        for i, c in enumerate(columnas):
            val = fila.get(c.get("id"), fila.get(c.get("label"), ""))
            _texto(page, _cx(i + 1) + 6, y + 12, val, size=8.5, color=NEGRO, max_w=w_col - 10)
        y += alto_fila
        dibujadas += 1
    top = y - alto_fila * dibujadas - alto_fila    # borde superior de la cabecera
    for i in range(len(columnas) + 2):             # líneas verticales (incluye la del «#»)
        xx = _cx(i) if i <= len(columnas) else x1
        page.draw_line(fitz.Point(xx, top), fitz.Point(xx, y), color=LINEA, width=0.6)
    page.draw_rect(fitz.Rect(x0, top, x1, y), color=LINEA, width=0.8)
    return y, restantes, fila0 + dibujadas


# ── MOLDE GUÍA (piezas de la variable, con el diseño recortado — el MISMO PDF que la tizada) ───
def _dibujar_piezas(doc, page, y, piezas, y_max, cols=5):
    """Coloca las piezas en una grilla de `cols` columnas; devuelve (y_final, restantes). Cada pieza
    va en su propia TARJETA (sombra suave + fondo claro + borde) para que cada espacio se distinga;
    adentro, el PDF real de la pieza (recorte NATIVO → el diseño queda dentro de la silueta).
    Cada pieza es {nombre, w_cm, h_cm, pdf(bytes)}."""
    x0 = MARGEN
    ancho = A4_W - 2 * MARGEN
    w_cel = ancho / cols
    gap = 5                              # aire entre tarjetas
    h_cel = 132                          # alto de la celda (tarjeta + rótulo)
    h_card = h_cel - 18                  # alto de la tarjeta (la imagen); el rótulo es sólo el nombre
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
            card = fitz.Rect(cx + gap, fila_y + gap, cx + w_cel - gap, fila_y + gap + h_card)
            # SOMBRA suave: una tarjeta gris apenas corrida atrás → da relieve sin ser agresiva.
            page.draw_rect(fitz.Rect(card.x0 + 1.6, card.y0 + 2.0, card.x1 + 1.6, card.y1 + 2.0),
                           color=None, fill=(0.86, 0.87, 0.88))
            # TARJETA: fondo casi blanco + borde fino.
            page.draw_rect(card, color=(0.80, 0.82, 0.84), width=0.8, fill=(0.985, 0.99, 0.995))
            src = None
            try:
                src = fitz.open("pdf", pz.get("pdf"))
                r0 = src[0].rect
                pad = 7
                dispo_w, dispo_h = card.width - 2 * pad, card.height - 2 * pad
                esc = min(dispo_w / r0.width, dispo_h / r0.height) if r0.width and r0.height else 1
                aw, ah = r0.width * esc, r0.height * esc
                dst = fitz.Rect(card.x0 + (card.width - aw) / 2, card.y0 + (card.height - ah) / 2,
                                card.x0 + (card.width + aw) / 2, card.y0 + (card.height + ah) / 2)
                page.show_pdf_page(dst, src, 0)
            except Exception:
                pass
            finally:
                if src is not None:
                    src.close()
            # Sólo el NOMBRE general de la pieza (sin número). La MEDIDA no se muestra: no se necesita.
            nom = _generico(pz.get("nombre") or "—")
            _texto(page, cx + gap + 2, fila_y + h_card + 13, nom, size=7.5, bold=True, color=NEGRO, max_w=w_cel - 2 * gap - 2)
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

    # 1) TABLA (arriba). Puede ocupar más de una página si hay muchas filas (la numeración sigue).
    pg = nueva_pagina()
    y = _seccion(pg, 78, "TABLA DE TALLES")
    y += 6
    y, restan, _f0 = _dibujar_tabla(pg, y, columnas, filas, A4_H - MARGEN)
    while restan:
        pg = nueva_pagina()
        y = _seccion(pg, 78, "TABLA DE TALLES (continuación)")
        y += 6
        y, restan, _f0 = _dibujar_tabla(pg, y, columnas, restan, A4_H - MARGEN, fila0=_f0)

    # 2) MOLDE GUÍA (abajo — sigue en la misma página si entra, si no, página nueva).
    #    El encabezado dice el DISEÑO (para distinguir si hay más de uno), NO el talle: es sólo una guía.
    for mg in (moldes_guia or []):
        piezas = mg.get("piezas") or []
        titulo_mg = f"MOLDE GUÍA · {mg.get('nombre', '')}" + (f"  ·  {mg.get('diseno')}" if mg.get("diseno") else "")
        if y + 200 > A4_H - MARGEN:        # no entra ni el título + una fila → página nueva
            pg = nueva_pagina(); y = 78
        else:
            y += 24
        y = _seccion(pg, y, titulo_mg)
        y += 10
        y, rest = _dibujar_piezas(doc, pg, y, piezas, A4_H - MARGEN)
        while rest:
            pg = nueva_pagina(); y = 78
            y = _seccion(pg, y, titulo_mg + " (continuación)")
            y += 10
            y, rest = _dibujar_piezas(doc, pg, y, rest, A4_H - MARGEN)

    total = doc.page_count
    for i, pg in enumerate(doc):
        _encabezado(pg, titulo, subtitulo, i + 1, total)

    ruta = os.path.join(salida, nombre_archivo)
    doc.save(ruta, garbage=3, deflate=True)
    doc.close()
    return ruta
