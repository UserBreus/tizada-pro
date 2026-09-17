// node frontend/src/motor/pruebas/render.mjs <molde.ai> <mesa> <escala> <salida.raw> [icc]
// Rasteriza UNA mesa con mupdf.js (RGB, sin alfa) y escribe los píxeles crudos + "<ancho> <alto>"
// en la primera línea de <salida.raw>.txt. Lo compara `verificar_navegador_render.py` contra
// `page.get_pixmap` de PyMuPDF.
import fs from 'node:fs'
import * as mupdf from 'mupdf'

const [, , entrada, mesa, escala, salida, icc] = process.argv
if (icc === '1') mupdf.enableICC(); else if (icc === '0') mupdf.disableICC()
const doc = mupdf.Document.openDocument(fs.readFileSync(entrada), 'application/pdf')
const page = doc.loadPage(Number(mesa) - 1)
const t = performance.now()
const s = Number(escala)
const pix = page.toPixmap(mupdf.Matrix.scale(s, s), mupdf.ColorSpace.DeviceRGB, false, true)
const seg = (performance.now() - t) / 1000
fs.writeFileSync(salida, pix.getPixels())
fs.writeFileSync(salida + '.txt', `${pix.getWidth()} ${pix.getHeight()} ${seg}`)
