// UNA PÁGINA COMO SVG — lo que `page.get_svg_image()` de PyMuPDF hace en el servidor para la vista
// previa de cada pieza (`_svg_worker`). Es el mismo escritor SVG de MuPDF: medido sobre una hoja
// real de 313 MB de SVG, la única diferencia es que los `id` de los clipPath arrancan en 0 en vez
// de 1 (PyMuPDF ya venía contando). El texto sale como trazado (`text=path`), como allá.

/** El SVG (texto) de la página `pagina` (0 = la primera) de `doc`. */
export function svgDePagina(mupdf, doc, pagina) {
  const page = doc.loadPage(pagina)
  const buf = new mupdf.Buffer()
  const w = new mupdf.DocumentWriter(buf, 'svg', 'text=path')
  try {
    const dev = w.beginPage(page.getBounds())
    page.run(dev, mupdf.Matrix.identity)
    w.endPage()
  } finally {
    w.close()
    page.destroy()
  }
  const s = buf.asString()
  buf.destroy()
  return s
}

/** El SVG de un PDF suelto (bytes): la primera página. */
export function svgDePdf(mupdf, bytes) {
  const doc = mupdf.Document.openDocument(bytes, 'application/pdf')
  try {
    return svgDePagina(mupdf, doc, 0)
  } finally {
    doc.destroy()
  }
}
