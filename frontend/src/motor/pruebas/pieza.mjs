// node frontend/src/motor/pruebas/pieza.mjs <fixture.json> <salida.json> [carpeta_pdfs]
// Arma con el motor del navegador la BASE y el ESTAMPADO de cada pieza del fixture (camino B) y
// escribe los operadores; con `carpeta_pdfs`, también el PDF de cada pieza (para compararlos
// dibujados). Lo compara `verificar_navegador_pieza.py` contra `motor_pedido.generar_pedido`.
import fs from 'node:fs'
import path from 'node:path'
import * as mupdf from 'mupdf'
import { armarBase, documentoPieza } from '../pieza/base.js'
import { estamparPieza } from '../pieza/estampar.js'
import { crearAbridor } from '../texto/fuentes.js'

const [, , fixture, salida, carpetaPdfs] = process.argv
const F = JSON.parse(fs.readFileSync(fixture, 'utf-8'))

let FuenteCurvas = null
try { FuenteCurvas = (await import('../texto/curvas.js')).FuenteCurvas } catch { FuenteCurvas = null }

const docs = new Map()          // mesa → PDFDocument de m{mesa}.pdf
const indices = new Map()       // mesa → m{mesa}.json
const abrirMesa = (mesa) => {
  if (!docs.has(mesa)) {
    docs.set(mesa, mupdf.Document.openDocument(fs.readFileSync(path.join(F.desplegado, `m${mesa}.pdf`)), 'application/pdf'))
    indices.set(mesa, JSON.parse(fs.readFileSync(path.join(F.desplegado, `m${mesa}.json`), 'utf-8')))
  }
  return [docs.get(mesa), indices.get(mesa)]
}

let abridor = null
if (FuenteCurvas) {
  abridor = crearAbridor({
    catalogo: F.catalogo, alias: F.alias || {}, FuenteCurvas,
    traer: async (e) => new Uint8Array(fs.readFileSync(e.ruta)),
  })
  const nombres = new Set(['Arial-BoldMT'])
  for (const m of Object.values(F.pers || {})) for (const c of Object.values(m)) if (c.fuente) nombres.add(c.fuente)
  await abridor.precargar([...nombres])
}

const out = []
for (const p of F.piezas) {
  const [doc, idx] = abrirMesa(p.mesa)
  const conts = idx.talles[p.talle] || []
  const cont = conts[p.idx_mesa]
  // la escala del XObject = el /UserUnit de la página desplegada (lo que pikepdf pone en /Matrix)
  const pageObj = doc.findPage(p.pagina)
  const uu = pageObj.get('UserUnit')
  const S = (uu && uu.isNumber && uu.isNumber()) ? Number(uu.asNumber()) : 1.0
  const base = armarBase(cont, S, F.borde)
  let estampado = null
  if (abridor) {
    estampado = estamparPieza({
      base, ph: (F.pers || {})[String(p.mesa)] || {}, persona: p.persona, talle: p.talle, pieza: p.pieza,
      nro: p.nro, variante: p.variante || null, grupo: p.grupo || null, etiqueta: F.etiqueta,
      fuente: abridor.abrir, alias: F.alias || {}, info: p.info || {},
    })
  }
  const r = { pieza: p.pieza, talle: p.talle, base_stream: base.baseStream, clip: base.clip, estampado,
              W: base.W, H: base.H, B: base.B, S }
  if (carpetaPdfs) {
    const bytes = documentoPieza(mupdf, doc, p.pagina, base, estampado || '')
    r.pdf = path.join(carpetaPdfs, `nav_${out.length}.pdf`)
    fs.writeFileSync(r.pdf, bytes)
  }
  out.push(r)
}
fs.writeFileSync(salida, JSON.stringify({ con_fuentes: !!FuenteCurvas, piezas: out }))
