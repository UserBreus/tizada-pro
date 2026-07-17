"""
OBJETOS AGREGADOS al editor de diseño — TIZADA PRO.

El usuario sube un PNG/SVG/PDF/.ai y lo agrega como un objeto editable MÁS (mover/rotar/escalar/
espejar), igual que los que vienen del arte. Para que enganche con TODO el pipeline sin inventar
un camino nuevo, cada archivo se NORMALIZA a un PDF de 1 página:

- PDF / .ai  → ya es PDF: se toma la página 0 (un .ai es un PDF con compat. Illustrator).
- SVG        → se convierte a PDF vectorial (PyMuPDF), sin perder el vector.
- PNG / JPG  → se arma una página del tamaño de la imagen con la imagen embebida.

Así un objeto agregado es "una página PDF con un tamaño en cm", que el motor puede componer con
`show_pdf_page` (vectorial exacto, misma calidad que la tizada) en la posición/rotación/escala que
el usuario le dé — idéntico a como se tratan los editables del arte.
"""
import os
import io

import fitz

PT_A_CM = 2.54 / 72.0   # puntos PDF → cm


def _es(nombre, *exts):
    return (nombre or "").lower().rsplit(".", 1)[-1] in exts


def normalizar_a_pdf(datos, filename):
    """Convierte los bytes subidos a un PDF de 1 página. Devuelve (pdf_bytes, w_cm, h_cm, tipo).
    Lanza ValueError si el formato no se soporta o el archivo está roto."""
    if _es(filename, "pdf", "ai"):
        doc = fitz.open(stream=datos, filetype="pdf")
        if doc.page_count == 0:
            raise ValueError("el PDF/AI no tiene páginas")
        # recortar a la 1ª página en un PDF nuevo (así el objeto es siempre 1 página)
        una = fitz.open()
        una.insert_pdf(doc, from_page=0, to_page=0)
        r = doc[0].rect
        out = una.tobytes()
        doc.close(); una.close()
        return out, r.width * PT_A_CM, r.height * PT_A_CM, "vector"

    if _es(filename, "svg"):
        d = fitz.open(stream=datos, filetype="svg")
        pdfb = d.convert_to_pdf()
        r = d[0].rect
        d.close()
        return pdfb, r.width * PT_A_CM, r.height * PT_A_CM, "vector"

    if _es(filename, "png", "jpg", "jpeg"):
        pix = fitz.Pixmap(io.BytesIO(datos))
        # tamaño en cm asumiendo 96 DPI (estándar web) si la imagen no trae DPI real
        dpi = 96.0
        w_cm = pix.width / dpi * 2.54
        h_cm = pix.height / dpi * 2.54
        doc = fitz.open()
        pg = doc.new_page(width=pix.width, height=pix.height)
        pg.insert_image(pg.rect, stream=datos)
        out = doc.tobytes()
        doc.close(); pix = None
        return out, w_cm, h_cm, "imagen"

    raise ValueError(f"formato no soportado: {filename} (usá PNG, SVG, PDF o .ai)")


def preview_svg(pdf_bytes):
    """SVG de la 1ª página para mostrarlo NÍTIDO en el editor (mismo criterio que el arte)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        return doc[0].get_svg_image(text_as_path=True)
    finally:
        doc.close()


def carpeta(datos_dir, pid, sub=None):
    d = os.path.join(datos_dir, "productos", pid, "objetos_agregados")
    if sub:
        d = os.path.join(d, sub)
    os.makedirs(d, exist_ok=True)
    return d
