// UN SVG → UN PDF DE UNA PÁGINA, EN ESTA COMPUTADORA — 2026-09-22.
//
// 🔴 POR QUÉ: «el servidor será sólo para sostener el sistema y la base». Para agregar un objeto al
// diseño («Editar diseño» → agregar), el servidor convertía el SVG con PyMuPDF (`fitz.open(...,
// "svg").convert_to_pdf()`). El MuPDF del navegador NO trae el lector de SVG (comprobado: en el
// .wasm sólo está el escritor), así que acá está el lector: el SVG se pasa a operadores PDF
// VECTORIALES (nada se rasteriza: LEY del vector original).
//
// QUÉ ENTIENDE: <svg> (width/height/viewBox), <g>, <path>, <rect> (con esquinas redondeadas),
// <circle>, <ellipse>, <line>, <polyline>, <polygon>, <use>/<symbol>/<defs>, <clipPath>,
// `transform` (matrix/translate/scale/rotate/skewX/skewY), relleno y trazo (colores con nombre,
// #rgb, #rrggbb, rgb()), `fill-rule`, grosor, uniones, puntas, `stroke-miterlimit`, opacidad
// (`opacity`, `fill-opacity`, `stroke-opacity`) y estilos por atributo, `style=""` y `<style>`
// con reglas por clase, id o etiqueta (lo que exporta Illustrator).
// QUÉ NO: degradados, patrones, imágenes, texto vivo, máscaras y filtros. Si el SVG trae alguno se
// AVISA con el motivo y no se sube nada (exportarlo como PDF desde Illustrator lo resuelve).
//
// MEDIDAS: 1 unidad de usuario = 1 pt, como MuPDF (que es con lo que el servidor medía el objeto):
// así un objeto mide lo mismo que antes.

const NOMBRES = {
  black: '#000000', white: '#ffffff', red: '#ff0000', green: '#008000', blue: '#0000ff', yellow: '#ffff00',
  cyan: '#00ffff', aqua: '#00ffff', magenta: '#ff00ff', fuchsia: '#ff00ff', gray: '#808080', grey: '#808080',
  silver: '#c0c0c0', maroon: '#800000', olive: '#808000', lime: '#00ff00', teal: '#008080', navy: '#000080',
  purple: '#800080', orange: '#ffa500', pink: '#ffc0cb', brown: '#a52a2a', gold: '#ffd700', darkgray: '#a9a9a9',
  darkgrey: '#a9a9a9', lightgray: '#d3d3d3', lightgrey: '#d3d3d3', darkred: '#8b0000', darkblue: '#00008b',
  darkgreen: '#006400', indigo: '#4b0082', violet: '#ee82ee', crimson: '#dc143c', coral: '#ff7f50',
}
const NO_SOPORTADO = {
  linearGradient: 'degradados', radialGradient: 'degradados', pattern: 'patrones', image: 'imágenes',
  text: 'texto vivo (pasalo a curvas)', mask: 'máscaras', filter: 'filtros', foreignObject: 'contenido HTML',
}

const n4 = (v) => {
  if (!Number.isFinite(v)) return '0'
  const r = Math.round(v * 10000) / 10000
  return Object.is(r, -0) ? '0' : String(r)
}
const mul = (a, b) => [a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3], a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3],
  a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5]]
const ID = [1, 0, 0, 1, 0, 0]

function error(msg) { const e = new Error(msg); e.svg = true; return e }

