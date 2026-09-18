// LOS OBJETOS EDITABLES DEL ARTE (capas «Editable …») — PLAN_NAVEGADOR.md, etapa 3, camino A.
// Traducción de `motor_pedido._extraer_editables_crudo(con_thumb=False)` y de
// `molde_real._analizar_capa`/`objetos_de_capa` (los objetos de una capa, con su `obj_id`
// estable por geometría) más el `get_bboxlog(layers=True)` de PyMuPDF (texto, imágenes y
// sombreados de la capa, que `get_drawings` no ve).
//
// Devuelve la misma lista que Python, sin `thumb` ni `svg` (el navegador dibuja el objeto él
// mismo desde el arte): [{mesa, capa, nombre, bbox_mu, mesa_rect, w_cm, h_cm, thumb: null,
// svg: null, objetos: [{obj_id, kind, bbox_mu, mesa_rect, w_cm, h_cm, fill, recolorable, thumb,
// svg}]}]. El `obj_id` es `sha1(repr(firma))[:8]` con el `repr` de Python reproducido letra por
// letra (`reprPy`): un id distinto rompería la configuración guardada de cada objeto.
import { pyRound, pyStrip } from '../py.js'
import { sha1Hex } from '../sha1.js'
import { instrucciones, contenidoCrudo } from '../pdf/contenido.js'
import { dibujosDePagina } from '../pdf/dibujos.js'
import { cropboxPyMuPDF } from '../molde/contornos.js'
import { abrir, nombresOc, normNombre, reprPy, strOperando, floatOperando, transformarRect, rectVacio, WS_PY } from './texto.js'
import { esCapaEditable } from './personalizacion.js'

export const CM = 28.3465
const RX_WS = new RegExp('[' + WS_PY + ']', 'u')

const CONSTRUCCION = new Set(['m', 'l', 'c', 'v', 'y', 're', 'h'])
const PAINT_PATH = new Set(['S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*'])
const TERMINADORES = new Set([...PAINT_PATH, 'n'])
const FILL_PATH = new Set(['f', 'F', 'f*', 'b', 'b*', 'B', 'B*'])
const STROKE_PATH = new Set(['S', 's', 'b', 'b*', 'B', 'B*'])
const PAINT_TEXT = new Set(['Tj', 'TJ', "'", '"'])

/** `_mmul`: `a` aplicada ANTES que `b` (el operador `cm`). */
const mmul = (a, b) => [a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3],
                        a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3],
                        a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5]]
const mpt = (m, x, y) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]]

const nulo = (o) => !o || o.isNull()

/** `float(v)` de un número de pikepdf: el texto del archivo → double. Con mupdf.js los reales
 *  llegan como `float`; `toString()` devuelve la escritura más corta que vuelve a ese float, que
 *  para lo que escribe Illustrator (≤ 7 cifras) es el texto original. */
function numeroExacto(o) {
  if (o.isInteger()) return o.asNumber()
  const t = o.toString()
  const v = Number(t)
  return Number.isFinite(v) ? v : o.asNumber()
}

/** `_bbox_xobject(page, nombre, ctm)`: BBox (coords PDF) de un Form XObject con la CTM vigente. */
function bboxXObject(page, nombre, ctm) {
  try {
    const xo = page.getObject().get('Resources').get('XObject').get(nombre)
    if (nulo(xo)) return null
    const bb = xo.get('BBox')
    if (nulo(bb) || !bb.isArray() || bb.length < 4) return null
    const bx = [0, 1, 2, 3].map((i) => numeroExacto(bb.get(i)))
    const mo = xo.get('Matrix')
    let M = [1, 0, 0, 1, 0, 0]
    if (!nulo(mo)) {
      if (!mo.isArray() || mo.length < 6) return null
      M = [0, 1, 2, 3, 4, 5].map((i) => numeroExacto(mo.get(i)))
    }
    const m = mmul(M, ctm)
    const xs = [], ys = []
    for (const [px, py] of [[bx[0], bx[1]], [bx[2], bx[1]], [bx[2], bx[3]], [bx[0], bx[3]]]) {
      const q = mpt(m, px, py)
      xs.push(q[0]); ys.push(q[1])
    }
    return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]
  } catch {
    return null
  }
}

