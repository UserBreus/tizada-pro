// node frontend/src/motor/pruebas/aplanar.mjs <entrada.pdf> <salida.pdf> [total]
// Aplana una hoja para el RIP con el motor del navegador (`rip/aplanar.js`) y la guarda.
// Lo compara `verificar_navegador_aplanar.py` contra `aplanar_rip._aplanar_archivo` del servidor.
import fs from 'node:fs'
import * as mupdf from 'mupdf'
import { aplanarParaRip } from '../rip/aplanar.js'

const [, , entrada, salida, modo] = process.argv
const bytes = new Uint8Array(fs.readFileSync(entrada))
const t = performance.now()
const out = aplanarParaRip(mupdf, bytes, { total: modo === 'total' })
const seg = (performance.now() - t) / 1000
fs.writeFileSync(salida, out)
console.log(JSON.stringify({ bytes: out.length, segundos: seg }))
