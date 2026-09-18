// node frontend/src/motor/pruebas/pieza_a.mjs <fixture.json> <salida.json> [carpeta_pdfs]
// Arma con el motor del navegador la BASE y el ESTAMPADO de cada pieza del fixture (camino A: el
// arte SEPARADO, con editables, marcas de proceso y objetos agregados) y escribe los operadores;
// con `carpeta_pdfs`, también el PDF de cada pieza. Lo compara `verificar_navegador_pieza_a.py`
// contra `motor_pedido.generar_pedido`.
import fs from 'node:fs'
import path from 'node:path'
import * as mupdf from 'mupdf'
import { contextoCaminoA, documentoPiezaCaminoA } from '../pieza/caminoA.js'
import { estamparPieza } from '../pieza/estampar.js'
import { crearAbridor } from '../texto/fuentes.js'

const [, , fixture, salida, carpetaPdfs] = process.argv
const F = JSON.parse(fs.readFileSync(fixture, 'utf-8'))

let FuenteCurvas = null
try { FuenteCurvas = (await import('../texto/curvas.js')).FuenteCurvas } catch { FuenteCurvas = null }

let abridor = null
if (FuenteCurvas) {
  abridor = crearAbridor({
    catalogo: F.catalogo, alias: F.alias || {}, FuenteCurvas,
    traer: async (e) => new Uint8Array(fs.readFileSync(e.ruta)),
  })
  const nombres = new Set(['Arial-BoldMT'])
  for (const caso of F.casos) for (const m of Object.values(caso.pers || {})) for (const c of Object.values(m)) if (c.fuente) nombres.add(c.fuente)
  await abridor.precargar([...nombres])
}

const casos = []
let n = 0
for (const caso of F.casos) {
  const arte = new Uint8Array(fs.readFileSync(caso.arte))
  const oa = caso.objetos_agregados && caso.objetos_agregados.objetos
    ? { objetos: caso.objetos_agregados.objetos, abrir: (a) => new Uint8Array(fs.readFileSync(path.join(caso.objetos_agregados.dir, a))) }
    : null
  const ctx = contextoCaminoA(mupdf, {
    arte, mapeoArte: caso.mapeo_arte, mapeoVar: caso.mapeo_var || {}, editables: caso.editables || [],
    editablesCfg: caso.editables_cfg ?? null, editablesTamano: caso.editables_tamano ?? null,
    editablesColor: caso.editables_color ?? null, editablesMarca: caso.editables_marca ?? null,
    editablesSinMarca: caso.editables_sin_marca ?? null, marcasComoCruz: caso.marcas_como_cruz ?? true,
    referencia: caso.referencia || 'alto', borde: F.borde, objetosAgregados: oa,
    fuente: abridor ? abridor.abrir : null,
  })
  const out = []
  for (const p of caso.piezas) {
    const base = ctx.armarBase({ cont: p.cont, pieza: p.pieza, talle: p.talle, variante: p.variante ?? null })
    let estampado = null
    if (abridor) {
      const ph = base.mesaA ? ((caso.pers || {})[String(base.mesaA)] || {}) : {}
      estampado = estamparPieza({
        base, ph, persona: p.persona, talle: p.talle, pieza: p.pieza, nro: p.nro, variante: p.variante ?? null,
        grupo: p.grupo ?? null, etiqueta: F.etiqueta, fuente: abridor.abrir, alias: F.alias || {}, info: p.info || {},
        separado: true, arteRect: base.arteRect,
      })
    }
    const r = { pieza: p.pieza, talle: p.talle, variante: p.variante ?? null, base_stream: base.baseStream, clip: base.clip,
      estampado, mesa_a: base.mesaA, W: base.W, H: base.H, B: base.B, S: base.S,
      fuentes: base.fuentesXo.map(([nom, ref]) => [nom, ref.origen]), arte_rect: base.arteRect }
    if (carpetaPdfs) {
      const bytes = documentoPiezaCaminoA(mupdf, base, estampado || '')
      r.pdf = path.join(carpetaPdfs, `nav_${n++}.pdf`)
      fs.writeFileSync(r.pdf, bytes)
    }
    out.push(r)
  }
  casos.push({ nombre: caso.nombre, redibujados: [...ctx.redibujarValidos], piezas: out })
  ctx.cerrar()
}
fs.writeFileSync(salida, JSON.stringify({ con_fuentes: !!FuenteCurvas, casos }))
