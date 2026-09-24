// LA HOJA DE TIZADA, DIBUJADA RÁPIDO: cada dibujo de origen se interpreta UNA vez.
//
// Medido sobre un pedido real (2026-09-18, «el visor le re cuesta»): una hoja de 10 MB tarda 20-30 s
// en armar su lista de dibujo. No es la hoja: son 100 `Do` de 7 dibujos de origen (la mesa
// desplegada de cada talle, 117 000 operadores cada uno) — MuPDF vuelve a INTERPRETAR el dibujo
// entero en cada `Do`, aunque el recorte de la pieza deje ver el 5 %. 100 × 117 000 = 11,7
// millones de operadores por página, por hilo.
//
// Acá se hace lo que MuPDF no hace solo: cada XObject de la página se convierte en una lista de
// dibujo UNA vez (0,5 s) y el contenido de la página —que es nuestro, lo escribe `hoja/componer.js`
// y lo aplana `rip/aplanar.js`: `q`/`Q`/`cm`, trazados, recortes, rellenos y trazos CMYK, `Do`— se
// repite sobre el dispositivo de dibujo llamando a cada lista con la matriz de su colocación. El
// dispositivo (`DrawDevice`) es el mismo que usa MuPDF para la página entera: mismo rasterizador,
// mismo anti-alias, misma conversión de color. Si en la página aparece un operador que no está en
// esta lista (texto vivo, imágenes, sombreados…), se devuelve `null` y se dibuja por el camino de
// siempre (`dibujarMesa`): nunca una vista distinta, en todo caso una más lenta.
import { instrucciones } from '../pdf/contenido.js'
import { rectoDePagina, recorteDeFracciones, aEntero } from './dibujar.js'

const num = (v) => (v && v.i !== undefined ? Number(v.i) : v && v.r !== undefined ? Number(v.r) : NaN)
const OPS = new Set(['q', 'Q', 'cm', 'm', 'l', 'c', 'v', 'y', 'h', 're', 'W', 'W*', 'n', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*',
  'S', 's', 'k', 'K', 'g', 'G', 'rg', 'RG', 'w', 'j', 'J', 'M', 'd', 'gs', 'Do', 'i', 'ri', 'BDC', 'EMC', 'BMC'])

/**
 * Prepara la página `pagina` de `doc` para repetirla: parsea su contenido y arma una lista de
 * dibujo por XObject. Devuelve `null` si la página no se puede repetir (algo fuera del repertorio).
 */
export function prepararReplay(mupdf, doc, pagina, cacheXO = null, claveDe = null) {
  const page = doc.loadPage(pagina)
  try {
    const obj = page.getObject()
    const base = page.getTransform()
    const cont = leerContenido(obj)
    const ops = []
    for (const ins of instrucciones(cont)) {
      if (ins.op === 'INLINE IMAGE' || !OPS.has(ins.op)) return null
      ops.push(ins)
    }
    const res = obj.getInheritable('Resources')
    const xobjs = new Map()
    const xo = res && !res.isNull() ? res.get('XObject') : null
    if (xo && !xo.isNull() && xo.isDictionary()) {
      xo.forEach((v, k) => {
        const st = v.get('Subtype')
        if (!st || st.isNull() || st.asName() !== 'Form') { xobjs.set(String(k), null); return }
        // `cacheXO` (Map): la lista de un XObject que YA se armó en OTRO documento con el mismo
        // dibujo se reusa. Lo usa la ficha: cada pieza de la guía es un PDF aparte que trae la MESA
        // entera del talle como XObject — sin esto se interpretaba la mesa completa una vez POR
        // PIEZA (2026-09-22, «la ficha tarda más de 40 s»).
        if (cacheXO) {
          const kx = claveDe ? claveDe(v, String(k)) : claveXObject(v)
          let l = kx ? cacheXO.get(kx) : undefined
          if (!l) { l = listaDeXObject(mupdf, doc, v); if (kx) cacheXO.set(kx, l) }
          xobjs.set(String(k), l)
          return
        }
        xobjs.set(String(k), listaDeXObject(mupdf, doc, v))
      })
    }
    for (const ins of ops) {
      if (ins.op === 'Do') {
        const n = ins.args[0] && ins.args[0].n
        if (!n || !xobjs.has(n) || xobjs.get(n) === null) return null
      }
    }
    const b = page.getBounds()
    // con `cacheXO` las listas son del que armó la caché: las destruye él (`destruirCacheXO`)
    return { ops, xobjs, base, bounds: b, destroy() { if (!cacheXO) for (const x of xobjs.values()) if (x) { try { x.dl.destroy() } catch { /* nada */ } } xobjs.clear() } }
  } finally {
    page.destroy()
  }
}