// la CTM arranca como la tupla de ENTEROS `(1, 0, 0, 1, 0, 0)` de Python: si nunca hubo un `cm`,
// `round(ctm[0], 3)` es el int `1` y su repr es «1», no «1.0» — la firma cambia con eso
const CTM_INICIAL = [1, 0, 0, 1, 0, 0]

/**
 * `molde_real._analizar_capa(page, objetivo)["objetos"]` sobre una lista de instrucciones ya
 * parseada (`pdf/contenido.js`, los mismos índices que pikepdf).
 */
export function objetosDeCapa(page, insts, objetivo) {
  const obj = normNombre(objetivo)
  let ctm = CTM_INICIAL, ctmInt = true
  const pilaCtm = [], pilaOc = []
  let ini = null, pts = [], clip = false
  let fill = null
  const unidades = []
  const cacheOc = new Map()
  const frameCapas = () => { const s = new Set(); for (const fr of pilaOc) for (const x of fr) s.add(x); return s }
  const numDe = (v) => (ctmInt ? { int: v } : v)

  for (let i = 0; i < insts.length; i++) {
    const it = insts[i]
    const op = it.op
    if (op === 'q') pilaCtm.push([ctm, ctmInt])
    else if (op === 'Q') { if (pilaCtm.length) [ctm, ctmInt] = pilaCtm.pop() }
    else if (op === 'cm') {
      try { ctm = mmul(it.args.map(floatOperando), ctm); ctmInt = false } catch { /* pass */ }
    } else if (op === 'k') {
      try { fill = it.args.map(floatOperando).slice(0, 4) } catch { fill = null }
    } else if (op === 'scn' || op === 'sc') {
      try { const vals = it.args.map(floatOperando); fill = vals.length === 4 ? vals : fill } catch { /* pass */ }
    } else if (op === 'BDC' || op === 'BMC') {
      let nombres = new Set()
      if (op === 'BDC' && it.args.length === 2 && it.args[0].n === 'OC') {
        const k = it.args[1].n
        if (k !== undefined && cacheOc.has(k)) nombres = cacheOc.get(k)
        else { nombres = new Set(nombresOc(page, it.args[1]).map(normNombre)); if (k !== undefined) cacheOc.set(k, nombres) }
      }
      pilaOc.push(nombres)
    } else if (op === 'EMC') {
      if (pilaOc.length) pilaOc.pop()
    } else if (CONSTRUCCION.has(op)) {
      if (ini === null) { ini = i; pts = []; clip = false }
      let fl
      try { fl = it.args.map(floatOperando) } catch { fl = [] }
      if (op === 're' && fl.length === 4) {
        const [x, y, w, h] = fl
        for (const [px, py] of [[x, y], [x + w, y], [x, y + h], [x + w, y + h]]) pts.push(mpt(ctm, px, py))
      } else {
        for (let k = 0; k < fl.length - 1; k += 2) pts.push(mpt(ctm, fl[k], fl[k + 1]))
      }
    } else if (op === 'W' || op === 'W*') {
      clip = true
    } else if (TERMINADORES.has(op)) {
      if (pts.length) {
        const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1])
        const bbox = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]
        const esClip = clip || op === 'n'
        const fillOp = FILL_PATH.has(op), strokeOp = STROKE_PATH.has(op)
        const sig = reprPy(['v', ...pts.map((p) => [pyRound(p[0], 1), pyRound(p[1], 1)])])
        unidades.push({ i, bbox, esClip, capas: frameCapas(), kind: 'vector', fillOp, strokeOp, fill: fillOp ? fill : null, sig })
      }
      ini = null; pts = []; clip = false
    } else if (op === 'Do') {
      const nom = it.args.length ? strOperando(it.args[0]) : ''
      let bbox = (it.args.length && it.args[0].n !== undefined) ? bboxXObject(page, it.args[0].n, ctm) : null
      if (bbox === null) bbox = [ctm[4], ctm[5], ctm[4], ctm[5]]
      const sig = reprPy(['do', nom, numDe(pyRound(ctm[0], 3)), numDe(pyRound(ctm[3], 3)), numDe(pyRound(ctm[4], 1)), numDe(pyRound(ctm[5], 1))])
      unidades.push({ i, bbox, esClip: false, capas: frameCapas(), kind: 'xobject', fillOp: false, strokeOp: false, fill: null, sig })
    } else if (PAINT_TEXT.has(op)) {
      unidades.push({ i, bbox: [ctm[4], ctm[5], ctm[4], ctm[5]], esClip: false, capas: frameCapas(), kind: 'texto',
                      fillOp: false, strokeOp: false, fill: null, sig: reprPy(['tx', { int: i }]) })
    } else if (op === 'sh') {
      unidades.push({ i, bbox: [ctm[4], ctm[5], ctm[4], ctm[5]], esClip: false, capas: frameCapas(), kind: 'shading',
                      fillOp: false, strokeOp: false, fill: null, sig: reprPy(['sh', numDe(pyRound(ctm[4], 1)), numDe(pyRound(ctm[5], 1)), { int: i }]) })
    }
  }

  const pintadas = unidades.filter((u) => u.capas.has(obj) && !u.esClip)
  const porSig = new Map()
  for (const u of pintadas) {
    if (!porSig.has(u.sig)) porSig.set(u.sig, [])
    porSig.get(u.sig).push(u)
  }
  const objetos = []
  for (const [s, us] of porSig) {
    const b = [Math.min(...us.map((u) => u.bbox[0])), Math.min(...us.map((u) => u.bbox[1])),
               Math.max(...us.map((u) => u.bbox[2])), Math.max(...us.map((u) => u.bbox[3]))]
    const fillOp = us.some((u) => u.fillOp), strokeOp = us.some((u) => u.strokeOp)
    const conFill = us.find((u) => u.fill !== null)
    objetos.push({
      obj_id: sha1Hex(s).slice(0, 8), kind: us[0].kind, bbox: b,
      fill: conFill ? [...conFill.fill] : null, recolorable: !!(fillOp || strokeOp),
      fill_op: fillOp, stroke_op: strokeOp, i_paints: new Set(us.map((u) => u.i)), _primera: Math.min(...us.map((u) => u.i)),
    })
  }
  objetos.sort((a, b) => a._primera - b._primera)
  for (const o of objetos) delete o._primera
  return objetos
}