function largo(v, def = null) {
  if (v === null || v === undefined || v === '') return def
  const m = String(v).trim().match(/^([+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?)\s*(px|pt|pc|mm|cm|in|%)?$/i)
  if (!m) return def
  const x = parseFloat(m[1])
  switch ((m[2] || '').toLowerCase()) {
    case 'pc': return x * 12
    case 'mm': return x * 72 / 25.4
    case 'cm': return x * 72 / 2.54
    case 'in': return x * 72
    case '%': return def
    default: return x                                  // px y pt: 1 unidad = 1 pt (como MuPDF)
  }
}

function numeros(s) {
  return (String(s || '').match(/[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?/gi) || []).map(Number)
}

function transformDe(s) {
  let m = ID
  const re = /(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)/g
  let t
  while ((t = re.exec(String(s || '')))) {
    const a = numeros(t[2])
    let k = ID
    if (t[1] === 'matrix' && a.length >= 6) k = a.slice(0, 6)
    else if (t[1] === 'translate') k = [1, 0, 0, 1, a[0] || 0, a[1] || 0]
    else if (t[1] === 'scale') k = [a[0] ?? 1, 0, 0, a[1] ?? a[0] ?? 1, 0, 0]
    else if (t[1] === 'rotate') {
      const r = (a[0] || 0) * Math.PI / 180, c = Math.cos(r), sn = Math.sin(r)
      k = [c, sn, -sn, c, 0, 0]
      if (a.length >= 3) k = mul(mul([1, 0, 0, 1, -a[1], -a[2]], k), [1, 0, 0, 1, a[1], a[2]])
    } else if (t[1] === 'skewX') k = [1, 0, Math.tan((a[0] || 0) * Math.PI / 180), 1, 0, 0]
    else if (t[1] === 'skewY') k = [1, Math.tan((a[0] || 0) * Math.PI / 180), 0, 1, 0, 0]
    m = mul(k, m)                                       // el de la derecha se aplica primero
  }
  return m
}

function color(v) {
  if (v === null || v === undefined) return undefined
  const s = String(v).trim().toLowerCase()
  if (!s || s === 'none' || s === 'transparent') return null
  if (s.startsWith('url(')) throw error('el SVG usa degradados o patrones')
  if (s === 'currentcolor') return undefined
  let hex = NOMBRES[s] || s
  if (/^#[0-9a-f]{3}$/.test(hex)) hex = '#' + hex.slice(1).split('').map((c) => c + c).join('')
  if (/^#[0-9a-f]{6}$/.test(hex)) return [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
  const m = s.match(/^rgba?\(([^)]*)\)$/)
  if (m) {
    const p = m[1].split(/[\s,]+/).filter(Boolean).slice(0, 3)
    return p.map((x) => (x.endsWith('%') ? parseFloat(x) / 100 : parseFloat(x) / 255)).map((x) => Math.max(0, Math.min(1, x || 0)))
  }
  return [0, 0, 0]
}

// ── estilos: <style> (clase, id, etiqueta), atributos y style="" ─────────────────────────────
function reglasCss(texto) {
  const reglas = []
  const limpio = String(texto || '').replace(/\/\*[\s\S]*?\*\//g, '')
  const re = /([^{}]+)\{([^}]*)\}/g
  let m
  while ((m = re.exec(limpio))) {
    const decl = {}
    for (const par of m[2].split(';')) {
      const i = par.indexOf(':')
      if (i > 0) decl[par.slice(0, i).trim().toLowerCase()] = par.slice(i + 1).trim()
    }
    for (const sel of m[1].split(',')) reglas.push({ sel: sel.trim(), decl })
  }
  return reglas
}
function aplica(sel, el) {
  if (sel.startsWith('.')) return (el.getAttribute('class') || '').split(/\s+/).includes(sel.slice(1))
  if (sel.startsWith('#')) return el.getAttribute('id') === sel.slice(1)
  return sel === el.localName
}
const PROPS = ['fill', 'stroke', 'stroke-width', 'fill-rule', 'clip-rule', 'stroke-linejoin', 'stroke-linecap',
  'stroke-miterlimit', 'opacity', 'fill-opacity', 'stroke-opacity', 'display', 'visibility', 'clip-path', 'mask', 'filter']
function estiloDe(el, reglas, padre) {
  const e = { ...padre, opacity: 1 }               // la opacidad del grupo NO se hereda, se multiplica
  const propio = {}
  for (const p of PROPS) { const v = el.getAttribute(p); if (v !== null) propio[p] = v }
  for (const r of reglas) if (aplica(r.sel, el)) Object.assign(propio, r.decl)
  const st = el.getAttribute('style')
  if (st) for (const par of st.split(';')) { const i = par.indexOf(':'); if (i > 0) propio[par.slice(0, i).trim().toLowerCase()] = par.slice(i + 1).trim() }
  for (const [k, v] of Object.entries(propio)) {
    if (k === 'opacity') e.opacityPropia = parseFloat(v)
    else e[k] = v
  }
  e.opacityTotal = (padre.opacityTotal ?? 1) * (Number.isFinite(e.opacityPropia) ? e.opacityPropia : 1)
  delete e.opacityPropia
  return e
}

// ── trazados: el `d` de <path> y las figuras, en operadores (con curvas cúbicas) ─────────────
function arcoACubicas(x1, y1, rx, ry, phi, fa, fs, x2, y2) {
  // SVG 1.1 F.6.5: del arco en forma de extremos al centro, y de ahí a curvas de hasta 90°
  if (rx === 0 || ry === 0) return [['L', x2, y2]]
  const sinp = Math.sin(phi), cosp = Math.cos(phi)
  const dx = (x1 - x2) / 2, dy = (y1 - y2) / 2
  const x1p = cosp * dx + sinp * dy, y1p = -sinp * dx + cosp * dy
  rx = Math.abs(rx); ry = Math.abs(ry)
  const lam = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
  if (lam > 1) { rx *= Math.sqrt(lam); ry *= Math.sqrt(lam) }
  const num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
  const den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
  let co = Math.sqrt(Math.max(0, num / den))
  if (fa === fs) co = -co
  const cxp = co * (rx * y1p) / ry, cyp = co * -(ry * x1p) / rx
  const cx = cosp * cxp - sinp * cyp + (x1 + x2) / 2, cy = sinp * cxp + cosp * cyp + (y1 + y2) / 2
  const ang = (ux, uy, vx, vy) => {
    const d = Math.hypot(ux, uy) * Math.hypot(vx, vy)
    let a = Math.acos(Math.max(-1, Math.min(1, (ux * vx + uy * vy) / d)))
    if (ux * vy - uy * vx < 0) a = -a
    return a
  }
  const t1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
  let dt = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
  if (!fs && dt > 0) dt -= 2 * Math.PI
  else if (fs && dt < 0) dt += 2 * Math.PI
  const segs = Math.ceil(Math.abs(dt) / (Math.PI / 2))
  const d = dt / segs
  const k = (4 / 3) * Math.tan(d / 4)
  const out = []
  let t = t1
  const pt = (a) => [cx + rx * Math.cos(a) * cosp - ry * Math.sin(a) * sinp, cy + rx * Math.cos(a) * sinp + ry * Math.sin(a) * cosp]
  const der = (a) => [-rx * Math.sin(a) * cosp - ry * Math.cos(a) * sinp, -rx * Math.sin(a) * sinp + ry * Math.cos(a) * cosp]
  for (let i = 0; i < segs; i++) {
    const [ax, ay] = pt(t), [bx, by] = pt(t + d)
    const [dax, day] = der(t), [dbx, dby] = der(t + d)
    out.push(['C', ax + k * dax, ay + k * day, bx - k * dbx, by - k * dby, bx, by])
    t += d
  }
  return out
}

function comandosPath(d) {
  const toks = String(d || '').match(/[MmZzLlHhVvCcSsQqTtAa]|[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?/gi) || []
  const out = []
  let i = 0, cmd = null, cx = 0, cy = 0, sx = 0, sy = 0, lc = null, lq = null
  const num = () => Number(toks[i++])
  const hayNum = () => i < toks.length && !/^[A-Za-z]$/.test(toks[i])
  while (i < toks.length) {
    if (/^[A-Za-z]$/.test(toks[i])) cmd = toks[i++]
    else if (cmd === null) break
    const rel = cmd === cmd.toLowerCase(), C = cmd.toUpperCase()
    const ox = rel ? cx : 0, oy = rel ? cy : 0
    if (C === 'Z') { out.push(['Z']); cx = sx; cy = sy; lc = lq = null; continue }
    if (!hayNum()) continue
    if (C === 'M') {
      cx = num() + ox; cy = num() + oy; sx = cx; sy = cy; out.push(['M', cx, cy]); lc = lq = null
      cmd = rel ? 'l' : 'L'                              // los pares siguientes son líneas
    } else if (C === 'L') { cx = num() + ox; cy = num() + oy; out.push(['L', cx, cy]); lc = lq = null }
    else if (C === 'H') { cx = num() + (rel ? cx : 0); out.push(['L', cx, cy]); lc = lq = null }
    else if (C === 'V') { cy = num() + (rel ? cy : 0); out.push(['L', cx, cy]); lc = lq = null }
    else if (C === 'C') {
      const x1 = num() + ox, y1 = num() + oy, x2 = num() + ox, y2 = num() + oy
      cx = num() + ox; cy = num() + oy; out.push(['C', x1, y1, x2, y2, cx, cy]); lc = [x2, y2]; lq = null
    } else if (C === 'S') {
      const x1 = lc ? 2 * cx - lc[0] : cx, y1 = lc ? 2 * cy - lc[1] : cy
      const x2 = num() + ox, y2 = num() + oy
      cx = num() + ox; cy = num() + oy; out.push(['C', x1, y1, x2, y2, cx, cy]); lc = [x2, y2]; lq = null
    } else if (C === 'Q' || C === 'T') {
      let qx, qy
      if (C === 'Q') { qx = num() + ox; qy = num() + oy } else { qx = lq ? 2 * cx - lq[0] : cx; qy = lq ? 2 * cy - lq[1] : cy }
      const x = num() + ox, y = num() + oy
      out.push(['C', cx + 2 / 3 * (qx - cx), cy + 2 / 3 * (qy - cy), x + 2 / 3 * (qx - x), y + 2 / 3 * (qy - y), x, y])
      cx = x; cy = y; lq = [qx, qy]; lc = null
    } else if (C === 'A') {
      const rx = num(), ry = num(), rot = num(), fa = num(), fs = num()
      const x = num() + ox, y = num() + oy
      out.push(...arcoACubicas(cx, cy, rx, ry, rot * Math.PI / 180, !!fa, !!fs, x, y))
      cx = x; cy = y; lc = lq = null
    } else { i++ }
  }
  return out
}

const K = 0.5522847498                                   // cuarto de círculo con una cúbica
function elipse(cx, cy, rx, ry) {
  return [['M', cx + rx, cy],
    ['C', cx + rx, cy + K * ry, cx + K * rx, cy + ry, cx, cy + ry],
    ['C', cx - K * rx, cy + ry, cx - rx, cy + K * ry, cx - rx, cy],
    ['C', cx - rx, cy - K * ry, cx - K * rx, cy - ry, cx, cy - ry],
    ['C', cx + K * rx, cy - ry, cx + rx, cy - K * ry, cx + rx, cy], ['Z']]
}
function figura(el) {
  const f = (a, d = 0) => largo(el.getAttribute(a), d)
  switch (el.localName) {
    case 'path': return comandosPath(el.getAttribute('d'))
    case 'rect': {
      const x = f('x'), y = f('y'), w = f('width'), h = f('height')
      if (!(w > 0 && h > 0)) return []
      let rx = largo(el.getAttribute('rx'), null), ry = largo(el.getAttribute('ry'), null)
      if (rx === null && ry !== null) rx = ry
      if (ry === null && rx !== null) ry = rx
      rx = Math.min(rx || 0, w / 2); ry = Math.min(ry || 0, h / 2)
      if (!rx || !ry) return [['M', x, y], ['L', x + w, y], ['L', x + w, y + h], ['L', x, y + h], ['Z']]
      return [['M', x + rx, y], ['L', x + w - rx, y], ['C', x + w - rx + K * rx, y, x + w, y + ry - K * ry, x + w, y + ry],
        ['L', x + w, y + h - ry], ['C', x + w, y + h - ry + K * ry, x + w - rx + K * rx, y + h, x + w - rx, y + h],
        ['L', x + rx, y + h], ['C', x + rx - K * rx, y + h, x, y + h - ry + K * ry, x, y + h - ry],
        ['L', x, y + ry], ['C', x, y + ry - K * ry, x + rx - K * rx, y, x + rx, y], ['Z']]
    }
    case 'circle': { const r = f('r'); return r > 0 ? elipse(f('cx'), f('cy'), r, r) : [] }
    case 'ellipse': { const rx = f('rx'), ry = f('ry'); return rx > 0 && ry > 0 ? elipse(f('cx'), f('cy'), rx, ry) : [] }
    case 'line': return [['M', f('x1'), f('y1')], ['L', f('x2'), f('y2')]]
    case 'polyline': case 'polygon': {
      const p = numeros(el.getAttribute('points'))
      if (p.length < 4) return []
      const out = [['M', p[0], p[1]]]
      for (let i = 2; i + 1 < p.length; i += 2) out.push(['L', p[i], p[i + 1]])
      if (el.localName === 'polygon') out.push(['Z'])
      return out
    }
    default: return []
  }
}
function opsTrazado(cmds, m) {
  const P = (x, y) => `${n4(m[0] * x + m[2] * y + m[4])} ${n4(m[1] * x + m[3] * y + m[5])}`
  let s = ''
  for (const c of cmds) {
    if (c[0] === 'M') s += `${P(c[1], c[2])} m\n`
    else if (c[0] === 'L') s += `${P(c[1], c[2])} l\n`
    else if (c[0] === 'C') s += `${P(c[1], c[2])} ${P(c[3], c[4])} ${P(c[5], c[6])} c\n`
    else if (c[0] === 'Z') s += 'h\n'
  }
  return s
}

/**
 * `texto` = el SVG. Devuelve `{pdf: Uint8Array, w_pt, h_pt}`: un PDF de una página con el dibujo en
 * vector. Tira un Error con el motivo si el SVG trae algo que no se puede convertir.
 */
export function svgAPdf(texto) {
  if (typeof DOMParser === 'undefined') throw error('este navegador no puede leer SVG')
  const doc = new DOMParser().parseFromString(String(texto || ''), 'image/svg+xml')
  const svg = doc.documentElement
  if (!svg || svg.localName !== 'svg' || doc.getElementsByTagName('parsererror').length) throw error('el archivo no es un SVG válido')
  for (const [tag, que] of Object.entries(NO_SOPORTADO)) {
    const hay = [...doc.getElementsByTagName('*')].some((e) => e.localName === tag && !(tag === 'text' && !e.textContent.trim()))
    if (hay) throw error(`el SVG trae ${que}, que no se puede convertir acá: exportalo como PDF desde Illustrator`)
  }
  const vb = numeros(svg.getAttribute('viewBox'))
  let W = largo(svg.getAttribute('width'), null), H = largo(svg.getAttribute('height'), null)
  if (vb.length === 4) { if (W === null) W = vb[2]; if (H === null) H = vb[3] }
  if (!(W > 0) || !(H > 0)) { W = W > 0 ? W : 612; H = H > 0 ? H : 792 }
  // viewBox → página (preserveAspectRatio por defecto: xMidYMid meet) y el eje y dado vuelta
  let base = [1, 0, 0, -1, 0, H]
  if (vb.length === 4 && vb[2] > 0 && vb[3] > 0) {
    const s = Math.min(W / vb[2], H / vb[3])
    const tx = (W - vb[2] * s) / 2 - vb[0] * s, ty = (H - vb[3] * s) / 2 - vb[1] * s
    base = mul([s, 0, 0, s, tx, ty], base)
  }
  const reglas = [...doc.getElementsByTagName('*')].filter((e) => e.localName === 'style').flatMap((e) => reglasCss(e.textContent))
  const porId = new Map([...doc.getElementsByTagName('*')].filter((e) => e.getAttribute('id')).map((e) => [e.getAttribute('id'), e]))
  const gstates = new Map()                                // "ca|CA" → nombre del ExtGState
  const gs = (ca, CA) => {
    const k = `${n4(ca)}|${n4(CA)}`
    if (!gstates.has(k)) gstates.set(k, { nombre: `GS${gstates.size}`, ca, CA })
    return gstates.get(k).nombre
  }
  let cont = ''
  let pintado = 0

  const recorte = (el, m, est) => {
    // clip-path="url(#id)": la unión de las figuras del <clipPath> (en su propio espacio)
    const ref = String(est['clip-path'] || '').match(/url\(\s*#([^)\s]+)\s*\)/)
    if (!ref) return ''
    const cp = porId.get(ref[1])
    if (!cp || cp.localName !== 'clipPath') return ''
    if ((cp.getAttribute('clipPathUnits') || '') === 'objectBoundingBox') throw error('el SVG usa recortes relativos al objeto')
    let s = ''
    const juntar = (nodo, mm) => {
      for (const h of nodo.children) {
        const mh = mul(transformDe(h.getAttribute('transform')), mm)
        if (h.localName === 'use') { const u = porId.get((h.getAttribute('href') || h.getAttribute('xlink:href') || '').replace(/^#/, '')); if (u) juntar({ children: [u] }, mul([1, 0, 0, 1, largo(h.getAttribute('x'), 0), largo(h.getAttribute('y'), 0)], mh)) }
        else if (h.localName === 'g') juntar(h, mh)
        else s += opsTrazado(figura(h), mh)
      }
    }
    juntar(cp, mul(transformDe(cp.getAttribute('transform')), m))
    if (!s) return ''
    const par = (est['clip-rule'] || 'nonzero') === 'evenodd' ? 'W*' : 'W'
    return `${s}${par} n\n`
  }

  const pintar = (cmds, m, est) => {
    if (!cmds.length) return
    const fill = color(est.fill === undefined ? '#000000' : est.fill)
    const stroke = color(est.stroke === undefined ? 'none' : est.stroke)
    const rellena = fill !== null && fill !== undefined
    const traza = stroke !== null && stroke !== undefined && (largo(est['stroke-width'], 1) || 0) > 0
    if (!rellena && !traza) return
    const op = (est.opacityTotal ?? 1)
    const ca = op * (est['fill-opacity'] !== undefined ? parseFloat(est['fill-opacity']) : 1)
    const CA = op * (est['stroke-opacity'] !== undefined ? parseFloat(est['stroke-opacity']) : 1)
    let s = 'q\n'
    if ((rellena && ca < 1) || (traza && CA < 1)) s += `/${gs(Math.max(0, Math.min(1, ca)), Math.max(0, Math.min(1, CA)))} gs\n`
    if (rellena) s += `${fill.map(n4).join(' ')} rg\n`
    if (traza) {
      // el grosor va en el espacio del objeto: se pinta con su propia matriz (`cm`) para que un
      // `scale` no deforme el trazo distinto que el relleno
      s += `${stroke.map(n4).join(' ')} RG\n${n4(largo(est['stroke-width'], 1))} w\n`
      const lj = { miter: 0, round: 1, bevel: 2 }[est['stroke-linejoin']]; if (lj !== undefined) s += `${lj} j\n`
      const lc = { butt: 0, round: 1, square: 2 }[est['stroke-linecap']]; if (lc !== undefined) s += `${lc} J\n`
      if (est['stroke-miterlimit'] !== undefined) s += `${n4(parseFloat(est['stroke-miterlimit']) || 4)} M\n`
      else s += '4 M\n'
    }
    s += `${m.map(n4).join(' ')} cm\n${opsTrazado(cmds, ID)}`
    const eo = (est['fill-rule'] || 'nonzero') === 'evenodd'
    s += rellena && traza ? (eo ? 'B*\n' : 'B\n') : rellena ? (eo ? 'f*\n' : 'f\n') : 'S\n'
    s += 'Q\n'
    cont += s
    pintado++
  }

  const recorrer = (el, m, est, prof = 0) => {
    if (prof > 64) throw error('el SVG anida demasiados grupos (¿un <use> que se llama a sí mismo?)')
    const nombre = el.localName
    if (['defs', 'clipPath', 'symbol', 'style', 'title', 'desc', 'metadata', 'marker'].includes(nombre) && prof > 0) return
    const e = estiloDe(el, reglas, est)
    if (e.display === 'none' || e.visibility === 'hidden') return
    if (e.mask || e.filter) throw error('el SVG usa máscaras o filtros, que no se pueden convertir acá: exportalo como PDF')
    let mm = prof === 0 ? m : mul(transformDe(el.getAttribute('transform')), m)
    const clip = recorte(el, mm, e)
    if (clip) cont += `q\n${clip}`
    if (nombre === 'svg' || nombre === 'g' || nombre === 'a' || nombre === 'switch') {
      for (const h of el.children) recorrer(h, mm, e, prof + 1)
    } else if (nombre === 'use') {
      const u = porId.get((el.getAttribute('href') || el.getAttribute('xlink:href') || '').replace(/^#/, ''))
      if (u) {
        const mu = mul([1, 0, 0, 1, largo(el.getAttribute('x'), 0), largo(el.getAttribute('y'), 0)], mm)
        if (u.localName === 'symbol') for (const h of u.children) recorrer(h, mu, e, prof + 1)
        else recorrer(u, mul(transformDe(u.getAttribute('transform')), mu), e, prof + 1)
      }
    } else {
      pintar(figura(el), mm, e)
    }
    if (clip) cont += 'Q\n'
  }
  recorrer(svg, base, { fill: '#000000', opacityTotal: 1 })
  if (!pintado) throw error('el SVG no tiene nada que dibujar')

  // ── el PDF, a mano: catálogo, páginas, una página, su contenido y los ExtGState ──
  const objs = []
  const agregar = (s) => { objs.push(s); return objs.length }
  const idCont = agregar(null)
  const gsDict = [...gstates.values()].map((g) => `/${g.nombre} << /Type /ExtGState /ca ${n4(g.ca)} /CA ${n4(g.CA)} >>`).join(' ')
  const idPag = agregar(null)
  const idPags = agregar(`<< /Type /Pages /Kids [${idPag} 0 R] /Count 1 >>`)
  objs[idPag - 1] = `<< /Type /Page /Parent ${idPags} 0 R /MediaBox [0 0 ${n4(W)} ${n4(H)}] /Contents ${idCont} 0 R /Resources << ${gsDict ? `/ExtGState << ${gsDict} >>` : ''} >> >>`
  const idCat = agregar(`<< /Type /Catalog /Pages ${idPags} 0 R >>`)
  const bytesCont = new TextEncoder().encode(cont)
  const partes = []
  let pos = 0
  const offs = []
  const push = (u8) => { partes.push(u8); pos += u8.length }
  const enc = new TextEncoder()
  push(enc.encode('%PDF-1.6\n%\xE2\xE3\xCF\xD3\n'))
  for (let i = 0; i < objs.length; i++) {
    offs.push(pos)
    if (i + 1 === idCont) {
      push(enc.encode(`${i + 1} 0 obj\n<< /Length ${bytesCont.length} >>\nstream\n`))
      push(bytesCont)
      push(enc.encode('\nendstream\nendobj\n'))
    } else {
      push(enc.encode(`${i + 1} 0 obj\n${objs[i]}\nendobj\n`))
    }
  }
  const xref = pos
  let x = `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n`
  for (const o of offs) x += `${String(o).padStart(10, '0')} 00000 n \n`
  x += `trailer\n<< /Size ${objs.length + 1} /Root ${idCat} 0 R >>\nstartxref\n${xref}\n%%EOF\n`
  push(enc.encode(x))
  const pdf = new Uint8Array(pos)
  let k = 0
  for (const p of partes) { pdf.set(p, k); k += p.length }
  return { pdf, w_pt: W, h_pt: H }
}
