// LAS HERRAMIENTAS DEL MOLDE (camino A), EN ESTA COMPUTADORA — 2026-09-22.
//
// 🔴 POR QUÉ: «el servidor será sólo para sostener el sistema y la base; el resto lo hace la PC de
// quien se conectó». Nombrar variantes, partir un molde en variantes por piezas, agregar una pieza,
// el «nido» de tallas y la guía de medidas leían o reescribían el archivo del molde con PyMuPDF y
// pikepdf en el servidor. Acá están las mismas funciones, traducidas línea a línea:
//   · `variantes_molde.py`: `analizar`, `renombrar_capas`, `piezas_para_asignar`,
//     `_unidades_de_trazado`, `separar_por_piezas`;
//   · `piezas_molde.py`: `contornos_de_pdf`, `detectar_por_talle`, `agregar_pieza`,
//     `ops_de_segmentos`;
//   · `motor_pedido.py`: `nido_piezas` (+ `_rotar_segs_90`, `_bbox_segs`, `_segs_a_svg`),
//     `pdf_guia_medidas`, `ai_guia_medidas` (+ `_ai_path`, `_ai_text`, `_ai_layer`).
// Las que reescriben el archivo NO tocan el del usuario: devuelven los bytes de la versión nueva,
// y el servidor la guarda al lado (`plantilla.v<N>.ai`), como siempre.
import { tallesDePlantilla, ordenCapasArchivo, extraerPiezasMesa, detectarPiezas, featsConts, empOffsets, empFijos,
  aplicarFijos, emparejarPorForma, mapaIndices, CAPAS_SISTEMA } from './caminoA.js'
import { contornoDeDrawing, geometriaPagina, CM } from './contornos.js'
import { dibujosDePagina } from '../pdf/dibujos.js'
import { instrucciones, escribir, contenidoCrudo } from '../pdf/contenido.js'
import { pyFixed } from '../py.js'

const nulo = (o) => !o || (o.isNull && o.isNull())
const r1 = (v) => Math.round(v * 10) / 10
const ancho = (r) => Math.max(0, r[2] - r[0])
const alto = (r) => Math.max(0, r[3] - r[1])
const esDibujo = (d) => d.type === 'f' || d.type === 's' || d.type === 'fs'

// ─── variantes_molde.analizar ─────────────────────────────────────────────────────────────────
/** La radiografía del molde para NOMBRAR VARIANTES (misma forma que el Python). */
export function analizarVariantes(molde) {
  const porCapa = new Map()
  for (let i = 1; i <= molde.n; i++) {
    for (const d of molde.dibujos(i)) {
      if (!d.layer || !d.rect) continue
      if (!porCapa.has(d.layer)) porCapa.set(d.layer, [])
      porCapa.get(d.layer).push(d.rect)
    }
  }
  const orden = ordenCapasArchivo(molde)
  const esTalle = new Set(tallesDePlantilla(molde))
  let capas = []
  for (const [nom, rects] of porCapa) {
    const area = rects.reduce((a, r) => a + ancho(r) * alto(r), 0)
    const x0 = Math.min(...rects.map((r) => r[0])), y0 = Math.min(...rects.map((r) => r[1]))
    const x1 = Math.max(...rects.map((r) => r[2])), y1 = Math.max(...rects.map((r) => r[3]))
    capas.push({ capa: nom, piezas: rects.length, area: r1(area), bbox: [r1(x0), r1(y0), r1(x1), r1(y1)],
                 es_talle: esTalle.has(nom), candidata: rects.length > 1 })
  }
  const pos = (c) => { const i = orden.indexOf(c.capa); return i >= 0 ? i : 9999 }
  capas = capas.map((c, i) => [pos(c), i, c]).sort((a, b) => a[0] - b[0] || a[1] - b[1]).map((x) => x[2])
  const talles = capas.filter((c) => c.candidata)
  let formato = 'extendido'
  if (talles.length >= 2) {
    const a = talles[0].bbox, b = talles[1].bbox
    const sx = Math.max(0, Math.min(a[2], b[2]) - Math.max(a[0], b[0]))
    const sy = Math.max(0, Math.min(a[3], b[3]) - Math.max(a[1], b[1]))
    const an = Math.min(a[2] - a[0], b[2] - b[0]) || 1
    const al = Math.min(a[3] - a[1], b[3] - b[1]) || 1
    if (sx / an > 0.7 && sy / al > 0.7) formato = 'anidado'
  }
  const sugerencia = talles.map((c, i) => [c.area, i, c.capa]).sort((a, b) => a[0] - b[0] || a[1] - b[1]).map((x) => x[2])
  return { formato, capas, sugerencia, total_talles: talles.length,
           sin_talles: !capas.some((c) => c.es_talle), una_sola_capa: talles.length === 1 }
}

// ─── variantes_molde.renombrar_capas ──────────────────────────────────────────────────────────
/** Las capas renombradas (`{actual: nuevo}`) → `{bytes, n}` de la versión nueva. */
export function renombrarCapas(mupdf, bytes, mapa) {
  const m = {}
  for (const [k, v] of Object.entries(mapa || {})) if (String(v || '').trim()) m[String(k)] = String(v).trim()
  if (!Object.keys(m).length) throw new Error('no hay nombres para aplicar')
  const nuevos = Object.values(m)
  if (new Set(nuevos).size !== nuevos.length) throw new Error('hay dos variantes con el mismo nombre: cada una tiene que ser única')
  const doc = new mupdf.PDFDocument(bytes)
  try {
    const ocp = doc.getTrailer().get('Root').get('OCProperties')
    if (nulo(ocp)) throw new Error('el molde no tiene capas: no se pueden nombrar las variantes')
    const og = ocp.get('OCGs')
    let n = 0
    for (let i = 0; i < (nulo(og) ? 0 : og.length); i++) {
      const o = og.get(i)
      let nom = ''
      try { nom = o.get('Name').asString() } catch { nom = '' }
      if (Object.prototype.hasOwnProperty.call(m, nom)) { o.put('Name', doc.newString(m[nom])); n++ }
    }
    if (!n) throw new Error('ninguna de esas capas existe en el molde')
    return { bytes: doc.saveToBuffer('compress').asUint8Array().slice(), n }
  } finally { doc.destroy() }
}