/** Huella de un Form XObject (su contenido crudo + caja + matriz): dos iguales dan la misma lista. */
function claveXObject(xobj) {
  try {
    const raw = xobj.readRawStream().asUint8Array()
    let h = 2166136261 >>> 0
    for (let i = 0; i < raw.length; i++) { h ^= raw[i]; h = Math.imul(h, 16777619) >>> 0 }
    const bb = xobj.get('BBox'), mo = xobj.get('Matrix')
    return `${raw.length}|${h}|${bb && !bb.isNull() ? bb.toString() : ''}|${mo && !mo.isNull() ? mo.toString() : ''}`
  } catch {
    return null
  }
}

/** Libera las listas de una caché de `prepararReplay`. */
export function destruirCacheXO(cacheXO) {
  for (const x of (cacheXO || new Map()).values()) if (x) { try { x.dl.destroy() } catch { /* nada */ } }
  if (cacheXO) cacheXO.clear()
}

function leerContenido(pageObj) {
  const c = pageObj.get('Contents')
  if (!c || c.isNull()) return new Uint8Array(0)
  if (c.isArray()) {
    const partes = []
    for (let i = 0; i < c.length; i++) partes.push(c.get(i).readStream().asUint8Array().slice())
    let n = 0
    for (const p of partes) n += p.length + 1
    const out = new Uint8Array(n)
    let k = 0
    for (const p of partes) { out.set(p, k); k += p.length; out[k++] = 10 }
    return out
  }
  return c.readStream().asUint8Array().slice()
}

/**
 * La lista de dibujo de un Form XObject: se arma un documento de UNA página cuyo contenido es
 * `/X Do` (el XObject injertado tal cual, con su BBox, su Matrix y sus recursos) y se toma su
 * lista. Es exactamente lo que MuPDF hace en cada `Do` de la página: acá, una sola vez.
 */
function listaDeXObject(mupdf, doc, xobj) {
  const tmp = new mupdf.PDFDocument()
  try {
    const mapa = tmp.newGraftMap()
    const injertado = mapa.graftObject(xobj)
    const res = tmp.newDictionary()
    const sub = tmp.newDictionary()
    sub.put('X', injertado)
    res.put('XObject', sub)
    // el BBox del XObject transformado por su Matrix: la página tiene que abarcarlo entero
    const bb = xobj.get('BBox')
    const caja = [0, 1, 2, 3].map((i) => Number(bb.get(i).toString()))
    const mo = xobj.get('Matrix')
    let m = [1, 0, 0, 1, 0, 0]
    if (mo && !mo.isNull() && mo.isArray() && mo.length === 6) m = [0, 1, 2, 3, 4, 5].map((i) => Number(mo.get(i).toString()))
    const pts = [[caja[0], caja[1]], [caja[2], caja[1]], [caja[2], caja[3]], [caja[0], caja[3]]].map(([x, y]) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]])
    const mb = [Math.min(...pts.map((p) => p[0])), Math.min(...pts.map((p) => p[1])), Math.max(...pts.map((p) => p[0])), Math.max(...pts.map((p) => p[1]))]
    tmp.insertPage(-1, tmp.addPage(mb, 0, res, '/X Do'))
    const pg = tmp.loadPage(0)
    try {
      // la lista queda en el espacio del DISPOSITIVO de esa página (con su transformación: el
      // eje y invertido y el origen del MediaBox); para correrla con la matriz de la colocación
      // hay que deshacer primero esa transformación
      return { dl: pg.toDisplayList(true), inv: mupdf.Matrix.invert(pg.getTransform()) }
    } finally {
      pg.destroy()
    }
  } finally {
    tmp.destroy()
  }
}

const mul = (a, b) => [a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3], a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3],
  a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5]]

/**
 * Repite la página preparada sobre `dev` con la matriz `ctm0` (la del dibujo: escala y recorte).
 * Es la parte del intérprete de MuPDF (`pdf-op-run.c`) que estas hojas usan.
 */
// ── cajas en el espacio del dispositivo, para NO dibujar lo que cae fuera del recorte pedido ──
const cajaDe = (b, m) => {
  if (!b) return null
  const xs = [], ys = []
  for (const [x, y] of [[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]]) { xs.push(m[0] * x + m[2] * y + m[4]); ys.push(m[1] * x + m[3] * y + m[5]) }
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]
}
const cortar = (a, b) => (!a ? b : !b ? a : [Math.max(a[0], b[0]), Math.max(a[1], b[1]), Math.min(a[2], b[2]), Math.min(a[3], b[3])])
const vacia = (r) => !!r && (r[0] >= r[2] || r[1] >= r[3])

