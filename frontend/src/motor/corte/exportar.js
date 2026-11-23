// LA MESA DE CORTE EN LOS FORMATOS DE LAS MÁQUINAS (MAPA 816) — DXF 2000, AI (Illustrator 3), PLT (HPGL),
// SVG y EPS. Pedido del usuario 2026-11-23: «la descarga de la tizada debe poder bajarse aparte del PDF en
// formatos actuales y viejos para máquinas de corte láser, y también Illustrator 3; se elige al descargar».
//
// DE DÓNDE SALE: de la MISMA hoja que se ve en pantalla (la tizada para corte: cada pieza en blanco con su
// línea de corte y su etiqueta). La página se pasa por el escritor SVG de MuPDF con el texto como trazado
// (`svgDePagina`, el mismo de la vista previa) y de ahí se leen dos cosas:
//   · CORTE    — cada trazo lleno de la hoja (el borde de corte de cada pieza ES el contorno de la pieza);
//   · ETIQUETA — cada letra de la etiqueta (las `<use>` de los glifos), ya en curvas.
// Lo demás se descarta: rellenos (los rótulos «Talle …» de la línea punteada van en curvas rellenas), los
// trazos punteados (esa línea) y todo lo que esté dentro de un `<clipPath>`/`<mask>`.
// Coordenadas: milímetros reales, escala 1:1, origen abajo a la izquierda (y hacia arriba), salvo el SVG.
//
// 🔴 LAS CURVAS SALEN EXACTAS donde el formato tiene curvas (DXF 2000 = SPLINE, AI, EPS, SVG = Bézier).
// El PLT (HPGL) no tiene curvas: ahí cada curva se reparte en tramos rectos de 0,02 mm de error como máximo.
import { svgDePagina } from '../pieza/svg.js'

const PT_MM = 25.4 / 72
const TOL_MM = 0.02                     // error máximo al aplanar una curva (sólo PLT)
const r4 = (v) => { const s = (Math.round(v * 10000) / 10000).toFixed(4); return s === '-0.0000' ? '0.0000' : s }

export { FORMATOS_CORTE } from './formatos.js'

// ─── leer el SVG de MuPDF ─────────────────────────────────────────────────────────────────────────

const mult = (A, B) => [A[0] * B[0] + A[2] * B[1], A[1] * B[0] + A[3] * B[1], A[0] * B[2] + A[2] * B[3],
                        A[1] * B[2] + A[3] * B[3], A[0] * B[4] + A[2] * B[5] + A[4], A[1] * B[4] + A[3] * B[5] + A[5]]
const ID = [1, 0, 0, 1, 0, 0]

/** `transform="matrix(…) translate(…) scale(…)"` → matriz [a b c d e f]. */
export function leerTransform(t) {
  let M = ID
  if (!t) return M
  const re = /(matrix|translate|scale)\s*\(([^)]*)\)/g
  let m
  while ((m = re.exec(t))) {
    const v = m[2].trim().split(/[\s,]+/).map(Number)
    let T = ID
    if (m[1] === 'matrix') T = v
    else if (m[1] === 'translate') T = [1, 0, 0, 1, v[0] || 0, v[1] || 0]
    else if (m[1] === 'scale') T = [v[0], 0, 0, v.length > 1 ? v[1] : v[0], 0, 0]
    M = mult(M, T)
  }
  return M
}

const atributo = (tag, nombre) => {
  const m = tag.match(new RegExp(`\\s${nombre}="([^"]*)"`))
  return m ? m[1] : null
}

/**
 * `d` de un path → subtrazos `[{cerrado, segs: [['M',x,y] | ['L',x,y] | ['C',x1,y1,x2,y2,x,y]]}]`.
 * MuPDF escribe M/L/H/V/C/Z absolutos y números pegados («.5-.2»); también se aceptan los relativos.
 */
