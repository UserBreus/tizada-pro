// node frontend/src/motor/pruebas/desplegar.mjs <molde.ai> <carpeta_salida>
// El molde desplegado ENTERO por el motor del navegador, escrito como lo deja el servidor:
// m{mesa}.json, m{mesa}.pdf, etiqueta_archivo.json y alta.json. Lo compara
// `verificar_navegador_desplegado.py`.
import fs from 'node:fs'
import path from 'node:path'
import * as mupdf from 'mupdf'
import { desplegarMolde } from '../molde/desplegar.js'
import { aJSON } from '../molde/contornos.js'

const [, , entrada, carpeta] = process.argv
fs.mkdirSync(carpeta, { recursive: true })
const t0 = performance.now()
const doc = mupdf.Document.openDocument(fs.readFileSync(entrada), 'application/pdf')
const tiempos = {}
let ultimo = performance.now()
const r = desplegarMolde(mupdf, doc, {
  avisar: (etapa) => { const t = performance.now(); tiempos[etapa] = (tiempos[etapa] || 0) + (t - ultimo) / 1000; ultimo = t },
})
for (const [m, { json, pdf }] of r.mesas) {
  fs.writeFileSync(path.join(carpeta, `m${m}.json`), JSON.stringify(aJSON(json)))
  if (pdf) fs.writeFileSync(path.join(carpeta, `m${m}.pdf`), pdf)
}
if (r.etiqueta) fs.writeFileSync(path.join(carpeta, 'etiqueta_archivo.json'), JSON.stringify(aJSON(r.etiqueta)))
fs.writeFileSync(path.join(carpeta, 'alta.json'), JSON.stringify(aJSON(r.alta)))
fs.writeFileSync(path.join(carpeta, 'tiempos.json'), JSON.stringify({ total: (performance.now() - t0) / 1000, ...tiempos,
  memoria_mb: process.memoryUsage().rss / 1048576 }))