/**
 * `caja` = el rectángulo del dibujo pedido, en píxeles del dispositivo. LO QUE CAE FUERA NO SE
 * DIBUJA (2026-09-18, «la vista sigue lenta»): un recorte del zoom cubre 50 cm de una mesa de 8 m,
 * pero se corría el dibujo de origen ENTERO (117 000 elementos) por cada una de las ~100 piezas de
 * la hoja, aunque la pieza estuviera a metros del recorte. Ahora se lleva la caja del recorte de
 * cada pieza (`W n`) y, si no toca el dibujo pedido, ni su `Do` ni sus rellenos van al dispositivo.
 * El resultado tiene que ser idéntico (lo salteado quedaba fuera del lienzo): se verifica byte a byte.
 */
export function correrReplay(mupdf, prep, dev, ctm0, caja = null) {
  const CMYK = mupdf.ColorSpace.DeviceCMYK, GRAY = mupdf.ColorSpace.DeviceGray, RGB = mupdf.ColorSpace.DeviceRGB
  const base = mul(prep.base, ctm0)
  let gs = { ctm: base, fillCs: GRAY, fill: [0], strokeCs: GRAY, stroke: [0], lw: 1, cap: 0, join: 0, miter: 10, clips: 0,
             clipBox: caja ? caja.slice() : null, oculto: false }
  let pb = null                        // la caja del trazado en curso, espacio del usuario (con los puntos de control)
  const pt = (x, y) => { if (!pb) pb = [x, y, x, y]; else { if (x < pb[0]) pb[0] = x; if (y < pb[1]) pb[1] = y; if (x > pb[2]) pb[2] = x; if (y > pb[3]) pb[3] = y } }
  const pila = []
  let path = null
  let clipPendiente = null            // 'nz' | 'eo' hasta el operador de pintado
  let cur, inicio = [0, 0]
  const nuevoPath = () => { if (!path) path = new mupdf.Path(); return path }
  const soltarPath = () => { if (path) { try { path.destroy() } catch { /* nada */ } } path = null; pb = null }
  const stroke = () => new mupdf.StrokeState({ lineCap: gs.cap, lineJoin: gs.join, lineWidth: gs.lw, miterLimit: gs.miter })
  const pintar = (op) => {
    const p = path || new mupdf.Path()
    const eo = op.endsWith('*')
    const rellena = /^(f|F|f\*|B|B\*|b|b\*)$/.test(op)
    const traza = /^(S|s|B|B\*|b|b\*)$/.test(op)
    if (op === 's' || op === 'b' || op === 'b*') p.closePath()
    const cajaPath = cajaDe(pb, gs.ctm)
    // el orden de MuPDF: primero el recorte pendiente, después rellenar, después trazar
    if (clipPendiente) {
      if (caja) {
        gs.clipBox = cortar(gs.clipBox, cajaPath || [0, 0, 0, 0])
        if (vacia(gs.clipBox)) gs.oculto = true          // todo lo que sigue hasta el `Q` cae fuera
      }
      if (!gs.oculto) { dev.clipPath(p, clipPendiente === 'eo', gs.ctm); gs.clips++ }
      clipPendiente = null
    }
    let visible = !gs.oculto
    if (visible && caja && cajaPath) {
      const g = traza ? gs.lw * Math.max(Math.hypot(gs.ctm[0], gs.ctm[1]), Math.hypot(gs.ctm[2], gs.ctm[3])) * Math.max(1, gs.miter) : 0
      visible = !vacia(cortar(gs.clipBox, [cajaPath[0] - g, cajaPath[1] - g, cajaPath[2] + g, cajaPath[3] + g]))
    }
    if (visible && rellena) dev.fillPath(p, eo, gs.ctm, gs.fillCs, gs.fill, 1)
    if (visible && traza) { const ss = stroke(); try { dev.strokePath(p, ss, gs.ctm, gs.strokeCs, gs.stroke, 1) } finally { ss.destroy() } }
    if (!path) p.destroy()
    soltarPath()
  }
  try {
    for (const { op, args } of prep.ops) {
      const a = args
      switch (op) {
        case 'q': pila.push({ ...gs }); gs = { ...gs, clips: 0, clipBox: gs.clipBox ? gs.clipBox.slice() : null }; break
        case 'Q': {
          for (let i = 0; i < gs.clips; i++) dev.popClip()
          gs = pila.pop() || gs
          break
        }
        case 'cm': gs.ctm = mul(a.map(num), gs.ctm); break
        case 'm': cur = inicio = [num(a[0]), num(a[1])]; pt(cur[0], cur[1]); nuevoPath().moveTo(cur[0], cur[1]); break
        case 'l': cur = [num(a[0]), num(a[1])]; pt(cur[0], cur[1]); nuevoPath().lineTo(cur[0], cur[1]); break
        case 'c': cur = [num(a[4]), num(a[5])]; pt(num(a[0]), num(a[1])); pt(num(a[2]), num(a[3])); pt(cur[0], cur[1]); nuevoPath().curveTo(num(a[0]), num(a[1]), num(a[2]), num(a[3]), cur[0], cur[1]); break
        case 'v': cur = [num(a[2]), num(a[3])]; pt(num(a[0]), num(a[1])); pt(cur[0], cur[1]); nuevoPath().curveToV(num(a[0]), num(a[1]), cur[0], cur[1]); break
        case 'y': cur = [num(a[2]), num(a[3])]; pt(num(a[0]), num(a[1])); pt(cur[0], cur[1]); nuevoPath().curveToY(num(a[0]), num(a[1]), cur[0], cur[1]); break
        case 'h': if (path) { path.closePath(); cur = inicio }; break
        case 're': {
          const [x, y, w, h] = a.map(num)
          const p = nuevoPath()
          pt(x, y); pt(x + w, y + h)
          p.moveTo(x, y); p.lineTo(x + w, y); p.lineTo(x + w, y + h); p.lineTo(x, y + h); p.closePath()
          cur = inicio = [x, y]
          break
        }
        case 'W': clipPendiente = 'nz'; break
        case 'W*': clipPendiente = 'eo'; break
        case 'n': case 'f': case 'F': case 'f*': case 'B': case 'B*': case 'b': case 'b*': case 'S': case 's':
          pintar(op); break
        case 'k': gs.fillCs = CMYK; gs.fill = a.map(num); break
        case 'K': gs.strokeCs = CMYK; gs.stroke = a.map(num); break
        case 'g': gs.fillCs = GRAY; gs.fill = a.map(num); break
        case 'G': gs.strokeCs = GRAY; gs.stroke = a.map(num); break
        case 'rg': gs.fillCs = RGB; gs.fill = a.map(num); break
        case 'RG': gs.strokeCs = RGB; gs.stroke = a.map(num); break
        case 'w': gs.lw = num(a[0]); break
        case 'j': gs.join = num(a[0]); break
        case 'J': gs.cap = num(a[0]); break
        case 'M': gs.miter = num(a[0]); break
        case 'Do': {
          if (gs.oculto) break                           // la pieza cae fuera del dibujo pedido
          const x = prep.xobjs.get(a[0].n)
          x.dl.run(dev, mul(x.inv, gs.ctm))
          break
        }
        default: break                 // gs, d, i, ri, BDC/EMC: no cambian el dibujo de estas hojas
      }
    }
    for (let i = 0; i < gs.clips; i++) dev.popClip()
    while (pila.length) { const g = pila.pop(); for (let i = 0; i < g.clips; i++) dev.popClip() }
  } finally {
    soltarPath()
  }
}

/** Como `dibujarMesa`, pero con el replay. Devuelve `{png, w, h}`. */
export function dibujarConReplay(mupdf, doc, pagina, prep, { ancho = 1200, recorte = null } = {}) {
  const page = doc.loadPage(pagina)
  const r = rectoDePagina(page)
  page.destroy()
  const clip = recorteDeFracciones(r, recorte)
  const anchoPt = ((clip ? clip[2] - clip[0] : r[2] - r[0]) || 1.0)
  const z = ancho / anchoPt
  const m = mupdf.Matrix.scale(z, z)
  const caja = aEntero(mupdf.Rect.transform(clip || r, m))
  const pix = new mupdf.Pixmap(mupdf.ColorSpace.DeviceRGB, caja, false)
  pix.clear(255)
  const dev = new mupdf.DrawDevice(mupdf.Matrix.identity, pix)
  try {
    correrReplay(mupdf, prep, dev, m, caja)
  } finally {
    dev.close()
  }
  const png = pix.asPNG()
  const w = pix.getWidth(), h = pix.getHeight()
  pix.destroy()
  return { png, w, h }
}