/** `get_bboxlog(layers=True)`: [(código, rect, capa)] — sólo los que no son trazados (los
 *  trazados ya los cubre `dibujosDePagina`). */
export function bboxlog(mupdf, page) {
  const out = []
  let capa = ''
  const add = (codigo, r) => out.push([codigo, [r[0], r[1], r[2], r[3]], capa])
  const dev = new mupdf.Device({
    fillText(text, ctm) { add('fill-text', text.getBounds(null, ctm)) },
    strokeText(text, stroke, ctm) { add('stroke-text', text.getBounds(stroke, ctm)) },
    ignoreText(text, ctm) { add('ignore-text', text.getBounds(null, ctm)) },
    // `fz_bound_shade(shade, ctm)`: mupdf.js sólo da el límite con la identidad; se transforma
    // después por la CTM (idéntico salvo por redondeos de float32 con giros — no hay sombreados
    // en las capas editables de los artes reales)
    fillShade(shade, ctm) { add('fill-shade', transformarRect(shade.getBounds(), ctm)) },
    fillImage(image, ctm) { add('fill-image', transformarRect([0, 0, 1, 1], ctm)) },
    fillImageMask(image, ctm) { add('fill-imgmask', transformarRect([0, 0, 1, 1], ctm)) },
    beginLayer(name) { capa = name || '' },
    endLayer() { capa = '' },
  })
  page.run(dev, mupdf.Matrix.identity)
  dev.close()
  return out
}

