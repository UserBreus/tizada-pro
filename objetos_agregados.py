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


def inyectar_editable(arte_path, mesa, pdf_obj, nombre, rect):
    """Agrega el objeto al ARTE como una CAPA OCG llamada `Editable <nombre>`, dentro de la mesa
    indicada. A partir de acá el objeto **ES** un editable del arte: lo detecta `extraer_editables`
    y todo el sistema (editor, visor del Arte, motor, tizada) lo trata igual, sin código especial.

    Esto es lo que hace que el editor sea un espacio de edición REAL sobre el diseño y no una capa
    visual encima — como trabajar dentro de Illustrator.

    `mesa`  = número de mesa (página) del arte, 1-based, la de la pieza para ese rango.
    `rect`  = (x0, y0, x1, y1) en coordenadas de la página (y hacia ARRIBA), dónde va el objeto.
    Devuelve el nombre de la capa creada.
    """
    import pikepdf
    from pikepdf import Name, Dictionary, Array, String

    capa = f"Editable {nombre}".strip()
    pdf = pikepdf.open(arte_path, allow_overwriting_input=True)
    try:
        page = pdf.pages[int(mesa) - 1]
        with pikepdf.open(io.BytesIO(pdf_obj)) as src:
            xo = pdf.copy_foreign(src.pages[0].as_form_xobject())

        # 1) la CAPA (OCG) + su registro en el catálogo, o el visor no la reconoce como capa
        ocg = pdf.make_indirect(Dictionary(Type=Name.OCG, Name=String(capa),
                                           Intent=Array([Name.View, Name.Design])))
        ocp = pdf.Root.get("/OCProperties")
        if ocp is None:
            ocp = pdf.Root["/OCProperties"] = Dictionary(OCGs=Array([]), D=Dictionary(ON=Array([]), Order=Array([])))
        ocp["/OCGs"].append(ocg)
        d = ocp.get("/D")
        if d is None:
            d = ocp["/D"] = Dictionary(ON=Array([]), Order=Array([]))
        if "/ON" not in d:
            d["/ON"] = Array([])
        d["/ON"].append(ocg)
        if "/Order" not in d:
            d["/Order"] = Array([])
        d["/Order"].append(ocg)

        # 2) recursos de la página: el XObject y la propiedad que apunta a la capa
        xname = page.add_resource(xo, Name.XObject, prefix="OA")
        pname = page.add_resource(ocg, Name.Properties, prefix="OC")

        # 3) matriz que lleva la BBox del objeto al rect pedido (sin deformar: se respeta lo que
        #    manda quien llama, que ya calculó el rect con la proporción real)
        bx = [float(v) for v in xo.BBox]
        M = [float(v) for v in xo.Matrix] if "/Matrix" in xo else [1, 0, 0, 1, 0, 0]
        a, b, c, dd, e, f = M
        xs, ys = [], []
        for (px, py) in ((bx[0], bx[1]), (bx[2], bx[1]), (bx[2], bx[3]), (bx[0], bx[3])):
            xs.append(a * px + c * py + e); ys.append(b * px + dd * py + f)
        ox0, ox1, oy0, oy1 = min(xs), max(xs), min(ys), max(ys)
        rx0, ry0, rx1, ry1 = [float(v) for v in rect]
        sx = (rx1 - rx0) / (ox1 - ox0) if ox1 != ox0 else 1.0
        sy = (ry1 - ry0) / (oy1 - oy0) if oy1 != oy0 else 1.0
        tx, ty = rx0 - sx * ox0, ry0 - sy * oy0

        # 4) al content stream, DENTRO de la capa (BDC/EMC): así el objeto pertenece a la capa y
        #    se puede aislar/ocultar como cualquier otra del arte.
        page.contents_add(
            pikepdf.Stream(pdf, f"\nq /OC {pname} BDC\n{sx:.6f} 0 0 {sy:.6f} {tx:.3f} {ty:.3f} cm\n{xname} Do\nEMC Q\n".encode()),
            prepend=False)
        pdf.save()
    finally:
        pdf.close()
    return capa


def carpeta(datos_dir, pid, sub=None):
    d = os.path.join(datos_dir, "productos", pid, "objetos_agregados")
    if sub:
        d = os.path.join(d, sub)
    os.makedirs(d, exist_ok=True)
    return d
