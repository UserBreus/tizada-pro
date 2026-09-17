// LOS DIBUJOS DE UNA PÁGINA — traducción de `Page.get_cdrawings(extended=True)` de PyMuPDF.
//
// 🔴 POR QUÉ UNA TRADUCCIÓN Y NO «ALGO PARECIDO» (PLAN_NAVEGADOR.md, etapa 0). Todo lo que hoy
// encuentra las piezas de un molde (`piezas_con_diseno._piezas_de_mesa_cruda`, `molde_real`) lee
// la lista que devuelve `get_cdrawings`: el tipo de cada dibujo, su capa, su nivel de recorte, su
// rectángulo y sus tramos («l», «c», «re», «qu»). Para que el navegador prepare el molde IGUAL que
// el servidor tiene que ver EXACTAMENTE esa lista. MuPDF es el mismo en los dos lados; lo que hay
// que copiar es el «device» que PyMuPDF le pone encima (`JM_new_lineart_device_Device`,
// `Walker`, `jm_checkrect`, `jm_checkquad`, `jm_append_merge`, `compute_scissor`), línea por línea.
//
// ⚠️ FLOAT32. MuPDF transforma los puntos con `float` de C. Con `number` de JS (64 bits) el mismo
// cálculo difiere en la sexta cifra y la comparación contra el servidor no daría idéntico. Por
// eso cada operación pasa por `Math.fround`, en el mismo orden que la hace C.
//
// No se traducen (no los usa el alta y no se pueden leer igual desde mupdf.js): el color convertido
// a RGB, `lineCap`/`lineJoin`/`dashes`. Quedan fuera de la comparación a propósito.

const f = Math.fround

function transformar(x, y, m) {
  // fz_transform_point: x' = x*a + y*c + e ; y' = x*b + y*d + f
  return [f(f(f(x * m[0]) + f(y * m[2])) + m[4]), f(f(f(x * m[1]) + f(y * m[3])) + m[5])]
}

const INFINITO = null   // fz_infinite_rect

function incluir(r, p) {
  // fz_include_point_in_rect
  if (r === INFINITO) return r
  return [Math.min(r[0], p[0]), Math.min(r[1], p[1]), Math.max(r[2], p[0]), Math.max(r[3], p[1])]
}

function intersectar(a, b) {
  // fz_intersect_rect de MuPDF 1.26: recorta lado por lado y NO colapsa un resultado vacío —
  // puede quedar «al revés» (x0 > x1), y PyMuPDF lo devuelve así. Medido con la camiseta de
  // 117 MB: 60 recortes de una mesa salían distintos cuando acá se colapsaba a un punto.
  if (b === INFINITO) return a
  if (a === INFINITO) return b
  const r = [a[0], a[1], a[2], a[3]]
  if (r[0] < b[0]) r[0] = b[0]
  if (r[1] < b[1]) r[1] = b[1]
  if (r[2] > b[2]) r[2] = b[2]
  if (r[3] > b[3]) r[3] = b[3]
  return r
}

const aRect = (r) => (r === INFINITO ? [-2147483648, -2147483648, 2147483520, 2147483520] : [r[0], r[1], r[2], r[3]])
const mismoPunto = (a, b) => a[0] === b[0] && a[1] === b[1]

function mismosItems(a, b) {
  return JSON.stringify(a) === JSON.stringify(b)
}

/**
 * Los dibujos de `page` (un `mupdf.Page`), como `page.get_cdrawings(extended=True)`.
 * Cada uno: {type, items, rect|scissor, level, layer, closePath, even_odd, seqno, width, ...}.
 */
