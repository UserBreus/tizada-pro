// node frontend/src/motor/pruebas/dibujos.mjs <molde.ai> <carpeta_salida>
// Escribe lo que ve mupdf.js (traducción de get_cdrawings) para compararlo con PyMuPDF
// (`verificar_navegador_dibujos.py`). Corre en Node: el mismo código que el navegador.
// Una línea JSON por dibujo (`m<mesa>.ndjson`): el molde de 117 MB son cientos de miles de
// dibujos y un solo JSON pasaría el tope de largo de texto de V8.
import fs from 'node:fs'
import path from 'node:path'
import * as mupdf from 'mupdf'
import { dibujosDePagina } from '../pdf/dibujos.js'

const [, , entrada, carpeta] = process.argv
fs.mkdirSync(carpeta, { recursive: true })
const t0 = performance.now()
const bytes = fs.readFileSync(entrada)
const doc = mupdf.Document.openDocument(bytes, 'application/pdf')
const abrir = (performance.now() - t0) / 1000
const mesas = []
let pico = 0
for (let i = 0; i < doc.countPages(); i++) {
  const t = performance.now()
  const page = doc.loadPage(i)
  const dibujos = dibujosDePagina(mupdf, page)
  const seg = (performance.now() - t) / 1000
  pico = Math.max(pico, process.memoryUsage().rss)
  const fd = fs.openSync(path.join(carpeta, `m${i + 1}.ndjson`), 'w')
  let buf = []
  for (const d of dibujos) {
    buf.push(JSON.stringify(d))
    if (buf.length >= 5000) { fs.writeSync(fd, buf.join('\n') + '\n'); buf = [] }
  }
  if (buf.length) fs.writeSync(fd, buf.join('\n') + '\n')
  fs.closeSync(fd)
  mesas.push({ mesa: i + 1, rect: [...page.getBounds()], segundos: seg, n: dibujos.length })
  page.destroy()
}
const capas = []
for (let i = 0; i < doc.countLayers(); i++) capas.push(doc.getLayerName(i))
doc.destroy()
fs.writeFileSync(path.join(carpeta, 'resumen.json'), JSON.stringify({ mesas, capas, abrir,
  segundos: mesas.reduce((a, m) => a + m.segundos, 0) + abrir, memoria_mb: pico / 1048576 }))
console.log(`${mesas.length} mesa(s), ${mesas.reduce((a, m) => a + m.n, 0)} dibujos`)
