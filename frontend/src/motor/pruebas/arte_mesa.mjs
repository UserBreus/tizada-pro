// node frontend/src/motor/pruebas/arte_mesa.mjs <arte.ai> <carpeta_salida>
// Escribe cada mesa del arte como SVG con las capas «guías» y «Editable …» apagadas, igual que la
// tarea `arte_svg` del hilo de trabajo (lo compara `verificar_navegador_arte_mesa.py` con
// `/api/arte/mesa_img`).
import fs from 'node:fs'
import path from 'node:path'
import * as mupdf from 'mupdf'
import { svgDePagina } from '../pieza/svg.js'
import { apagarCapasNoImpresas } from '../arte/capas.js'

const [, , arte, salida] = process.argv
fs.mkdirSync(salida, { recursive: true })
const doc = mupdf.Document.openDocument(fs.readFileSync(arte), 'application/pdf')
const apagadas = apagarCapasNoImpresas(doc)
for (let p = 0; p < doc.countPages(); p++) fs.writeFileSync(path.join(salida, `${p + 1}.svg`), svgDePagina(mupdf, doc, p))
console.log(JSON.stringify({ mesas: doc.countPages(), apagadas }))
