// node frontend/src/motor/pruebas/editar_piezas.mjs <molde.ai> <ediciones.json> <salida.ai> <resultado.json>
// EDITAR PIEZAS (MAPA 746) en el motor del navegador: aplica las ediciones (`editarPiezas`), vuelve a
// leer el molde y verifica que SÓLO cambió lo pedido (`verificarEdicion`). Lo usa el contrato
// `verificar_editar_piezas.py`, que compara contra el gemelo de Python (`piezas_molde.editar_piezas`).
// Sólo LEE el molde de entrada; escribe la versión nueva donde se le dice.
import fs from 'node:fs'
import * as mupdf from 'mupdf'
import * as CA from '../molde/caminoA.js'
import { detectarPorTalle } from '../molde/herramientas.js'
import { editarPiezas, verificarEdicion } from '../molde/editarPiezas.js'

const [, , entrada, edJson, salida, resJson] = process.argv
const { ediciones, esperado, mesa = 1 } = JSON.parse(fs.readFileSync(edJson, 'utf8'))
const bytes = new Uint8Array(fs.readFileSync(entrada))
const abrir = (b) => new CA.MoldeA(mupdf, mupdf.Document.openDocument(b, 'application/pdf'))
const m0 = abrir(bytes.slice())
const talles = CA.tallesDePlantilla(m0)
const antes = detectarPorTalle(m0, mesa, talles)
const t0 = performance.now()
let out
try {
  const r = editarPiezas(mupdf, bytes.slice(), ediciones, mesa)
  const m1 = abrir(r.bytes.slice())
  const despues = detectarPorTalle(m1, mesa, talles)
  const mal = verificarEdicion(antes, despues, esperado || [])
  fs.writeFileSync(salida, r.bytes)
  out = { ok: !mal.length, mal, segundos: (performance.now() - t0) / 1000,
          despues: Object.fromEntries(Object.entries(despues).map(([t, cs]) => [t, cs.map((c) => c.bbox_raw)])) }
} catch (e) {
  out = { ok: false, error: String(e.message || e) }
}
fs.writeFileSync(resJson, JSON.stringify(out))
console.log(JSON.stringify({ ok: out.ok, mal: out.mal, error: out.error, segundos: out.segundos }))
