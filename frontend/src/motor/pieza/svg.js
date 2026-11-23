// UNA PÁGINA COMO SVG — lo que `page.get_svg_image()` de PyMuPDF hace en el servidor para la vista
// previa de cada pieza (`_svg_worker`). Es el mismo escritor SVG de MuPDF: medido sobre una hoja
// real de 313 MB de SVG, la única diferencia es que los `id` de los clipPath arrancan en 0 en vez
// de 1 (PyMuPDF ya venía contando). El texto sale como trazado (`text=path`), como allá.
//
// 🔴 LOS DEGRADADOS SALEN VECTORIALES (2026-10-01, MAPA 605): el escritor de MuPDF dibujaba cada
// `sh` como una imagen PNG del tamaño de lo que recorta (8-12 s por mesa con un arte de 11
// degradados, y un píxel en pantalla). `pdf/degradados.js` los cambia por un relleno marcador
// antes de escribir y por un `linearGradient`/`radialGradient` después. Si algo no cierra, se
// dibuja como antes (lento pero igual de correcto). TODO SVG de este sistema sale por acá.
import { marcarDegradados } from '../pdf/degradados.js'

function escribirSvg(mupdf, doc, pagina, recorte) {
  const page = doc.loadPage(pagina)
  const buf = new mupdf.Buffer()
  const w = new mupdf.DocumentWriter(buf, 'svg', 'text=path')
  let dev = null
  try {
    if (recorte) {
      dev = w.beginPage([0, 0, recorte[2], recorte[3]])
      page.run(dev, mupdf.Matrix.translate(-recorte[0], -recorte[1]))
    } else {
      dev = w.beginPage(page.getBounds())
      page.run(dev, mupdf.Matrix.identity)
    }
    w.endPage()
  } finally {
    w.close()
    // 🔴 EL ESCRITOR Y SU DISPOSITIVO SE SUELTAN ACÁ (MAPA 814). El escritor guarda su propia referencia
    // al buffer del SVG: sin `destroy()`, el SVG entero quedaba en la memoria del motor hasta que el
    // navegador recolectara el objeto. Con una imagen de 120 MB cada vista previa es un SVG de 112 MB:
    // medido, la 3ª en el mismo hilo llenaba los 2 GB («malloc failed») y la tizada ya no tenía lugar.
    if (dev) { try { dev.destroy() } catch { /* nada */ } }
    try { w.destroy() } catch { /* nada */ }
    page.destroy()
  }
  let s
  try { s = buf.asString() } finally { buf.destroy() }
  return s
}

/**
 * El SVG (texto) de la página `pagina` (0 = la primera) de `doc`. Con `recorte` `[x0, y0, ancho,
 * alto]` (coordenadas de la página, y hacia abajo) sale sólo esa parte, con el origen en su esquina.
 */
export function svgDePagina(mupdf, doc, pagina, recorte = null) {
  let marcas = null
  try { marcas = marcarDegradados(mupdf, doc, pagina) } catch { marcas = null }
  if (!marcas) return escribirSvg(mupdf, doc, pagina, recorte)
  let s
  try { s = escribirSvg(mupdf, doc, pagina, recorte) } finally { marcas.deshacer() }
  let listo = null
  try { listo = marcas.aplicar(s) } catch { listo = null }
  // no cerró la cuenta de marcadores: se dibuja por el camino de siempre (el documento ya volvió)
  return listo === null ? escribirSvg(mupdf, doc, pagina, recorte) : listo
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
