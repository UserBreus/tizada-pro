// node frontend/src/motor/pruebas/dxf.mjs <molde.dxf> <salida.pdf> <resumen.json>
// El importador de DXF del motor del navegador (`motor/dxf/importar.js`): el PDF con una capa por
// talle y el resumen. Lo compara `verificar_navegador_dxf.py` contra `importar_dxf.dxf_a_pdf`.
import fs from 'node:fs'
import * as mupdf from 'mupdf'
import { dxfAPdf } from '../dxf/importar.js'

const [, , entrada, salidaPdf, salidaJson] = process.argv
const t0 = performance.now()
const r = dxfAPdf(mupdf, fs.readFileSync(entrada))
fs.writeFileSync(salidaPdf, r.pdf)
fs.writeFileSync(salidaJson, JSON.stringify({ ...r.resumen, _omitidas: r.omitidas, _segundos: (performance.now() - t0) / 1000 }))
