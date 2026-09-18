// node frontend/src/motor/pruebas/vista.mjs <archivo.pdf> <pagina1> <ancho> <salida.png> [cx0 cy0 cx1 cy1]
// Dibuja una mesa (o un recorte) con el motor del navegador y guarda el PNG.
// Lo compara `verificar_navegador_vista.py` contra el dibujo del servidor (`_dibujar_vista_mesa`).
import fs from 'node:fs'
import * as mupdf from 'mupdf'
import { dibujarMesa } from '../vista/dibujar.js'
import { prepararReplay, dibujarConReplay } from '../vista/replay.js'

// `--replay` al final: dibuja con `vista/replay.js` (lo que usa el visor), para compararlo con el exacto.
const argv = process.argv.slice(2)
const usarReplay = argv[argv.length - 1] === '--replay'
if (usarReplay) argv.pop()
const [entrada, pagina, ancho, salida, ...rec] = argv
mupdf.enableICC()
const doc = mupdf.Document.openDocument(fs.readFileSync(entrada), 'application/pdf')
const recorte = rec.length === 4 ? rec.map(Number) : null
const t = performance.now()
let res
if (usarReplay) {
  const prep = prepararReplay(mupdf, doc, Number(pagina) - 1)
  if (!prep) { console.log(JSON.stringify({ error: 'esta página no se puede repetir' })); process.exit(2) }
  res = dibujarConReplay(mupdf, doc, Number(pagina) - 1, prep, { ancho: Number(ancho), recorte })
} else {
  res = dibujarMesa(mupdf, doc, Number(pagina) - 1, { ancho: Number(ancho), recorte })
}
const { png, w, h } = res
const seg = (performance.now() - t) / 1000
fs.writeFileSync(salida, png)
console.log(JSON.stringify({ w, h, segundos: seg }))
