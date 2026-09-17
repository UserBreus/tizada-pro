// node frontend/src/motor/pruebas/molde.mjs <molde.ai> <salida.json>
// El alta del camino B (sólo contornos) hecha por el motor del navegador: por mesa lo que va a
// `m{mesa}.json` (talles, marco, U) y el resultado del alta (registro, visor, resumen). Lo compara
// `verificar_navegador_molde.py` contra `piezas_con_diseno.alta_molde_con_diseno(paginas=False)`.
import fs from 'node:fs'
import * as mupdf from 'mupdf'
import { dibujosDePagina } from '../pdf/dibujos.js'
import { tallesDelMolde, geometriaPagina, contornosDeMesa, altaDesdeContornos, aJSON } from '../molde/contornos.js'

const [, , entrada, salida] = process.argv
const t0 = performance.now()
const doc = mupdf.Document.openDocument(fs.readFileSync(entrada), 'application/pdf')
const talles = tallesDelMolde(doc)
const mesas = {}
const porMesa = new Map(), geos = new Map()
const n = doc.countPages()
for (let i = 0; i < n; i++) {
  const page = doc.loadPage(i)
  const geo = geometriaPagina(page)
  geos.set(i + 1, geo)
  if (talles.length) {
    // la lectura LIGERA, como en `molde/desplegar.js` (la completa sólo si hace falta el respaldo)
    let completos = null
    const r = contornosDeMesa(dibujosDePagina(mupdf, page, { ligero: true }), geo, i + 1, talles,
      () => (completos = completos || dibujosDePagina(mupdf, page)))
    mesas[i + 1] = { orden: talles, talles: aJSON(r.talles), marco: r.marco, U: r.U }
    if (r.talles.size) porMesa.set(i + 1, r.talles)
  }
  page.destroy()
}
const alta = altaDesdeContornos(porMesa, geos, talles, n)
fs.writeFileSync(salida, JSON.stringify({ talles, mesas, alta: aJSON(alta), segundos: (performance.now() - t0) / 1000 }))