export function dibujosDePagina(mupdf, page) {
  const out = []
  const dev = {
    seqno: 0, depth: 0, scissors: [], layer: '',
    ctm: null, pathType: 0, pathrect: INFINITO, pathdict: null,
    lastpoint: [0, 0], firstpoint: [0, 0], havemove: 0, linecount: 0,
  }
  const FILL = 1, STROKE = 2, CLIP = 3, CLIP_STROKE = 4

  function checkrect() {
    dev.linecount = 0
    const items = dev.pathdict.items
    const n = items.length
    const line0 = items[n - 3], line2 = items[n - 1]
    const ll = line0[1], lr = line0[2], ur = line2[1], ul = line2[2]
    if (ll[1] !== lr[1] || ll[0] !== ul[0] || ur[1] !== ul[1] || ur[0] !== lr[0]) return 0
    let r, orient
    if (ul[1] < lr[1]) { r = [ul[0], ul[1], lr[0], lr[1]]; orient = 1 } else { r = [ll[0], ll[1], ur[0], ur[1]]; orient = -1 }
    items.splice(n - 3, 3, ['re', r, orient])
    return 1
  }

  function checkquad() {
    const items = dev.pathdict.items
    const n = items.length
    const p = []
    let lp = null
    for (let i = 0; i < 4; i++) {
      const line = items[n - 4 + i]
      p.push(line[1])
      lp = line[2]
    }
    if (lp[0] !== p[0][0] || lp[1] !== p[0][1]) return 0
    dev.linecount = 0
    // fz_make_quad(ul=p0, ur=p3, ll=p1, lr=p2) → ((ul),(ur),(ll),(lr))
    items.splice(n - 4, 4, ['qu', [p[0], p[3], p[1], p[2]]])
    return 1
  }

  const walker = {
    moveTo(x, y) {
      dev.lastpoint = transformar(x, y, dev.ctm)
      if (dev.pathrect === INFINITO) dev.pathrect = [dev.lastpoint[0], dev.lastpoint[1], dev.lastpoint[0], dev.lastpoint[1]]
      dev.firstpoint = dev.lastpoint
      dev.havemove = 1
      dev.linecount = 0
    },
    lineTo(x, y) {
      const p1 = transformar(x, y, dev.ctm)
      dev.pathrect = incluir(dev.pathrect, p1)
      dev.pathdict.items.push(['l', dev.lastpoint, p1])
      dev.lastpoint = p1
      dev.linecount += 1
      if (dev.linecount === 4 && dev.pathType !== FILL) checkquad()
    },
    curveTo(x1, y1, x2, y2, x3, y3) {
      dev.linecount = 0
      const p1 = transformar(x1, y1, dev.ctm), p2 = transformar(x2, y2, dev.ctm), p3 = transformar(x3, y3, dev.ctm)
      dev.pathrect = incluir(incluir(incluir(dev.pathrect, p1), p2), p3)
      dev.pathdict.items.push(['c', dev.lastpoint, p1, p2, p3])
      dev.lastpoint = p3
    },
    closePath() {
      if (dev.linecount === 3) {
        if (checkrect()) return
      }
      dev.linecount = 0
      if (dev.havemove) {
        if (!mismoPunto(dev.lastpoint, dev.firstpoint)) {
          dev.pathdict.items.push(['l', dev.lastpoint, dev.firstpoint])
          dev.lastpoint = dev.firstpoint
        }
        dev.pathdict.closePath = false
      } else {
        dev.pathdict.closePath = true
      }
      dev.havemove = 0
    },
  }

  function recorrer(path) {
    dev.pathrect = INFINITO
    dev.linecount = 0
    dev.lastpoint = [0, 0]
    dev.pathdict = { items: [] }
    path.walk(walker)
    if (!dev.pathdict.items.length) dev.pathdict = null
  }

  function agregar() {
    // jm_append_merge: un trazo con los mismos tramos que el relleno anterior se funde en «fs»
    const pd = dev.pathdict
    const append = () => { out.push({ ...pd }); dev.pathdict = null }
    if (!out.length) return append()
    if (pd.type !== 's') return append()
    const prev = out[out.length - 1]
    if (prev.type !== 'f') return append()
    if (!mismosItems(prev.items, pd.items)) return append()
    for (const [k, v] of Object.entries(pd)) if (!(k in prev)) prev[k] = v
    prev.type = 'fs'
    dev.pathdict = null
  }

  function scissor() {
    // compute_scissor
    const n = dev.scissors.length
    const s = n > 0 ? intersectar(dev.scissors[n - 1], dev.pathrect) : dev.pathrect
    dev.scissors.push(s)
    return s
  }

  const device = new mupdf.Device({
    fillPath(path, evenOdd, ctm) {
      dev.ctm = ctm
      dev.pathType = FILL
      recorrer(path)
      if (!dev.pathdict) return
      Object.assign(dev.pathdict, {
        type: 'f', even_odd: !!evenOdd, rect: aRect(dev.pathrect), seqno: dev.seqno, layer: dev.layer, level: dev.depth,
      })
      agregar()
      dev.seqno += 1
    },
    strokePath(path, stroke, ctm) {
      let factor = 1
      if (ctm[0] !== 0 && Math.abs(ctm[0]) === Math.abs(ctm[3])) factor = Math.abs(ctm[0])
      else if (ctm[1] !== 0 && Math.abs(ctm[1]) === Math.abs(ctm[2])) factor = Math.abs(ctm[1])
      dev.ctm = ctm
      dev.pathType = STROKE
      recorrer(path)
      if (!dev.pathdict) return
      Object.assign(dev.pathdict, { type: 's', width: factor * stroke.getLineWidth() })
      if (!('closePath' in dev.pathdict)) dev.pathdict.closePath = false
      Object.assign(dev.pathdict, { rect: aRect(dev.pathrect), layer: dev.layer, seqno: dev.seqno, level: dev.depth })
      agregar()
      dev.seqno += 1
    },
    clipPath(path, evenOdd, ctm) {
      dev.ctm = ctm
      dev.pathType = CLIP
      recorrer(path)
      if (!dev.pathdict) return
      dev.pathdict.type = 'clip'
      dev.pathdict.even_odd = !!evenOdd
      if (!('closePath' in dev.pathdict)) dev.pathdict.closePath = false
      dev.pathdict.scissor = aRect(scissor())
      dev.pathdict.level = dev.depth
      dev.pathdict.layer = dev.layer
      agregar()
      dev.depth += 1
    },
    clipStrokePath(path, stroke, ctm) {
      dev.ctm = ctm
      dev.pathType = CLIP_STROKE
      recorrer(path)
      if (!dev.pathdict) return
      // (PyMuPDF escribe la clave 'dictkey_type' por error: el tipo queda SIN poner; se copia igual)
      dev.pathdict.dictkey_type = 'clip'
      dev.pathdict.even_odd = null
      if (!('closePath' in dev.pathdict)) dev.pathdict.closePath = false
      dev.pathdict.scissor = aRect(scissor())
      dev.pathdict.level = dev.depth
      dev.pathdict.layer = dev.layer
      agregar()
      dev.depth += 1
    },
    clipText() { dev.pathrect = dev.pathrect; scissor(); dev.depth += 1 },
    clipStrokeText() { scissor(); dev.depth += 1 },
    clipImageMask() { scissor(); dev.depth += 1 },
    popClip() {
      if (!dev.scissors.length) return
      dev.scissors.pop()
      dev.depth -= 1
    },
    beginGroup(bbox) {
      dev.pathdict = { type: 'group', rect: [bbox[0], bbox[1], bbox[2], bbox[3]], level: dev.depth, layer: dev.layer }
      agregar()
      dev.depth += 1
    },
    endGroup() { dev.depth -= 1 },
    beginLayer(name) { dev.layer = name || '' },
    endLayer() { dev.layer = '' },
    fillText() { dev.seqno += 1 },
    strokeText() { dev.seqno += 1 },
    ignoreText() { dev.seqno += 1 },
    fillShade() { dev.seqno += 1 },
    fillImage() { dev.seqno += 1 },
    fillImageMask() { dev.seqno += 1 },
  })
  page.run(device, mupdf.Matrix.identity)
  device.close()
  return out
}
