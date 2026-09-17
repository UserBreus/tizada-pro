// node frontend/src/motor/pruebas/ficha.mjs <fixture.json> <salida.pdf>
// Arma la ficha técnica con el motor del navegador a partir de un fixture (los PDF de las piezas
// vienen en base64). Lo compara `verificar_navegador_ficha.py` contra `ficha_tecnica.generar_ficha`.
import fs from 'node:fs'
import * as mupdf from 'mupdf'
import { generarFicha } from '../ficha/ficha.js'

const [, , fixture, salida] = process.argv
const F = JSON.parse(fs.readFileSync(fixture, 'utf-8'))
const b64 = (s) => (s ? new Uint8Array(Buffer.from(s, 'base64')) : null)
for (const g of F.moldes_guia || []) {
  for (const p of g.piezas || []) p.pdf = b64(p.pdf)
  for (const pr of g.procesos || []) { if (pr.pdf) pr.pdf = b64(pr.pdf); if (pr.thumb) pr.thumb = b64(pr.thumb) }
}
const t = performance.now()
const pdf = generarFicha(mupdf, { titulo: F.titulo, subtitulo: F.subtitulo, planilla: F.planilla, moldesGuia: F.moldes_guia })
fs.writeFileSync(salida, pdf)
console.log(JSON.stringify({ bytes: pdf.length, segundos: (performance.now() - t) / 1000 }))