export function leerD(d) {
  const tok = d.match(/[MmLlHhVvCcZzSsQqTtAa]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?/g) || []
  const subs = []
  let cur = null, cmd = null, x = 0, y = 0, x0 = 0, y0 = 0, i = 0
  const n = () => Number(tok[i++])
  while (i < tok.length) {
    if (/[a-zA-Z]/.test(tok[i])) cmd = tok[i++]
    const rel = cmd === cmd.toLowerCase()
    const C = cmd.toUpperCase()
    if (C === 'Z') {
      if (cur) { cur.cerrado = true; x = x0; y = y0 }
      cur = null
      continue
    }
    if (C === 'M') {
      x = (rel ? x : 0) + n(); y = (rel ? y : 0) + n(); x0 = x; y0 = y
      cur = { cerrado: false, segs: [['M', x, y]] }; subs.push(cur)
      cmd = rel ? 'l' : 'L'                       // pares siguientes = líneas
    } else if (C === 'L') {
      x = (rel ? x : 0) + n(); y = (rel ? y : 0) + n(); cur.segs.push(['L', x, y])
    } else if (C === 'H') {
      x = (rel ? x : 0) + n(); cur.segs.push(['L', x, y])
    } else if (C === 'V') {
      y = (rel ? y : 0) + n(); cur.segs.push(['L', x, y])
    } else if (C === 'C') {
      const bx = rel ? x : 0, by = rel ? y : 0
      const x1 = bx + n(), y1 = by + n(), x2 = bx + n(), y2 = by + n()
      x = bx + n(); y = by + n()
      cur.segs.push(['C', x1, y1, x2, y2, x, y])
    } else {
      throw new Error(`el trazado trae «${cmd}», que la exportación de corte no sabe leer`)
    }
    if (!cur) throw new Error('trazado sin punto de inicio')
  }
  return subs
}

const aplicar = (M, s) => ({
  cerrado: s.cerrado,
  segs: s.segs.map((g) => {
    const out = [g[0]]
    for (let k = 1; k < g.length; k += 2) out.push(M[0] * g[k] + M[2] * g[k + 1] + M[4], M[1] * g[k] + M[3] * g[k + 1] + M[5])
    return out
  }),
})

/**
 * El SVG de una mesa → `{ anchoMm, altoMm, corte, etiqueta }` (subtrazos en mm, y hacia ARRIBA).
 * `escala` = puntos reales por unidad del SVG (1, o el /UserUnit de una mesa de más de 5,08 m).
 */