// ─── piezas_molde ─────────────────────────────────────────────────────────────────────────────
function itemsComoGetDrawings(items) {
  return (items || []).map((it) => {
    if (it[0] !== 're') return it
    const r = it[1]
    return ['re', [Math.min(r[0], r[2]), Math.min(r[1], r[3]), Math.max(r[0], r[2]), Math.max(r[1], r[3])], it[2]]
  })
}

/** `contornos_de_pdf`: los trazados de la página 1 de un PDF suelto (la pieza que sube el usuario),
 *  en crudas (y arriba), de mayor a menor área. */
export function contornosDePdf(mupdf, bytes) {
  const doc = mupdf.Document.openDocument(bytes, 'application/pdf')
  try {
    const page = doc.loadPage(0)
    try {
      const geo = geometriaPagina(page)
      const conts = []
      for (const d of dibujosDePagina(mupdf, page).filter(esDibujo)) {
        let c = null
        try { c = contornoDeDrawing(itemsComoGetDrawings(d.items), d.rect, geo.cb, 1.0, 1, null) } catch { c = null }
        if (c && c.segmentos && c.segmentos.some((s) => s[0] !== 'h')) conts.push(c)
      }
      return conts.map((c, i) => [c.w * c.h, i, c]).sort((a, b) => b[0] - a[0] || a[1] - b[1]).map((x) => x[2])
    } finally { page.destroy() }
  } finally { doc.destroy() }
}

/** `detectar_por_talle`: `{talle: [contornos]}` (lo mismo que `extraer_piezas_mesa` talle por talle). */
export function detectarPorTalle(molde, mesa, talles) {
  const out = {}
  for (const t of talles) out[t] = extraerPiezasMesa(molde, mesa, t)
  return out
}

/** `ops_de_segmentos`: segmentos crudos → operadores de trazado (SIN dar vuelta la Y). */
export function opsDeSegmentos(segs, dx, dy, u = 1.0) {
  const P = (x, y) => [(x + dx) * u, (y + dy) * u]
  const f = (v) => pyFixed(v, 4)
  const out = []
  for (const s of segs) {
    const op = s[0]
    if (op === 'm') { const [x, y] = P(s[1], s[2]); out.push(`${f(x)} ${f(y)} m`) }
    else if (op === 'l') { const [x, y] = P(s[1], s[2]); out.push(`${f(x)} ${f(y)} l`) }
    else if (op === 'c') {
      const a = P(s[1], s[2]), b = P(s[3], s[4]), c = P(s[5], s[6])
      out.push(`${f(a[0])} ${f(a[1])} ${f(b[0])} ${f(b[1])} ${f(c[0])} ${f(c[1])} c`)
    } else if (op === 're') { const [x, y] = P(s[1], s[2]); out.push(`${f(x)} ${f(y)} ${f(s[3] * u)} ${f(s[4] * u)} re`) }
    else if (op === 'h') out.push('h')
  }
  return out.join('\n')
}

function ocgPorNombre(doc, nombre) {
  const ocp = doc.getTrailer().get('Root').get('OCProperties')
  if (nulo(ocp)) return null
  const og = ocp.get('OCGs')
  for (let i = 0; i < (nulo(og) ? 0 : og.length); i++) {
    try { if (og.get(i).get('Name').asString() === String(nombre)) return og.get(i) } catch { /* sigue */ }
  }
  return null
}
function recursosPropios(doc, pageObj) {
  let res = pageObj.get('Resources')
  if (nulo(res)) {
    const her = pageObj.getInheritable('Resources')
    res = nulo(her) ? doc.newDictionary() : doc.graftObject(her)
    pageObj.put('Resources', res)
  }
  return res
}
function mismoObjeto(a, b) {
  try { return a.isIndirect() && b.isIndirect() && a.asIndirect() === b.asIndirect() } catch { return false }
}
function nombreEnRecursos(doc, pageObj, ocg, sugerido) {
  const res = recursosPropios(doc, pageObj)
  let props = res.get('Properties')
  if (nulo(props)) { props = doc.newDictionary(); res.put('Properties', props) }
  let ya = null
  props.forEach((v, k) => { if (ya === null && mismoObjeto(v, ocg)) ya = String(k) })
  if (ya !== null) return ya
  let n = sugerido, i = 0
  const tiene = (k) => { const v = props.get(k); return !nulo(v) }
  while (tiene(n)) { i++; n = `${sugerido}${i}` }
  props.put(n, ocg)
  return n
}
function agregarContenido(doc, pageObj, texto) {
  const st = doc.addStream(texto, doc.newDictionary())
  const cont = pageObj.get('Contents')
  if (nulo(cont)) pageObj.put('Contents', st)
  else if (cont.isArray()) cont.push(st)
  else { const a = doc.newArray(); a.push(cont); a.push(st); pageObj.put('Contents', a) }
}

/**
 * `agregar_pieza`: `colocaciones` = `{talle: [{segmentos, dx, dy}, …]}` en crudas; cada una va al
 * FINAL del contenido, dentro de la capa de su talle (así nadie se renumera). → `{bytes, puestos}`.
 */
