// node frontend/src/motor/pruebas/vista.mjs <archivo.pdf> <pagina1> <ancho> <salida.png> [cx0 cy0 cx1 cy1]
// Dibuja una mesa (o un recorte) con el motor del navegador y guarda el PNG.
// Lo compara `verificar_navegador_vista.py` contra el dibujo del servidor (`_dibujar_vista_mesa`).
import fs from 'node:fs'
import * as mupdf from 'mupdf'
import { dibujarMesa } from '../vista/dibujar.js'

const [, , entrada, pagina, ancho, salida, ...rec] = process.argv
mupdf.enableICC()
const doc = mupdf.Document.openDocument(fs.readFileSync(entrada), 'application/pdf')
const recorte = rec.length === 4 ? rec.map(Number) : null
const t = performance.now()
const { png, w, h } = dibujarMesa(mupdf, doc, Number(pagina) - 1, { ancho: Number(ancho), recorte })
const seg = (performance.now() - t) / 1000
fs.writeFileSync(salida, png)
console.log(JSON.stringify({ w, h, segundos: seg }))