/** `_nombre_editable(capa)`: sin el prefijo «editable» (con o sin separador). */
export function nombreEditable(capa) {
  const s = pyStrip(String(capa))
  const chars = Array.from(s)
  let i = 0
  const esWs = (ch) => RX_WS.test(ch)
  while (i < chars.length && esWs(chars[i])) i++
  const pal = chars.slice(i, i + 8).join('')
  let fin = null
  if (pal.toLowerCase() === 'editable') {
    const sig = chars[i + 8]
    // `\b`: después de «editable» no puede seguir otro carácter de palabra
    if (sig === undefined || !/[\p{L}\p{N}_]/u.test(sig)) {
      let j = i + 8
      while (j < chars.length && (esWs(chars[j]) || chars[j] === '-' || chars[j] === '_')) j++
      fin = j
    }
  }
  return (fin === null ? s : pyStrip(chars.slice(fin).join(''))) || 'Editable'
}

/**
 * `_extraer_editables_crudo(path_arte, con_thumb=False)` sobre los bytes del arte.
 */
export function extraerEditables(mupdf, bytes, { estricto = false } = {}) {
  const doc = abrir(mupdf, bytes)
  const objs = []
  try {
    const n = doc.countPages()
    for (let pno = 0; pno < n; pno++) {
      const pg = doc.loadPage(pno)
      try {
        const cajas = new Map()
        const sumar = (lay, x0, y0, x1, y1) => {
          if (!lay || !esCapaEditable(lay)) return
          const b = cajas.get(lay)
          if (!b) { cajas.set(lay, [x0, y0, x1, y1]); return }
          b[0] = Math.min(b[0], x0); b[1] = Math.min(b[1], y0)
          b[2] = Math.max(b[2], x1); b[3] = Math.max(b[3], y1)
        }
        for (const dr of dibujosDePagina(mupdf, pg)) {
          if ((dr.type === 'f' || dr.type === 's' || dr.type === 'fs') && dr.rect) sumar(dr.layer, dr.rect[0], dr.rect[1], dr.rect[2], dr.rect[3])
        }
        try {
          for (const [codigo, r, lay] of bboxlog(mupdf, pg)) {
            if (codigo.includes('path')) continue
            if (!rectVacio(r)) sumar(lay, r[0], r[1], r[2], r[3])
          }
        } catch (e) { if (estricto) throw e }
        const insts = cajas.size ? [...instrucciones(contenidoCrudo(pg))] : null
        const cb = cropboxPyMuPDF(pg)
        const pr = pg.getBounds()
        const prW = Math.max(0, pr[2] - pr[0]), prH = Math.max(0, pr[3] - pr[1])
        const cbW = Math.max(0, cb[2] - cb[0])
        const U = cbW ? prW / cbW : 1.0
        const aMu = (bp) => [pyRound((bp[0] - cb[0]) * U, 2), pyRound((cb[3] - bp[3]) * U, 2),
                             pyRound((bp[2] - cb[0]) * U, 2), pyRound((cb[3] - bp[1]) * U, 2)]
        const mesaRect = [pyRound(pr[0], 2), pyRound(pr[1], 2), pyRound(prW, 2), pyRound(prH, 2)]
        for (const [capa, b] of cajas) {
          let od = []
          try { od = objetosDeCapa(pg, insts, capa) } catch (e) { if (estricto) throw e; od = [] }
          const objetos = od.map((o) => {
            const bm = aMu(o.bbox)
            return { obj_id: o.obj_id, kind: o.kind, bbox_mu: bm, mesa_rect: mesaRect,
                     w_cm: pyRound((bm[2] - bm[0]) / CM, 1), h_cm: pyRound((bm[3] - bm[1]) / CM, 1),
                     fill: o.fill, recolorable: !!o.recolorable, thumb: null, svg: null }
          })
          objs.push({
            mesa: pno + 1, capa, nombre: nombreEditable(capa),
            bbox_mu: b.map((v) => pyRound(v, 2)), mesa_rect: mesaRect,
            w_cm: pyRound((b[2] - b[0]) / CM, 1), h_cm: pyRound((b[3] - b[1]) / CM, 1),
            thumb: null, svg: null, objetos,
          })
        }
      } finally {
        pg.destroy()
      }
    }
  } finally {
    doc.destroy()
  }
  return objs
}