export function agregarPieza(mupdf, bytes, colocaciones, mesa = 1) {
  if (!colocaciones || !Object.keys(colocaciones).length) throw new Error('no hay nada que agregar')
  const doc = new mupdf.PDFDocument(bytes)
  try {
    const pageObj = doc.findPage(mesa - 1)
    const puestos = []
    for (const [talle, cols] of Object.entries(colocaciones)) {
      const ocg = ocgPorNombre(doc, talle)
      if (!ocg) continue
      const pname = nombreEnRecursos(doc, pageObj, ocg, 'OCpz')
      let escrito = false
      for (const col of (Array.isArray(cols) ? cols : [cols])) {
        const ops = opsDeSegmentos(col.segmentos, Number(col.dx || 0), Number(col.dy || 0))
        if (!ops.trim()) continue
        agregarContenido(doc, pageObj, `q\n/OC /${pname} BDC\n0 0 0 RG 1 w\n${ops}\nS\nEMC\nQ\n`)
        escrito = true
      }
      if (escrito) puestos.push(talle)
    }
    if (!puestos.length) throw new Error('ninguno de los talles pedidos existe como capa en el molde')
    return { bytes: doc.saveToBuffer('compress').asUint8Array().slice(), puestos }
  } finally { doc.destroy() }
}

// ─── variantes_molde: separar la capa única en variantes ──────────────────────────────────────
const CONSTRUCCION = new Set(['m', 'l', 'c', 'v', 'y', 're', 'h'])
const PINTADO = new Set(['S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*', 'n'])
const num = (v) => (v && v.i !== undefined ? Number(v.i) : v && v.r !== undefined ? Number(v.r) : NaN)
const mul = (a, b) => [a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3], a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3],
  a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5]]

/** `_unidades_de_trazado`: `[[ini, fin, bbox, esClip]]` por trazado pintado del contenido. */
export function unidadesDeTrazado(inst) {
  let ctm = [1, 0, 0, 1, 0, 0]
  const pila = [], unidades = []
  let ini = null, pts = [], clip = false
  inst.forEach((it, i) => {
    const op = it.op
    if (op === 'q') pila.push(ctm)
    else if (op === 'Q') ctm = pila.length ? pila.pop() : ctm
    else if (op === 'cm') { const f = (it.args || []).map(num); if (f.length === 6 && f.every(Number.isFinite)) ctm = mul(f, ctm) }
    else if (CONSTRUCCION.has(op)) {
      if (ini === null) { ini = i; pts = []; clip = false }
      const f = (it.args || []).map(num)
      const ap = (x, y) => [ctm[0] * x + ctm[2] * y + ctm[4], ctm[1] * x + ctm[3] * y + ctm[5]]
      if (op === 're' && f.length === 4) {
        const [x, y, w, h] = f
        for (const [px, py] of [[x, y], [x + w, y], [x, y + h], [x + w, y + h]]) pts.push(ap(px, py))
      } else for (let k = 0; k + 1 < f.length; k += 2) pts.push(ap(f[k], f[k + 1]))
    } else if (op === 'W' || op === 'W*') clip = true
    else if (PINTADO.has(op)) {
      if (ini !== null && pts.length) {
        const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1])
        unidades.push([ini, i, [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)], clip])
      }
      ini = null; pts = []; clip = false
    }
  })
  return unidades
}

/** `piezas_para_asignar`: la mesa+capa con MÁS piezas → `{mesa, capa, piezas}`. */
export function piezasParaAsignar(molde) {
  let mejor = [0, null, null]
  for (let m = 1; m <= molde.n; m++) {
    const capas = new Set(molde.dibujos(m).map((d) => d.layer).filter(Boolean))
    for (const c of capas) {
      const n = extraerPiezasMesa(molde, m, c).length
      if (n > mejor[0]) mejor = [n, m, c]
    }
  }
  if (!mejor[1]) throw new Error('el molde no tiene piezas dibujadas en ninguna capa')
  return { mesa: mejor[1], capa: mejor[2], piezas: extraerPiezasMesa(molde, mejor[1], mejor[2]) }
}

/**
 * `separar_por_piezas`: parte la capa única en una capa REAL por variante. `asignaciones` =
 * `{pieza_idx: variante}` sobre `piezasParaAsignar`. → `{bytes, mesa, capa_origen, orden}`.
 */
