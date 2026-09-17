// node frontend/src/motor/pruebas/parece.mjs <molde.ai>
// ¿Trae el diseño adentro? La decisión del motor del navegador, para compararla con
// `piezas_con_diseno.parece_molde_con_diseno` (lo hace `verificar_navegador_molde.py`).
import fs from 'node:fs'
import * as mupdf from 'mupdf'
import { dibujosDePagina } from '../pdf/dibujos.js'
import { geometriaPagina, conteoConDiseno, decidirConDiseno } from '../molde/contornos.js'

const doc = mupdf.Document.openDocument(fs.readFileSync(process.argv[2]), 'application/pdf')
const total = { clips: 0, pintados: 0 }
for (let m = 0; m < Math.min(doc.countPages(), 2); m++) {
  const page = doc.loadPage(m)
  const c = conteoConDiseno(dibujosDePagina(mupdf, page, { ligero: true }), geometriaPagina(page))
  page.destroy()
  total.clips += c.clips
  total.pintados += c.pintados
}
console.log(JSON.stringify(decidirConDiseno(total)))
