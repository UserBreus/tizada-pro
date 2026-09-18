// DIBUJAR UNA MESA (O UN RECORTE) EN EL NAVEGADOR — PLAN_NAVEGADOR.md, etapa 2.
//
// Es la traducción de `servidor._dibujar_vista_mesa`: misma lista de dibujo, mismo recorte, misma
// escala, mismo PNG. Lo que hoy hace el pool del visor del servidor (DisplayList → get_pixmap →
// PNG) lo hace acá la computadora de quien mira.
//
// 🔴 POR QUÉ CON LISTA DE DIBUJO Y NO `page.toPixmap`: `toPixmap` no sabe de recortes, y el visor
// pide justo eso (el pedazo que se está mirando, nítido). Con la lista se puede dibujar cualquier
// rectángulo de la página, que es lo que hace PyMuPDF por dentro con `clip=`.

/** El rectángulo de la página, como lo devuelve `page.getBounds()` → `[x0, y0, x1, y1]`. */
export function rectoDePagina(page) {
  const b = page.getBounds()
  return [b[0], b[1], b[2], b[3]]
}

/**
 * El recorte en coordenadas de la página, a partir de las fracciones `{cx0, cy0, cx1, cy1}` que
 * usa la pantalla (0..1 sobre el ancho y el alto de la mesa). Sin recorte o con (0,0,1,1) va la
 * mesa entera. Idéntico a `_dibujar_vista_mesa`.
 */
export function recorteDeFracciones(r, recorte) {
  if (!recorte) return null
  const [cx0, cy0, cx1, cy1] = recorte
  if (cx0 === 0 && cy0 === 0 && cx1 === 1 && cy1 === 1) return null
  const an = r[2] - r[0], al = r[3] - r[1]
  return [r[0] + an * cx0, r[1] + al * cy0, r[0] + an * cx1, r[1] + al * cy1]
}

/**
 * El `fz_irect` de un rectángulo escalado. Es `fz_round_rect` de MuPDF: hacia afuera, pero con un
 * margen de 0,001 para que el ruido del float no agregue una fila de más.
 * 🔴 Sin ese margen, una hoja de 8 m salía 5328 px de alto donde el servidor la hace de 5327.
 */
export function aEntero(r) {
  const f = Math.fround
  return [Math.floor(f(r[0]) + 0.001), Math.floor(f(r[1]) + 0.001),
          Math.ceil(f(r[2]) - 0.001), Math.ceil(f(r[3]) - 0.001)]
}

/**
 * Dibuja la página `pagina` (0 = la primera) de `doc` a PNG.
 *   · `ancho`   — el ancho final en píxeles (de la mesa entera o del recorte, como el servidor);
 *   · `recorte` — `[cx0, cy0, cx1, cy1]` en fracciones, o `null` para la mesa entera;
 *   · `lista`   — una lista de dibujo ya armada (se reusa entre recortes de la misma mesa).
 * Devuelve `{png: Uint8Array, w, h}`.
 */
export function dibujarMesa(mupdf, doc, pagina, { ancho = 1200, recorte = null, lista = null } = {}) {
  const page = doc.loadPage(pagina)
  const r = rectoDePagina(page)
  const dl = lista || page.toDisplayList(true)
  const clip = recorteDeFracciones(r, recorte)
  const anchoPt = ((clip ? clip[2] - clip[0] : r[2] - r[0]) || 1.0)
  const z = ancho / anchoPt
  const m = mupdf.Matrix.scale(z, z)
  // El rectángulo a dibujar, ya escalado y redondeado a píxeles enteros (lo que PyMuPDF llama
  // `irect`): si no se redondea igual, la imagen sale corrida medio píxel y no coincide.
  const caja = aEntero(mupdf.Rect.transform(clip || r, m))
  const pix = new mupdf.Pixmap(mupdf.ColorSpace.DeviceRGB, caja, false)
  pix.clear(255)
  const dev = new mupdf.DrawDevice(mupdf.Matrix.identity, pix)
  try {
    dl.run(dev, m)
  } finally {
    dev.close()
  }
  const png = pix.asPNG()
  const w = pix.getWidth(), h = pix.getHeight()
  pix.destroy()
  if (!lista) dl.destroy()
  page.destroy()
  return { png, w, h }
}