export function separarPorPiezas(mupdf, bytes, molde, asignaciones) {
  const asig = new Map()
  for (const [k, v] of Object.entries(asignaciones || {})) if (String(v || '').trim()) asig.set(Math.trunc(Number(k)), String(v).trim())
  if (!asig.size) throw new Error('no hay ninguna pieza asignada a una variante')
  const { mesa, capa: capaOrigen, piezas } = piezasParaAsignar(molde)
  const fuera = [...asig.keys()].filter((i) => i < 0 || i >= piezas.length).sort((a, b) => a - b)
  if (fuera.length) throw new Error(`hay piezas que no existen en el molde: [${fuera.join(', ')}]`)
  for (const nom of new Set(asig.values())) {
    if (CAPAS_SISTEMA.has(nom) && nom !== '0') throw new Error(`«${nom}» es un nombre reservado del sistema: elegí otro`)
  }
  const area = new Map()
  for (const [i, nom] of asig) {
    const b = piezas[i].bbox_mu
    area.set(nom, (area.get(nom) || 0) + Math.abs(b[2] - b[0]) * Math.abs(b[3] - b[1]))
  }
  const orden = [...area.keys()].map((n, i) => [area.get(n), i, n]).sort((a, b) => a[0] - b[0] || a[1] - b[1]).map((x) => x[2])
  const doc = new mupdf.PDFDocument(bytes)
  try {
    const pageObj = doc.findPage(mesa - 1)
    const inst = [...instrucciones(contenidoCrudo(doc.loadPage(mesa - 1)))]
    const unidades = unidadesDeTrazado(inst).filter((u) => !u[3])
    const libres = unidades.map((_, i) => i)
    const dePieza = new Map()
    piezas.forEach((pz, k) => {
      const [x0, y0, x1, y1] = pz.bbox_raw
      const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2
      const tol = 0.15 * Math.min(Math.abs(x1 - x0), Math.abs(y1 - y0)) || 1.0
      let mejor = null
      for (const u of libres) {
        const b = unidades[u][2]
        const d = ((b[0] + b[2]) / 2 - cx) ** 2 + ((b[1] + b[3]) / 2 - cy) ** 2
        if (mejor === null || d < mejor[0]) mejor = [d, u]
      }
      if (mejor === null || Math.sqrt(mejor[0]) > tol) throw new Error(`no se pudo ubicar la pieza ${k + 1} dentro del molde: este molde no se puede separar por piezas`)
      dePieza.set(k, unidades[mejor[1]])
      libres.splice(libres.indexOf(mejor[1]), 1)
    })
    const root = doc.getTrailer().get('Root')
    let ocp = root.get('OCProperties')
    if (nulo(ocp)) {
      ocp = doc.newDictionary(); ocp.put('OCGs', doc.newArray())
      const dd = doc.newDictionary(); dd.put('Order', doc.newArray()); dd.put('ON', doc.newArray()); ocp.put('D', dd)
      root.put('OCProperties', ocp)
    }
    const res = recursosPropios(doc, pageObj)
    let props = res.get('Properties')
    if (nulo(props)) { props = doc.newDictionary(); res.put('Properties', props) }
    let ocgOrigen = null
    const usados = new Set()
    props.forEach((v, k) => {
      usados.add(String(k))
      try { if (v.get('Name').asString() === capaOrigen) ocgOrigen = String(k) } catch { /* sigue */ }
    })
    const resDe = new Map()
    orden.forEach((nom, j) => {
      const d = doc.newDictionary()
      d.put('Type', doc.newName('OCG')); d.put('Name', doc.newString(nom))
      const it = doc.newArray(); it.push(doc.newName('View')); it.push(doc.newName('Design')); d.put('Intent', it)
      const ocg = doc.addObject(d)
      ocp.get('OCGs').push(ocg)
      let dd = ocp.get('D')
      if (nulo(dd)) { dd = doc.newDictionary(); dd.put('Order', doc.newArray()); dd.put('ON', doc.newArray()); ocp.put('D', dd) }
      for (const k of ['Order', 'ON']) { if (nulo(dd.get(k))) dd.put(k, doc.newArray()); dd.get(k).push(ocg) }
      let k = `MCv${j}`
      while (usados.has(k)) k += 'x'
      usados.add(k)
      props.put(k, ocg)
      resDe.set(nom, k)
    })
    const abre = new Map(), cierra = new Set()
    for (const [k, u] of dePieza) {
      const nom = asig.get(k)
      const destinoRes = nom ? resDe.get(nom) : ocgOrigen
      if (!destinoRes) continue
      abre.set(u[0], destinoRes)
      cierra.add(u[1])
    }
    const nivel = [], quitar = new Set()
    inst.forEach((it, i) => {
      if (it.op === 'BDC' || it.op === 'BMC') {
        const esOc = !!(it.args && it.args.length && it.args[0] && it.args[0].n === 'OC')
        nivel.push(esOc)
        if (esOc) quitar.add(i)
      } else if (it.op === 'EMC') {
        if (nivel.length && nivel.pop()) quitar.add(i)
      }
    })
    const nuevo = []
    inst.forEach((it, i) => {
      if (quitar.has(i)) return
      if (abre.has(i)) nuevo.push({ op: 'BDC', args: [{ n: 'OC' }, { n: abre.get(i) }] })
      nuevo.push(it)
      if (cierra.has(i)) nuevo.push({ op: 'EMC', args: [] })
    })
    pageObj.put('Contents', doc.addStream(escribir(nuevo), doc.newDictionary()))
    return { bytes: doc.saveToBuffer('compress').asUint8Array().slice(), mesa, capa_origen: capaOrigen, orden }
  } finally { doc.destroy() }
}