export function geometriaDeSvg(svg, escala = 1) {
  const vb = (atributo(svg.slice(0, 2000), 'viewBox') || '').split(/[\s,]+/).map(Number)
  const W = vb.length === 4 ? vb[2] : Number(atributo(svg.slice(0, 2000), 'width'))
  const H = vb.length === 4 ? vb[3] : Number(atributo(svg.slice(0, 2000), 'height'))
  const k = escala * PT_MM
  const aMm = (s) => ({ cerrado: s.cerrado, segs: s.segs.map((g) => { const o = [g[0]]; for (let j = 1; j < g.length; j += 2) o.push(g[j] * k, (H - g[j + 1]) * k); return o }) })
  // los glifos: <path id="font_…" d="…"/> dentro de <defs>
  const glifos = new Map()
  for (const m of svg.matchAll(/<path\s+id="(font_[^"]+)"\s+d="([^"]*)"/g)) glifos.set(m[1], m[2])
  // 🔴 LA ETIQUETA DEL SISTEMA VA EN CURVAS (`estampar.js`): cada letra es un RELLENO y, con «borde» de
  // etiqueta, el MISMO dibujo además TRAZADO (el halo). Ese halo no es una línea de corte: un trazo que
  // tiene su gemelo relleno (mismo dibujo, misma posición) es una letra. Por eso se junta todo primero.
  const trazos = [], rellenos = [], rellenosClave = new Set()
  const pila = [ID]
  let oculto = 0                                // dentro de clipPath / mask / defs / symbol
  const re = /<(\/?)(g|path|use|clipPath|mask|defs|symbol)\b([^>]*?)(\/?)>/g
  let m
  while ((m = re.exec(svg))) {
    const [, cierra, tag, attrs, sola] = m
    const t = ' ' + attrs
    if (tag === 'clipPath' || tag === 'mask' || tag === 'defs' || tag === 'symbol') {
      if (cierra) oculto = Math.max(0, oculto - 1)
      else if (!sola) oculto++
      continue
    }
    if (tag === 'g') {
      if (cierra) { if (pila.length > 1) pila.pop() } else if (!sola) pila.push(mult(pila[pila.length - 1], leerTransform(atributo(t, 'transform'))))
      continue
    }
    if (cierra || oculto) continue
    const M = mult(pila[pila.length - 1], leerTransform(atributo(t, 'transform')))
    if (tag === 'use') {
      // un texto de verdad (no curvas): sus glifos son letras de la etiqueta
      const id = (atributo(t, 'xlink:href') || atributo(t, 'href') || '').replace(/^#/, '')
      const d = glifos.get(id)
      if (d) rellenos.push({ M, d })
      continue
    }
    const d = atributo(t, 'd')
    if (!d) continue
    const clave = M.map((v) => v.toFixed(3)).join(',') + '|' + d
    const fill = atributo(t, 'fill'), stroke = atributo(t, 'stroke')
    if (fill && fill !== 'none') { rellenos.push({ M, d }); rellenosClave.add(clave) }
    // un trazo lleno (sin punteado: la línea entre talles de «separados» no se corta)
    if (stroke && stroke !== 'none' && !atributo(t, 'stroke-dasharray')) trazos.push({ M, d, clave })
  }
  const corte = [], etiqueta = [], vistos = new Set()
  for (const r of rellenos) for (const s of leerD(r.d)) etiqueta.push(aMm(aplicar(r.M, s)))
  for (const tr of trazos) {
    if (rellenosClave.has(tr.clave)) continue      // el halo de una letra
    for (const s of leerD(tr.d)) {
      const g = aMm(aplicar(tr.M, s))
      if (g.segs.length < 2) continue
      // el borde «fuera» se dibuja dos veces sobre el mismo contorno: una sola línea de corte
      const cl = g.segs.map((x) => x.slice(1).map((v) => v.toFixed(2)).join(',')).join(';')
      if (vistos.has(cl)) continue
      vistos.add(cl)
      corte.push(g)
    }
  }
  return { anchoMm: W * k, altoMm: H * k, corte, etiqueta }
}

/** Página `pi` de la hoja (bytes del PDF) → geometría en mm. */
export function geometriaDeHoja(mupdf, bytes, pi = 0) {
  const doc = mupdf.Document.openDocument(bytes, 'application/pdf')
  try {
    const pdf = doc.asPDF ? doc.asPDF() : doc
    let uu = 1
    try {
      const v = pdf.findPage(pi).get('UserUnit')
      if (v && v.isNumber && v.isNumber()) uu = Number(v.asNumber()) || 1
    } catch { uu = 1 }
    const svg = svgDePagina(mupdf, doc, pi)
    // MuPDF ya puede venir aplicando el /UserUnit a la página: se mide contra el MediaBox real
    let escala = 1
    try {
      const mb = pdf.findPage(pi).get('MediaBox')
      const anchoReal = (Number(mb.get(2).asNumber()) - Number(mb.get(0).asNumber())) * uu
      const vb = (atributo(svg.slice(0, 2000), 'viewBox') || '').split(/[\s,]+/).map(Number)
      if (vb.length === 4 && vb[2] > 0) escala = anchoReal / vb[2]
    } catch { escala = uu }
    return geometriaDeSvg(svg, escala)
  } finally {
    try { doc.destroy() } catch { /* nada */ }
  }
}

// ─── curvas ───────────────────────────────────────────────────────────────────────────────────────

/** Una cúbica en tramos rectos con error ≤ `tol` (subdivisión adaptativa). */
function aplanarCubica(p0x, p0y, x1, y1, x2, y2, x3, y3, tol, out, prof = 0) {
  const dx = x3 - p0x, dy = y3 - p0y
  const d2 = Math.abs((x1 - x3) * dy - (y1 - y3) * dx), d3 = Math.abs((x2 - x3) * dy - (y2 - y3) * dx)
  const l2 = dx * dx + dy * dy
  if (prof > 16 || ((d2 + d3) * (d2 + d3) <= tol * tol * l2 * 16) || (l2 < 1e-12 && Math.hypot(x1 - p0x, y1 - p0y) + Math.hypot(x2 - p0x, y2 - p0y) < tol)) {
    out.push([x3, y3]); return
  }
  const ax = (p0x + x1) / 2, ay = (p0y + y1) / 2, bx = (x1 + x2) / 2, by = (y1 + y2) / 2, cx = (x2 + x3) / 2, cy = (y2 + y3) / 2
  const abx = (ax + bx) / 2, aby = (ay + by) / 2, bcx = (bx + cx) / 2, bcy = (by + cy) / 2
  const mx = (abx + bcx) / 2, my = (aby + bcy) / 2
  aplanarCubica(p0x, p0y, ax, ay, abx, aby, mx, my, tol, out, prof + 1)
  aplanarCubica(mx, my, bcx, bcy, cx, cy, x3, y3, tol, out, prof + 1)
}

/** Subtrazo → puntos (las curvas aplanadas). */
export function puntosDe(s, tol = TOL_MM) {
  const out = []
  let px = 0, py = 0
  for (const g of s.segs) {
    if (g[0] === 'M' || g[0] === 'L') { out.push([g[1], g[2]]); px = g[1]; py = g[2] } else {
      aplanarCubica(px, py, g[1], g[2], g[3], g[4], g[5], g[6], tol, out); px = g[5]; py = g[6]
    }
  }
  if (s.cerrado && out.length && (out[0][0] !== px || out[0][1] !== py)) out.push([out[0][0], out[0][1]])
  return out
}

/** Subtrazo → sólo cúbicas (una recta = cúbica con los controles a 1/3 y 2/3), cerrado si lo estaba. */
function comoCubicas(s) {
  const p = [], segs = []
  let px = 0, py = 0, sx = 0, sy = 0
  for (const g of s.segs) {
    if (g[0] === 'M') { px = sx = g[1]; py = sy = g[2]; p.push([px, py]) } else if (g[0] === 'L') {
      segs.push([px + (g[1] - px) / 3, py + (g[2] - py) / 3, px + 2 * (g[1] - px) / 3, py + 2 * (g[2] - py) / 3, g[1], g[2]])
      px = g[1]; py = g[2]
    } else { segs.push(g.slice(1)); px = g[5]; py = g[6] }
  }
  if (s.cerrado && (px !== sx || py !== sy)) {
    segs.push([px + (sx - px) / 3, py + (sy - py) / 3, px + 2 * (sx - px) / 3, py + 2 * (sy - py) / 3, sx, sy])
  }
  return { inicio: p[0] || [0, 0], segs }
}

const soloRectas = (s) => s.segs.every((g) => g[0] !== 'C')

// ─── los formatos ─────────────────────────────────────────────────────────────────────────────────

/** SVG: dos capas («Corte» en rojo, «Etiqueta» en azul), en milímetros. */
export function aSvg(geo, { etiqueta = true } = {}) {
  const H = geo.altoMm
  const d = (lista) => lista.map((s) => s.segs.map((g) => g[0] === 'C'
    ? `C${r4(g[1])} ${r4(H - g[2])} ${r4(g[3])} ${r4(H - g[4])} ${r4(g[5])} ${r4(H - g[6])}`
    : `${g[0]}${r4(g[1])} ${r4(H - g[2])}`).join('') + (s.cerrado ? 'Z' : '')).join('')
  const capa = (id, estilo, lista) => (lista.length
    ? `<g id="${id}" inkscape:groupmode="layer" inkscape:label="${id}" ${estilo}><path d="${d(lista)}"/></g>\n` : '')
  return `<?xml version="1.0" encoding="UTF-8"?>\n` +
    `<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" version="1.1" ` +
    `width="${r4(geo.anchoMm)}mm" height="${r4(H)}mm" viewBox="0 0 ${r4(geo.anchoMm)} ${r4(H)}">\n` +
    capa('Corte', 'fill="none" stroke="#ff0000" stroke-width="0.1"', geo.corte) +
    (etiqueta ? capa('Etiqueta', 'fill="#0000ff" fill-rule="nonzero" stroke="none"', geo.etiqueta) : '') +
    '</svg>\n'
}

/** Los operadores de PostScript de un subtrazo (en puntos). */
function psTrazo(s, op = { m: 'moveto', l: 'lineto', c: 'curveto', h: 'closepath' }) {
  const p = (v) => r4(v / PT_MM)
  let o = ''
  for (const g of s.segs) {
    if (g[0] === 'M') o += `${p(g[1])} ${p(g[2])} ${op.m}\n`
    else if (g[0] === 'L') o += `${p(g[1])} ${p(g[2])} ${op.l}\n`
    else o += `${p(g[1])} ${p(g[2])} ${p(g[3])} ${p(g[4])} ${p(g[5])} ${p(g[6])} ${op.c}\n`
  }
  if (s.cerrado && op.h) o += `${op.h}\n`
  return o
}

const cajaPt = (geo) => [Math.ceil(geo.anchoMm / PT_MM), Math.ceil(geo.altoMm / PT_MM)]

/** EPS (PostScript nivel 2): la línea de corte en rojo de 0,1 mm, la etiqueta rellena en azul. */
export function aEps(geo, { etiqueta = true, titulo = 'mesa' } = {}) {
  const [w, h] = cajaPt(geo)
  let o = '%!PS-Adobe-3.0 EPSF-3.0\n' +
    `%%BoundingBox: 0 0 ${w} ${h}\n%%HiResBoundingBox: 0 0 ${r4(geo.anchoMm / PT_MM)} ${r4(geo.altoMm / PT_MM)}\n` +
    `%%Title: ${titulo.replace(/[()\\\r\n]/g, ' ')}\n%%Creator: TIZADA PRO\n%%DocumentProcessColors: Cyan Magenta Yellow\n` +
    '%%LanguageLevel: 2\n%%Pages: 1\n%%EndComments\n%%BeginProlog\n%%EndProlog\n%%Page: 1 1\n' +
    'gsave\n0 1 1 0 setcmykcolor\n' + r4(0.1 / PT_MM) + ' setlinewidth\n0 setlinejoin\n0 setlinecap\n'
  for (const s of geo.corte) o += 'newpath\n' + psTrazo(s) + 'stroke\n'
  if (etiqueta && geo.etiqueta.length) {
    o += '1 1 0 0 setcmykcolor\nnewpath\n'
    for (const s of geo.etiqueta) o += psTrazo(s)
    o += 'fill\n'
  }
  return o + 'grestore\nshowpage\n%%Trailer\n%%EOF\n'
}

/**
 * AI de Illustrator 3 (el formato de texto de Adobe Illustrator 3.x, que leen las máquinas láser
 * viejas): grupos `u … U`, trazo CMYK `K`, relleno `k`, `m`/`L`/`C`, `S`/`s` trazo, `f` relleno; las
 * letras con agujeros van como trazado compuesto `*u … *U`.
 */
export function aAi3(geo, { etiqueta = true, titulo = 'mesa' } = {}) {
  const [w, h] = cajaPt(geo)
  const t = titulo.replace(/[()\\\r\n]/g, ' ')
  let o = '%!PS-Adobe-2.0 EPSF-1.2\n%%Creator:Adobe Illustrator(TM) 3.2\n' +
    `%%Title:${t}\n%%For:TIZADA PRO\n%%BoundingBox:0 0 ${w} ${h}\n%%HiResBoundingBox:0 0 ${r4(geo.anchoMm / PT_MM)} ${r4(geo.altoMm / PT_MM)}\n` +
    `%%TemplateBox:${Math.round(w / 2)} ${Math.round(h / 2)} ${Math.round(w / 2)} ${Math.round(h / 2)}\n` +
    '%%DocumentProcessColors: Cyan Magenta Yellow\n%AI3_ColorUsage: Color\n' +
    `%AI3_TemplateBox:${Math.round(w / 2)} ${Math.round(h / 2)} ${Math.round(w / 2)} ${Math.round(h / 2)}\n` +
    `%AI3_TileBox:0 0 ${w} ${h}\n%AI3_DocumentPreview: None\n%%EndComments\n%%EndProlog\n%%BeginSetup\n%%EndSetup\n`
  const ai = (s) => psTrazo(s, { m: 'm', l: 'L', c: 'C', h: null })
  o += 'u\n0 1 1 0 K\n' + r4(0.1 / PT_MM) + ' w\n0 j\n0 J\n4 M\n[]0 d\n'
  for (const s of geo.corte) o += ai(s) + (s.cerrado ? 's\n' : 'S\n')
  o += 'U\n'
  if (etiqueta && geo.etiqueta.length) {
    o += 'u\n1 1 0 0 k\n*u\n'
    for (const s of geo.etiqueta) o += ai(s) + 'f\n'
    o += '*U\nU\n'
  }
  return o + '%%PageTrailer\ngsave annotatepage grestore showpage\n%%Trailer\n%%EOF\n'
}

/** PLT (HPGL): pluma 1 = corte, pluma 2 = etiqueta; 40 unidades por mm (0,025 mm). */
export function aPlt(geo, { etiqueta = true } = {}) {
  const u = (v) => Math.round(v * 40)
  let o = 'IN;PA;SP1;\n'
  const trazos = (lista) => {
    for (const s of lista) {
      const pts = puntosDe(s)
      if (pts.length < 2) continue
      o += `PU${u(pts[0][0])},${u(pts[0][1])};PD${pts.slice(1).map((p) => `${u(p[0])},${u(p[1])}`).join(',')};\n`
    }
  }
  trazos(geo.corte)
  if (etiqueta && geo.etiqueta.length) { o += 'PU;SP2;\n'; trazos(geo.etiqueta) }
  return o + 'PU;SP0;\n'
}

/**
 * DXF 2000 (AC1015), en milímetros: capas «Corte» (rojo) y «Etiqueta» (azul). Un contorno sólo de rectas
 * es una LWPOLYLINE cerrada; uno con curvas, una SPLINE de grado 3 exacta (cada Bézier es un tramo, con
 * los nudos repetidos tres veces). Con la estructura que pide AutoCAD 2000: identificadores, tabla
 * BLOCK_RECORD, el espacio modelo y el diccionario raíz.
 */
export function aDxf(geo, { etiqueta = true } = {}) {
  let h = 0x30
  const hx = () => (h++).toString(16).toUpperCase()
  const L = []
  const g = (c, v) => { L.push(String(c), String(v)) }
  const ms = '1F', ps = '1B'                       // BLOCK_RECORD del espacio modelo y del papel
  // ── HEADER ──
  g(0, 'SECTION'); g(2, 'HEADER')
  g(9, '$ACADVER'); g(1, 'AC1015')
  g(9, '$INSBASE'); g(10, 0); g(20, 0); g(30, 0)
  g(9, '$EXTMIN'); g(10, 0); g(20, 0); g(30, 0)
  g(9, '$EXTMAX'); g(10, r4(geo.anchoMm)); g(20, r4(geo.altoMm)); g(30, 0)
  g(9, '$LIMMIN'); g(10, 0); g(20, 0)
  g(9, '$LIMMAX'); g(10, r4(geo.anchoMm)); g(20, r4(geo.altoMm))
  g(9, '$INSUNITS'); g(70, 4)
  g(9, '$MEASUREMENT'); g(70, 1)
  const iSeed = L.length; g(9, '$HANDSEED'); g(5, 'FFFF')
  g(0, 'ENDSEC')
  // ── CLASSES ──
  g(0, 'SECTION'); g(2, 'CLASSES'); g(0, 'ENDSEC')
  // ── TABLES ──
  g(0, 'SECTION'); g(2, 'TABLES')
  const tabla = (nombre, hnd, n) => { g(0, 'TABLE'); g(2, nombre); g(5, hnd); g(330, 0); g(100, 'AcDbSymbolTable'); g(70, n) }
  tabla('VPORT', '8', 1)
  g(0, 'VPORT'); g(5, hx()); g(330, '8'); g(100, 'AcDbSymbolTableRecord'); g(100, 'AcDbViewportTableRecord'); g(2, '*Active'); g(70, 0)
  g(10, 0); g(20, 0); g(11, 1); g(21, 1); g(12, r4(geo.anchoMm / 2)); g(22, r4(geo.altoMm / 2)); g(13, 0); g(23, 0); g(14, 10); g(24, 10)
  g(15, 10); g(25, 10); g(16, 0); g(26, 0); g(36, 1); g(17, 0); g(27, 0); g(37, 0); g(40, r4(Math.max(geo.altoMm, 1) * 1.1)); g(41, 1.5)
  g(42, 50); g(43, 0); g(44, 0); g(50, 0); g(51, 0); g(71, 0); g(72, 100); g(73, 1); g(74, 3); g(75, 0); g(76, 0); g(77, 0); g(78, 0)
  g(0, 'ENDTAB')
  tabla('LTYPE', '5', 3)
  for (const [nom, hd] of [['ByBlock', '14'], ['ByLayer', '15'], ['Continuous', '16']]) {
    g(0, 'LTYPE'); g(5, hd); g(330, '5'); g(100, 'AcDbSymbolTableRecord'); g(100, 'AcDbLinetypeTableRecord'); g(2, nom); g(70, 0)
    g(3, nom === 'Continuous' ? 'Solid line' : ''); g(72, 65); g(73, 0); g(40, 0)
  }
  g(0, 'ENDTAB')
  const capas = [['0', 7], ['Corte', 1]].concat(etiqueta ? [['Etiqueta', 5]] : [])
  tabla('LAYER', '2', capas.length)
  for (const [nom, col] of capas) {
    g(0, 'LAYER'); g(5, hx()); g(330, '2'); g(100, 'AcDbSymbolTableRecord'); g(100, 'AcDbLayerTableRecord'); g(2, nom); g(70, 0)
    g(62, col); g(6, 'Continuous'); g(370, -3); g(390, 'F')
  }
  g(0, 'ENDTAB')
  tabla('STYLE', '3', 1)
  g(0, 'STYLE'); g(5, '11'); g(330, '3'); g(100, 'AcDbSymbolTableRecord'); g(100, 'AcDbTextStyleTableRecord'); g(2, 'Standard'); g(70, 0)
  g(40, 0); g(41, 1); g(50, 0); g(71, 0); g(42, 2.5); g(3, 'txt'); g(4, '')
  g(0, 'ENDTAB')
  tabla('VIEW', '6', 0); g(0, 'ENDTAB')
  tabla('UCS', '7', 0); g(0, 'ENDTAB')
  tabla('APPID', '9', 1)
  g(0, 'APPID'); g(5, '12'); g(330, '9'); g(100, 'AcDbSymbolTableRecord'); g(100, 'AcDbRegAppTableRecord'); g(2, 'ACAD'); g(70, 0)
  g(0, 'ENDTAB')
  g(0, 'TABLE'); g(2, 'DIMSTYLE'); g(5, 'A'); g(330, 0); g(100, 'AcDbSymbolTable'); g(70, 1); g(100, 'AcDbDimStyleTable'); g(71, 0)
  g(0, 'DIMSTYLE'); g(105, '27'); g(330, 'A'); g(100, 'AcDbSymbolTableRecord'); g(100, 'AcDbDimStyleTableRecord'); g(2, 'Standard'); g(70, 0)
  g(0, 'ENDTAB')
  tabla('BLOCK_RECORD', '1', 2)
  g(0, 'BLOCK_RECORD'); g(5, ms); g(330, '1'); g(100, 'AcDbSymbolTableRecord'); g(100, 'AcDbBlockTableRecord'); g(2, '*Model_Space')
  g(0, 'BLOCK_RECORD'); g(5, ps); g(330, '1'); g(100, 'AcDbSymbolTableRecord'); g(100, 'AcDbBlockTableRecord'); g(2, '*Paper_Space')
  g(0, 'ENDTAB')
  g(0, 'ENDSEC')
  // ── BLOCKS ──
  g(0, 'SECTION'); g(2, 'BLOCKS')
  for (const [nom, br, hb, he] of [['*Model_Space', ms, '20', '21'], ['*Paper_Space', ps, '1C', '1D']]) {
    g(0, 'BLOCK'); g(5, hb); g(330, br); g(100, 'AcDbEntity'); if (nom === '*Paper_Space') g(67, 1); g(8, '0'); g(100, 'AcDbBlockBegin')
    g(2, nom); g(70, 0); g(10, 0); g(20, 0); g(30, 0); g(3, nom); g(1, '')
    g(0, 'ENDBLK'); g(5, he); g(330, br); g(100, 'AcDbEntity'); if (nom === '*Paper_Space') g(67, 1); g(8, '0'); g(100, 'AcDbBlockEnd')
  }
  g(0, 'ENDSEC')
  // ── ENTITIES ──
  g(0, 'SECTION'); g(2, 'ENTITIES')
  const entidad = (s, capa) => {
    if (soloRectas(s)) {
      const pts = s.segs.map((x) => [x[1], x[2]])
      const cerr = s.cerrado || (pts.length > 2 && pts[0][0] === pts[pts.length - 1][0] && pts[0][1] === pts[pts.length - 1][1])
      if (cerr && pts.length > 1 && pts[0][0] === pts[pts.length - 1][0] && pts[0][1] === pts[pts.length - 1][1]) pts.pop()
      if (pts.length < 2) return
      g(0, 'LWPOLYLINE'); g(5, hx()); g(330, ms); g(100, 'AcDbEntity'); g(8, capa); g(100, 'AcDbPolyline')
      g(90, pts.length); g(70, cerr ? 1 : 0); g(43, 0)
      for (const p of pts) { g(10, r4(p[0])); g(20, r4(p[1])) }
      return
    }
    const { inicio, segs } = comoCubicas(s)
    if (!segs.length) return
    const n = segs.length
    const nudos = [0, 0, 0, 0]
    for (let i = 1; i < n; i++) nudos.push(i, i, i)
    nudos.push(n, n, n, n)
    const ctrl = [inicio]
    for (const c of segs) ctrl.push([c[0], c[1]], [c[2], c[3]], [c[4], c[5]])
    g(0, 'SPLINE'); g(5, hx()); g(330, ms); g(100, 'AcDbEntity'); g(8, capa); g(100, 'AcDbSpline')
    g(210, 0); g(220, 0); g(230, 1)
    g(70, 8 + (s.cerrado ? 1 : 0)); g(71, 3); g(72, nudos.length); g(73, ctrl.length); g(74, 0)
    g(42, '0.0000000001'); g(43, '0.0000000001')
    for (const k of nudos) g(40, k)
    for (const p of ctrl) { g(10, r4(p[0])); g(20, r4(p[1])); g(30, 0) }
  }
  for (const s of geo.corte) entidad(s, 'Corte')
  if (etiqueta) for (const s of geo.etiqueta) entidad(s, 'Etiqueta')
  g(0, 'ENDSEC')
  // ── OBJECTS: el diccionario raíz ──
  g(0, 'SECTION'); g(2, 'OBJECTS')
  g(0, 'DICTIONARY'); g(5, 'C'); g(330, 0); g(100, 'AcDbDictionary'); g(281, 1); g(3, 'ACAD_GROUP'); g(350, 'D')
  g(0, 'DICTIONARY'); g(5, 'D'); g(330, 'C'); g(100, 'AcDbDictionary'); g(281, 1)
  g(0, 'ENDSEC')
  g(0, 'EOF')
  L[iSeed + 3] = hx()                              // $HANDSEED: el próximo identificador libre
  return L.join('\r\n') + '\r\n'
}

/** Página `pi` de la hoja → bytes del archivo en `formato` (`dxf`, `ai`, `plt`, `svg`, `eps`). */
// 🔴 SÓLO EL MOLDE (regla del usuario 2026-11-23: «en el corte no deben salir las etiquetas, sólo es molde, nada más»): la
// capa de la etiqueta existe en los escritores pero la tizada para corte nunca la pide (`etiqueta` falso siempre).
export function exportarMesa(mupdf, bytes, pi, formato, { etiqueta = false, titulo = 'mesa' } = {}) {
  const geo = geometriaDeHoja(mupdf, bytes, pi)
  if (!geo.corte.length) throw new Error('esta mesa no tiene líneas de corte')
  const txt = formato === 'dxf' ? aDxf(geo, { etiqueta }) : formato === 'ai' ? aAi3(geo, { etiqueta, titulo })
    : formato === 'plt' ? aPlt(geo, { etiqueta }) : formato === 'svg' ? aSvg(geo, { etiqueta })
      : formato === 'eps' ? aEps(geo, { etiqueta, titulo }) : null
  if (txt === null) throw new Error(`formato de corte desconocido: ${formato}`)
  return { bytes: new TextEncoder().encode(txt), piezas: geo.corte.length, letras: geo.etiqueta.length }
}