// ─── motor_pedido.nido_piezas ─────────────────────────────────────────────────────────────────
function rotarSegs90(segs, cx, cy) {
  const R = (x, y) => [cx + (y - cy), cy - (x - cx)]
  const out = []
  for (const s of segs) {
    const op = s[0]
    if (op === 'm' || op === 'l') out.push([op, ...R(s[1], s[2])])
    else if (op === 'c') out.push(['c', ...R(s[1], s[2]), ...R(s[3], s[4]), ...R(s[5], s[6])])
    else if (op === 're') {
      const [x0, y0, w, h] = [s[1], s[2], s[3], s[4]]
      const rp = [[x0, y0], [x0 + w, y0], [x0 + w, y0 + h], [x0, y0 + h]].map(([px, py]) => R(px, py))
      out.push(['m', ...rp[0]]); for (const p of rp.slice(1)) out.push(['l', ...p]); out.push(['h'])
    } else out.push(s)
  }
  return out
}
export function bboxSegs(segs) {
  const xs = [], ys = []
  for (const s of segs) {
    const op = s[0]
    if (op === 'm' || op === 'l') { xs.push(s[1]); ys.push(s[2]) }
    else if (op === 'c') { xs.push(s[1], s[3], s[5]); ys.push(s[2], s[4], s[6]) }
    else if (op === 're') { xs.push(s[1], s[1] + s[3]); ys.push(s[2], s[2] + s[4]) }
  }
  if (!xs.length) return null
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]
}
const f1 = (v) => pyFixed(v, 1)
function segsASvg(segs, dx, dy, toPx) {
  const out = []
  for (const s of segs) {
    const op = s[0]
    if (op === 'm') { const [x, y] = toPx(s[1] + dx, s[2] + dy); out.push(`M ${f1(x)} ${f1(y)}`) }
    else if (op === 'l') { const [x, y] = toPx(s[1] + dx, s[2] + dy); out.push(`L ${f1(x)} ${f1(y)}`) }
    else if (op === 'c') {
      const a = toPx(s[1] + dx, s[2] + dy), b = toPx(s[3] + dx, s[4] + dy), c = toPx(s[5] + dx, s[6] + dy)
      out.push(`C ${f1(a[0])} ${f1(a[1])} ${f1(b[0])} ${f1(b[1])} ${f1(c[0])} ${f1(c[1])}`)
    } else if (op === 're') {
      const [x0, y0] = toPx(s[1] + dx, s[2] + dy), [x1, y1] = toPx(s[1] + s[3] + dx, s[2] + s[4] + dy)
      out.push(`M ${f1(x0)} ${f1(y0)} L ${f1(x1)} ${f1(y0)} L ${f1(x1)} ${f1(y1)} L ${f1(x0)} ${f1(y1)} Z`)
    } else if (op === 'h') out.push('Z')
  }
  return out.join(' ')
}
const pyRoundHalfEven = (v, n = 0) => { const k = 10 ** n; const x = v * k; const r = Math.round(x); return (Math.abs(x % 1) === 0.5 ? (r % 2 === 0 ? r : r - 1) : r) / k }

/** `nido_piezas`: cada pieza nombrada con TODAS sus tallas apiladas, en un marco común de px. */
export function nidoPiezas(molde, registro, { talleGuia = null, anchoPreview = 1100, indices = null, emparejado = null } = {}) {
  const base = detectarPiezas(molde, talleGuia)
  const mesa = base.mesa, guia = base.talle_ref, talles = base.talles && base.talles.length ? base.talles : [guia]
  const contsPorTalle = new Map()
  for (const t of talles) { const cs = extraerPiezasMesa(molde, mesa, t); if (cs.length) contsPorTalle.set(t, cs) }
  if (!contsPorTalle.has(guia)) throw new Error('el talle guía no tiene piezas')
  const nombresGuia = new Map()
  for (const [nom, porT] of Object.entries(registro || {})) {
    const info = (porT || {})[guia]
    if (info && info.mesa === mesa && info.pieza_idx !== null && info.pieza_idx !== undefined) nombresGuia.set(nom, info.pieza_idx)
  }
  if (!nombresGuia.size) throw new Error('no hay piezas nombradas para nestear')
  const fGuia = featsConts(contsPorTalle.get(guia), empOffsets(emparejado, guia))
  const mapaExacto = mapaIndices(indices, guia)
  const porNombre = new Map()
  for (const [t, conts] of contsPorTalle) {
    let eleccion
    if (t === guia) {
      eleccion = new Map([...nombresGuia].filter(([, i]) => i < conts.length).map(([n, i]) => [n, [i, false]]))
    } else if (mapaExacto && mapaExacto.has(t)) {
      const mt = mapaExacto.get(t)
      const fT = featsConts(conts, empOffsets(emparejado, t))
      eleccion = new Map()
      for (const [nom, gi] of nombresGuia) {
        const j = mt.get(gi)
        if (j === undefined || j === null || j >= conts.length) continue
        let rot = false
        if (gi < fGuia.length && j < fT.length) {
          const fr = fGuia[gi], fc = fT[j]
          rot = (Math.abs(-fc.lar - fr.lar) + 0.25) < Math.abs(fc.lar - fr.lar)
        }
        eleccion.set(nom, [j, rot])
      }
    } else {
      eleccion = emparejarPorForma(fGuia, nombresGuia, featsConts(conts, empOffsets(emparejado, t)))
    }
    if (t !== guia) eleccion = aplicarFijos(eleccion, empFijos(emparejado, t), conts.length)
    for (const [nom, [j, rot]] of eleccion) {
      const c = conts[j]
      const [x0, y0, x1, y1] = c.bbox_raw
      const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2
      const segs = rot ? rotarSegs90(c.segmentos, cx, cy) : c.segmentos
      const bb = bboxSegs(segs)
      if (!bb) continue
      if (!porNombre.has(nom)) porNombre.set(nom, new Map())
      porNombre.get(nom).set(t, { segs, cx: (bb[0] + bb[2]) / 2, base: bb[1], h: Math.max(bb[3] - bb[1], 1e-6), hw: Math.max((bb[2] - bb[0]) / 2.0, 1e-6) })
    }
  }
  if (!porNombre.size) throw new Error('no hay piezas nombradas para nestear')
  const half = new Map()
  for (const [nom, td] of porNombre) {
    const ds = [...td.values()]
    const hw = ds.length ? Math.max(...ds.map((d) => d.hw)) : 1.0
    const hmax = ds.length ? Math.max(...ds.map((d) => d.h)) : 2.0
    half.set(nom, [hw, hmax / 2.0])
    for (const d of ds) d.cy = d.base + hmax / 2.0
  }
  const nombresOrd = [...porNombre.keys()]
  const n = nombresOrd.length
  const cols = Math.max(1, Math.trunc(pyRoundHalfEven(Math.sqrt(n))))
  const gap = 0.18 * (half.size ? Math.max(...[...half.values()].map((h) => h[0])) : 100.0)
  const basePos = new Map()
  let rowTop = 0.0, i = 0
  while (i < n) {
    const fila = nombresOrd.slice(i, i + cols)
    const rowHh = Math.max(...fila.map((nm) => half.get(nm)[1]))
    let cx = 0.0
    for (const nm of fila) { const [hw] = half.get(nm); basePos.set(nm, [cx + hw, rowTop - rowHh]); cx += 2 * hw + gap }
    rowTop -= 2 * rowHh + gap
    i += cols
  }
  let minX = 1e18, minY = 1e18, maxX = -1e18, maxY = -1e18
  for (const [nom, td] of porNombre) {
    const [bx, by] = basePos.get(nom)
    for (const d of td.values()) {
      const bb = bboxSegs(d.segs)
      if (!bb) continue
      const ddx = bx - d.cx, ddy = by - d.cy
      minX = Math.min(minX, bb[0] + ddx); maxX = Math.max(maxX, bb[2] + ddx)
      minY = Math.min(minY, bb[1] + ddy); maxY = Math.max(maxY, bb[3] + ddy)
    }
  }
  const marg = Math.max(20.0, (maxX - minX) * 0.03)
  minX -= marg; maxX += marg; minY -= marg; maxY += marg
  const scale = anchoPreview / Math.max(1.0, maxX - minX)
  const W = anchoPreview, H = (maxY - minY) * scale
  const toPx = (rx, ry) => [(rx - minX) * scale, (maxY - ry) * scale]
  const piezasOut = []
  for (const [nom, td] of porNombre) {
    const [bx, by] = basePos.get(nom)
    const tallas = []
    for (const t of talles) {
      const d = td.get(t)
      if (!d) continue
      tallas.push({ talle: t, d: segsASvg(d.segs, bx - d.cx, by - d.cy, toPx) })
    }
    const [cxpx, cypx] = toPx(bx, by)
    const [hw, hh] = half.get(nom) || [1.0, 1.0]
    piezasOut.push({ nombre: nom, cx: pyRoundHalfEven(cxpx, 1), cy: pyRoundHalfEven(cypx, 1),
                     idx: nombresGuia.has(nom) ? nombresGuia.get(nom) : null,
                     hw: pyRoundHalfEven(hw * scale, 1), hh: pyRoundHalfEven(hh * scale, 1), talles: tallas })
  }
  return { vb: `0 0 ${Math.round(W).toFixed(0)} ${Math.round(H).toFixed(0)}`, w: Math.round(W), h: Math.round(H),
           guia, talles, piezas: piezasOut }
}

// ─── la guía de medidas (PDF y .ai) ───────────────────────────────────────────────────────────
function nombreMesaGuia(pieza, talleP, config, rango) {
  const gen = String(pieza).replace(/\s+\d+\s*$/, '').trim() || String(pieza)
  if (config === 'talle') return `#${talleP} ${gen}`
  if (config === 'rango' && rango && rango.length) return `#${rango[0]}-${rango[rango.length - 1]} ${gen}`
  return gen
}

/**
 * `pdf_guia_medidas`, sobre la geometría que arma el servidor (`capas_data` de `_guia_capas_data`):
 * una página por talle a tamaño real, el contorno en vector, el recuadro del diseño y el nombre de
 * mesa. → bytes del PDF.
 */
export function pdfGuiaMedidas(mupdf, capasData, { config = 'default', rango = [], titulo = 'Molde', limpio = false } = {}) {
  if (!capasData || !capasData.length) throw new Error('no se detectaron piezas en la plantilla')
  const MARG = 40, TOP = 90, LBLF = 16, TITF = 22
  const verde = '0.3 0.55 0.34', cyan = '0 0.55 0.7', tinta = '0.1 0.1 0.1'
  const esMulti = config === 'talle'
  const subBase = config === 'rango' ? ('rango ' + (rango && rango.length ? `${rango[0]}-${rango[rango.length - 1]}` : '—')) : 'todos los talles'
  const doc = new mupdf.PDFDocument()
  const fuente = new mupdf.Font('Helvetica-Bold')
  try {
    const fRef = doc.addSimpleFont(fuente, 'Latin')
    // el texto va en hexadecimal con el código Latin-1 de cada letra (la fuente es WinAnsi); lo
    // que no entra en un byte sale como «·», como en la ficha
    const hexTxt = (t) => '<' + [...String(t)].map((ch) => { const c = ch.codePointAt(0); return (c < 256 ? c : 0xB7).toString(16).padStart(2, '0') }).join('') + '>'
    const largo = (t, size) => { let w = 0; for (const ch of String(t)) w += fuente.advanceGlyph(fuente.encodeCharacter(ch.codePointAt(0)), 0); return w * size }
    const g = (v) => pyFixed(v, 3)
    for (const cd of capasData) {
      const PW = MARG * 2 + (cd.maxX - cd.minX), PH = TOP + MARG + (cd.maxY - cd.minY)
      // lienzo (y arriba) → página PDF (y arriba). En el Python la página es y-abajo con el molde
      // desde TOP+MARG hasta el borde de abajo: en y-arriba eso es `cy - minY` (sin margen abajo)
      const T = (cx, cy) => [MARG + (cx - cd.minX), cy - cd.minY]
      let s = `1 1 1 rg 0 0 ${g(PW)} ${g(PH)} re f\n`
      const sub = esMulti ? `talle ${cd.talle}` : subBase
      const tit = `${titulo} - ${limpio ? 'Base (contornos)' : 'Guía de armado'} · ${sub} · (tamaño real 1:1)`
      s += `BT /F0 ${TITF} Tf ${tinta} rg ${g(MARG)} ${g(PH - 36)} Td ${hexTxt(tit)} Tj ET\n`
      for (const it of cd.items) {
        s += `q ${verde} RG 2 w\n`
        for (const sg of it.segs) {
          const op = sg[0]
          if (op === 'm') { const [x, y] = T(sg[1], sg[2]); s += `${g(x)} ${g(y)} m\n` }
          else if (op === 'l') { const [x, y] = T(sg[1], sg[2]); s += `${g(x)} ${g(y)} l\n` }
          else if (op === 'c') { const a = T(sg[1], sg[2]), b = T(sg[3], sg[4]), c = T(sg[5], sg[6]); s += `${g(a[0])} ${g(a[1])} ${g(b[0])} ${g(b[1])} ${g(c[0])} ${g(c[1])} c\n` }
          else if (op === 're') { const [x, y] = T(sg[1], sg[2]); s += `${g(x)} ${g(y)} ${g(sg[3])} ${g(sg[4])} re\n` }
          else if (op === 'h') s += 'h\n'
        }
        s += 'S Q\n'
        if (limpio) continue
        const [rx0, ry0] = T(it.ccx - it.wC / 2, it.ccy - it.hC / 2)
        s += `q ${cyan} RG 2 w [14 8] 0 d ${g(rx0)} ${g(ry0)} ${g(it.wC)} ${g(it.hC)} re S Q\n`
        const nm = it.nombre ? nombreMesaGuia(it.nombre, cd.talle, config, rango) : ''
        if (nm) {
          const [cx, cy] = T(it.ccx, it.ccy)
          const w = largo(nm, LBLF)
          if (w > it.wC - 8 && it.hC > w + 14) {
            // pieza angosta y alta → texto vertical (girado 90°)
            s += `BT /F0 ${LBLF} Tf ${tinta} rg 0 1 -1 0 ${g(cx - 5)} ${g(cy - w / 2)} Tm ${hexTxt(nm)} Tj ET\n`
          } else {
            s += `BT /F0 ${LBLF} Tf ${tinta} rg ${g(cx - w / 2)} ${g(cy - 5)} Td ${hexTxt(nm)} Tj ET\n`
          }
        }
      }
      const res = doc.newDictionary(), fd = doc.newDictionary()
      fd.put('F0', fRef); res.put('Font', fd)
      doc.insertPage(doc.countPages(), doc.addPage([0, 0, PW, PH], 0, res, new TextEncoder().encode(s)))
    }
    return doc.saveToBuffer('compress').asUint8Array().slice()
  } finally {
    try { fuente.destroy() } catch { /* nada */ }
    doc.destroy()
  }
}

const aiEsc = (s) => String(s).replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)')
const f3 = (v) => pyFixed(v, 3)
function aiPath(segs, T) {
  const out = []
  let start = null
  for (const s of segs) {
    const op = s[0]
    if (op === 'm') { const [x, y] = T(s[1], s[2]); out.push(`${f3(x)} ${f3(y)} m`); start = [x, y] }
    else if (op === 'l') { const [x, y] = T(s[1], s[2]); out.push(`${f3(x)} ${f3(y)} L`) }
    else if (op === 'c') { const a = T(s[1], s[2]), b = T(s[3], s[4]), c = T(s[5], s[6]); out.push(`${f3(a[0])} ${f3(a[1])} ${f3(b[0])} ${f3(b[1])} ${f3(c[0])} ${f3(c[1])} c`) }
    else if (op === 're') {
      const [x, y, w, h] = [s[1], s[2], s[3], s[4]]
      const a = T(x, y), b = T(x + w, y), c2 = T(x + w, y + h), d = T(x, y + h)
      out.push(`${f3(a[0])} ${f3(a[1])} m`, `${f3(b[0])} ${f3(b[1])} L`, `${f3(c2[0])} ${f3(c2[1])} L`, `${f3(d[0])} ${f3(d[1])} L`, `${f3(a[0])} ${f3(a[1])} L`)
      start = a
    } else if (op === 'h') { if (start) out.push(`${f3(start[0])} ${f3(start[1])} L`) }
  }
  return out.join('\n')
}
const gPy = (v) => { const s = String(Number(v)); return s.includes('.') ? s.replace(/0+$/, '').replace(/\.$/, '') : s }
function aiText(text, x, y, size) {
  return `0 To\n1 0 0 1 ${f3(x)} ${f3(y)} 0 Tp\nTP\n0 Tr\n0 O\n0 0 0 1 k\n0 0 0 1 K\n/_Helvetica ${gPy(size)} Tf\n0 Ts\n100 Tz\n0 Tw\n0 Tc\n(${aiEsc(text)}) Tx\n(\\r) TX\nTO`
}
function aiLayer(nombre, r, g, b, cuerpo) {
  return `%AI5_BeginLayer\n1 1 1 1 0 0 0 ${r} ${g} ${b} Lb\n(${aiEsc(nombre)}) Ln\n0 A\n${cuerpo}\nLB\n%AI5_EndLayer\n`
}
export const EDITABLES_GUIA = ['Editable escudo', 'Editable logo']
export const normNom = (n) => String(n || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim()

/**
 * `ai_guia_medidas`: la guía como .ai nativo (capas REALES en Illustrator), sobre `capas_data`.
 * `capas` = capas del arte a crear vacías; `editables` = capas «Editable …». → bytes (latin-1).
 */
export function aiGuiaMedidas(capasData, { config = 'default', rango = [], titulo = 'Molde', capas = null, editables = null } = {}) {
  if (!capasData || !capasData.length) throw new Error('no se detectaron piezas en la plantilla')
  const its = capasData[0].items
  const MARG = 40.0, TOP = 60.0, GAP = 34.0
  const bboxIt = (it) => {
    const b = bboxSegs(it.segs) || [0, 0, 0, 0]
    const rx0 = it.ccx - it.wC / 2, ry0 = it.ccy - it.hC / 2, rx1 = it.ccx + it.wC / 2, ry1 = it.ccy + it.hC / 2
    return [Math.min(b[0], rx0), Math.min(b[1], ry0), Math.max(b[2], rx1), Math.max(b[3], ry1)]
  }
  const bxs = its.map(bboxIt)
  const ws = bxs.map((b) => b[2] - b[0]), hs = bxs.map((b) => b[3] - b[1])
  const rowLimit = Math.max(Math.max(...ws), (ws.reduce((a, b) => a + b, 0) / ws.length) * Math.ceil(Math.sqrt(its.length)))
  const placed = []
  let x = MARG, y = MARG, rowH = 0.0, rightEdge = MARG, topEdge = MARG
  bxs.forEach((b, i) => {
    const w = ws[i], h = hs[i]
    if (x > MARG && x + w > MARG + rowLimit) { x = MARG; y = y + rowH + GAP; rowH = 0.0 }
    placed.push([x - b[0], y - b[1]])
    rightEdge = Math.max(rightEdge, x + w); topEdge = Math.max(topEdge, y + h)
    x = x + w + GAP; rowH = Math.max(rowH, h)
  })
  const PW = rightEdge + MARG, PH = topEdge + MARG + TOP
  if (Math.max(PW, PH) > 16000) throw new Error('el molde a tamaño real es más grande que el máximo de Illustrator (227"). Elegí una VARIABLE para bajar la guía solo de sus piezas.')
  const Ti = (i, cx, cy) => [cx + placed[i][0], cy + placed[i][1]]
  const mo = ['0 0 0 1 K', '1.5 w']
  its.forEach((it, i) => { mo.push(aiPath(it.segs, (cx, cy) => Ti(i, cx, cy))); mo.push('S') })
  its.forEach((it, i) => {
    const rx0 = it.ccx - it.wC / 2, ry0 = it.ccy - it.hC / 2
    const a = Ti(i, rx0, ry0), b = Ti(i, rx0 + it.wC, ry0), c2 = Ti(i, rx0 + it.wC, ry0 + it.hC), d = Ti(i, rx0, ry0 + it.hC)
    mo.push('0.75 0 0 0 K\n1 w\n[8 6] 0 d')
    mo.push(`${f3(a[0])} ${f3(a[1])} m\n${f3(b[0])} ${f3(b[1])} L\n${f3(c2[0])} ${f3(c2[1])} L\n${f3(d[0])} ${f3(d[1])} L\n${f3(a[0])} ${f3(a[1])} L\nS`)
    mo.push('[] 0 d')
  })
  mo.push(aiText(`${titulo} - Guia (arma el arte encima) - 1:1`, MARG, PH - 34, 14))
  const nombreMesa = (p) => {
    const gen = String(p).replace(/\s+\d+\s*$/, '').trim() || String(p)
    return config === 'rango' && rango && rango.length ? `#${rango[0]}-${rango[rango.length - 1]} ${gen}` : gen
  }
  its.forEach((it, i) => {
    const nm = it.nombre ? nombreMesa(it.nombre) : ''
    if (!nm) return
    const [cx, cy] = Ti(i, it.ccx, it.ccy)
    mo.push(aiText(nm, cx - nm.length * 3.2, cy, 12))
  })
  const marca = `1 1 1 0 K\n0.01 w\n${pyFixed(MARG, 2)} ${pyFixed(MARG, 2)} m\n${pyFixed(MARG + 0.1, 2)} ${pyFixed(MARG, 2)} L\nS`
  const RESERVADAS = new Set(['molde', 'guia', 'guias'])
  const pers = []
  let diseno = null
  for (let nc of (capas || [])) {
    nc = String(nc).trim()
    if (!nc || RESERVADAS.has(nc.toLowerCase())) continue
    if (normNom(nc) === 'diseno') diseno = nc
    else if (normNom(nc).includes('editable')) continue          // «editable» en cualquier parte (`esCapaEditable`)
    else pers.push(nc)
  }
  const eds = (editables !== null && editables !== undefined ? editables : EDITABLES_GUIA).map((e) => String(e).trim()).filter(Boolean)
  let cuerpo = aiLayer(diseno || 'diseño', 128, 128, 128, marca)
  for (const ed of eds) cuerpo += aiLayer(ed, 255, 170, 60, marca)
  for (const nc of pers) cuerpo += aiLayer(nc, 190, 120, 255, marca)
  cuerpo += aiLayer('guias', 52, 211, 153, mo.join('\n'))
  const ai = '%!PS-Adobe-3.0 EPSF-3.0\n' +
    `%%Creator: TizadaPro\n%%Title: (${aiEsc(titulo)})\n` +
    `%%BoundingBox: 0 0 ${Math.trunc(PW + 1)} ${Math.trunc(PH + 1)}\n%%HiResBoundingBox: 0 0 ${f3(PW)} ${f3(PH)}\n` +
    '%%DocumentProcessColors: Cyan Magenta Yellow Black\n%%DocumentFonts: Helvetica\n' +
    `%AI5_FileFormat 3\n%AI3_ColorUsage: Color\n%AI5_ArtSize: ${f3(PW)} ${f3(PH)}\n` +
    '%%EndComments\n%%BeginProlog\n%%EndProlog\n%%BeginSetup\n%%EndSetup\n' +
    cuerpo + '%%PageTrailer\ngsave annotatepage grestore showpage\n%%Trailer\n%%EOF\n'
  const out = new Uint8Array(ai.length)
  for (let i = 0; i < ai.length; i++) { const c = ai.charCodeAt(i); out[i] = c < 256 ? c : 63 }   // latin-1, «?» si no entra
  return out
}
