// LAS PIEZAS DE UN MOLDE QUE YA TRAE EL DISEÑO ADENTRO (camino B), EN EL NAVEGADOR.
//
// Traducción función por función de `piezas_con_diseno.py` (y de lo que usa de `molde_real.py` y
// `motor_pedido.py`) — PLAN_NAVEGADOR.md, etapa 1. Los comentarios que explican el PORQUÉ de cada
// regla están en el Python; acá se repiten sólo los que cambian cómo se escribe en JavaScript.
// El contrato `verificar_navegador_molde.py` compara la salida con la del servidor, número a número.
//
// Un contorno es exactamente el dict de `molde_real._contorno_de_drawing`:
//   { segmentos: [['m', x, y], ['l', x, y], ['c', x1, y1, x2, y2, x3, y3], ['re', x, y, w, h], ['h']],
//     bbox_raw: [x0, y0, x1, y1], user_unit, bbox_mu: [x0, y0, x1, y1], w, h, mesa, talle }

import { pyRound, pyFixed, pyMax, compararTuplas } from '../py.js'

export const CM = 28.3465
const TOL_MARCO = 1.0

// ─── geometría de la página, como la ve PyMuPDF ──────────────────────────────────────────────
const f32 = Math.fround

function aRectPdf(obj) {
  // pdf_to_rect: los 4 números como float, normalizados (min/max)
  if (!obj || obj.isNull() || !obj.isArray() || obj.length < 4) return null
  const v = [0, 1, 2, 3].map((i) => f32(obj.get(i).asNumber()))
  return [Math.min(v[0], v[2]), Math.min(v[1], v[3]), Math.max(v[0], v[2]), Math.max(v[1], v[3])]
}
const vacio = (r) => r[0] >= r[2] || r[1] >= r[3]

/** `page.cropbox` de PyMuPDF (`JM_cropbox`): el CropBox con la y invertida respecto del MediaBox. */
export function cropboxPyMuPDF(page) {
  const obj = page.getObject()
  let mb = aRectPdf(obj.getInheritable('MediaBox'))
  if (!mb || vacio(mb)) mb = [0, 0, 612, 792]
  mb = [Math.min(mb[0], mb[2]), Math.min(mb[1], mb[3]), Math.max(mb[0], mb[2]), Math.max(mb[1], mb[3])]
  if (mb[2] - mb[0] < 1 || mb[3] - mb[1] < 1) mb = [0, 0, 1, 1]
  let cb = aRectPdf(obj.getInheritable('CropBox'))
  if (!cb || vacio(cb)) cb = mb.slice()
  return [cb[0], mb[3] - cb[3], cb[2], mb[3] - cb[1]]
}

const ancho = (r) => Math.max(0, r[2] - r[0])
const alto = (r) => Math.max(0, r[3] - r[1])

/** `{rect, cb, U, marco}` de una página: lo que `_piezas_de_mesa_cruda` y `desplegar_mesa` usan. */
export function geometriaPagina(page) {
  const b = page.getBounds()
  const rect = [b[0], b[1], b[2], b[3]]
  const cb = cropboxPyMuPDF(page)
  const U = ancho(cb) ? ancho(rect) / ancho(cb) : 1.0
  return { rect, cb, U, marco: [cb[0], cb[1], cb[2], cb[3]] }
}

// ─── los talles = las capas ──────────────────────────────────────────────────────────────────
/** `talles_del_molde`: los nombres de `layer_ui_configs()` (el /Order) y después los de `get_ocgs()`. */
export function tallesDelMolde(doc) {
  const orden = []
  const agregar = (n) => { if (n && !orden.includes(n)) orden.push(n) }
  let props = null
  try { props = doc.getTrailer().get('Root').get('OCProperties') } catch { props = null }
  if (!props || props.isNull()) return orden
  const ocgs = props.get('OCGs')
  const lista = []
  if (ocgs && ocgs.isArray()) for (let i = 0; i < ocgs.length; i++) lista.push(ocgs.get(i))
  const esOcg = (o) => lista.some((x) => x.isIndirect() && o.isIndirect() && x.asIndirect() === o.asIndirect())
  // pdf-layer.c `populate_ui`: arreglos anidados se recorren, un texto es un rótulo, un OCG que no
  // está en la lista principal se ignora
  const vistos = new Set()
  const recorrer = (arr) => {
    for (let i = 0; i < arr.length; i++) {
      const o = arr.get(i)
      if (o.isArray()) {
        const clave = o.isIndirect() ? o.asIndirect() : null
        if (clave !== null) { if (vistos.has(clave)) continue; vistos.add(clave) }
        recorrer(o)
        continue
      }
      if (o.isString()) { agregar(o.asString()); continue }
      if (!esOcg(o)) continue
      agregar(o.get('Name').asString())
    }
  }
  try {
    const order = props.get('D').get('Order')
    if (order && order.isArray()) recorrer(order)
  } catch { /* sin /Order */ }
  for (const o of lista) {
    try { agregar(o.get('Name').asString()) } catch { /* sin nombre */ }
  }
  return orden
}

// ─── descartes y agrupamiento ────────────────────────────────────────────────────────────────
function esMarcoDeMesa(r, rectPagina) {
  const p = rectPagina
  return Math.abs(r[0] - p[0]) < TOL_MARCO && Math.abs(r[1] - p[1]) < TOL_MARCO &&
    Math.abs(r[2] - p[2]) < TOL_MARCO && Math.abs(r[3] - p[3]) < TOL_MARCO
}

function sePisan(a, b) {
  const an = Math.min(a[2], b[2]) - Math.max(a[0], b[0])
  const al = Math.min(a[3], b[3]) - Math.max(a[1], b[1])
  if (an <= 0 || al <= 0) return false
  const comun = an * al
  const menor = Math.min(ancho(a) * alto(a), ancho(b) * alto(b))
  return menor <= 0 || comun / menor > 0.5
}

function agruparPorSolape(rects) {
  const padre = rects.map((_, i) => i)
  const raiz = (i) => {
    while (padre[i] !== i) { padre[i] = padre[padre[i]]; i = padre[i] }
    return i
  }
  for (let i = 0; i < rects.length; i++) {
    for (let j = i + 1; j < rects.length; j++) {
      if (sePisan(rects[i], rects[j])) {
        const ri = raiz(i), rj = raiz(j)
        if (ri !== rj) padre[rj] = ri
      }
    }
  }
  const grupos = new Map()
  for (let i = 0; i < rects.length; i++) {
    const r = raiz(i)
    if (!grupos.has(r)) grupos.set(r, [])
    grupos.get(r).push(i)
  }
  return [...grupos.values()]
}

const rectDe = (d) => d.scissor || d.rect || null

function envuelve(a, b, tol = 1.0) {
  return a[0] <= b[0] + tol && a[1] <= b[1] + tol && a[2] >= b[2] - tol && a[3] >= b[3] - tol
}

function pintadoPorClip(dibujos, talle) {
  // Map(índice en `dibujos` → [rellenos, trazos]); ver el Python
  const seq = []
  dibujos.forEach((d, k) => { if (d.layer === talle) seq.push(k) })
  const out = new Map()
  for (let k = 0; k < seq.length; k++) {
    const d = dibujos[seq[k]]
    if (d.type !== 'clip') continue
    const L = d.level || 0
    let f = 0, s = 0
    for (let m = k + 1; m < seq.length; m++) {
      const y = dibujos[seq[m]]
      if ((y.level || 0) <= L) break
      if (y.type === 'f' || y.type === 'fs') f++
      else if (y.type === 's') s++
    }
    out.set(seq[k], [f, s])
  }
  return out
}

// ─── el contorno ─────────────────────────────────────────────────────────────────────────────
/** `molde_real._contorno_de_drawing` con los items crudos de `get_cdrawings`. */
export function contornoDeDrawing(items, r, cb, U, mesa, talle) {
  const pt = (p) => [p[0] / U + cb[0], cb[3] - p[1] / U]
  const mismo = (a, b) => a !== null && Math.abs(a[0] - b[0]) < 0.05 && Math.abs(a[1] - b[1]) < 0.05
  const seg = []
  let actual = null
  for (const it of items) {
    const t = it[0]
    if (t === 'l') {
      const p1 = it[1], p2 = it[2]
      if (!mismo(actual, p1)) seg.push(['m', ...pt(p1)])
      seg.push(['l', ...pt(p2)])
      actual = p2
    } else if (t === 'c') {
      const p1 = it[1], c1 = it[2], c2 = it[3], p2 = it[4]
      if (!mismo(actual, p1)) seg.push(['m', ...pt(p1)])
      seg.push(['c', ...pt(c1), ...pt(c2), ...pt(p2)])
      actual = p2
    } else if (t === 're') {
      const rr = it[1]
      const [x0r, y0r] = pt([rr[0], rr[3]])
      seg.push(['re', x0r, y0r, ancho(rr) / U, alto(rr) / U])
      actual = null
    } else if (t === 'qu') {
      const q = it[1]                       // [ul, ur, ll, lr]
      const ps = [q[0], q[1], q[3], q[2]]   // ul, ur, lr, ll
      if (!mismo(actual, ps[0])) seg.push(['m', ...pt(ps[0])])
      for (const p of ps.slice(1)) seg.push(['l', ...pt(p)])
      seg.push(['l', ...pt(ps[0])])
      actual = ps[0]
    }
  }
  seg.push(['h'])
  const bboxRaw = [r[0] / U + cb[0], cb[3] - r[3] / U, r[2] / U + cb[0], cb[3] - r[1] / U]
  return { segmentos: seg, bbox_raw: bboxRaw, user_unit: U, bbox_mu: [r[0], r[1], r[2], r[3]],
    w: ancho(r), h: alto(r), mesa, talle }
}

// ─── ¿es un molde con el diseño adentro? ─────────────────────────────────────────────────────
/**
 * `parece_molde_con_diseno`, por mesa: cuántos recortes (que no sean el marco de la mesa) y
 * cuántos rellenos trae. El que llama suma las mesas (el servidor mira las dos primeras) y decide:
 * sin recortes → molde pelado (camino A); recortes sin nada pintado → tampoco; si no, camino B.
 * Sirve con la lectura LIGERA: los rellenos ligeros también entran como `f`.
 */
export function conteoConDiseno(dibujos, geo) {
  let clips = 0, pintados = 0
  for (const d of dibujos) {
    if (d.type === 'clip') {
      const r = rectDe(d)
      if (r && ancho(r) > 0 && alto(r) > 0 && !esMarcoDeMesa(r, geo.rect)) clips++
    } else if (d.type === 'f' || d.type === 'fs') {
      pintados++
    }
  }
  return { clips, pintados }
}

/** La decisión con los conteos sumados: `{si, motivo}` con los mismos textos que el servidor. */
export function decidirConDiseno({ clips, pintados }) {
  if (clips === 0) return { si: false, motivo: 'el archivo no trae máscaras de recorte: parece un molde sin diseño' }
  if (pintados === 0) return { si: false, motivo: 'el archivo trae recortes pero nada pintado adentro' }
  return { si: true, motivo: `${clips} máscaras de recorte con dibujo adentro` }
}

// ─── las piezas de una mesa en un talle ──────────────────────────────────────────────────────
export function piezasDeMesaCruda(dibujos, geo, mesa, talle, areaMin = 0.25, ladoMin = 0.3, completos = null) {
  const { rect, cb, U } = geo
  const cands = [], rects = []
  dibujos.forEach((d, k) => {
    if (d.type !== 'clip' || d.layer !== talle) return
    const r = rectDe(d)
    if (!r || ancho(r) <= 0 || alto(r) <= 0) return
    if (esMarcoDeMesa(r, rect)) return
    if (!(d.items && d.items.length)) return
    cands.push(k)
    rects.push(r)
  })
  // sin recortes: el respaldo necesita la caja de cada relleno, que la lectura ligera no calcula
  if (!cands.length) return respaldoPorTrazados(completos ? completos() : dibujos, geo, mesa, talle, areaMin, ladoMin)

  const pintado = pintadoPorClip(dibujos, talle)
  const trazos = dibujos.filter((x) => x.type === 's' && x.layer === talle).map(rectDe)
    .filter((t) => t && ancho(t) > 0 && alto(t) > 0)
  const piezas = []
  for (const grupo of agruparPorSolape(rects)) {
    const pint = (k) => pintado.get(cands[k]) || [0, 0]
    const conDiseno = grupo.filter((k) => pint(k)[0] > 0)
    let i = pyMax(conDiseno.length ? conDiseno : grupo, (k) => ancho(rects[k]) * alto(rects[k]))
    let r = rects[i]
    let linea = null
    if (conDiseno.length) {
      const esLinea = (k) => {
        const [f, s] = pint(k)
        if (f > 0 || !envuelve(rects[k], r)) return false
        return s > 0 || trazos.some((tr) => envuelve(rects[k], tr, 1.0) && envuelve(tr, rects[k], 1.0))
      }
      const envol = grupo.filter((k) => k !== i && esLinea(k))
      if (envol.length) linea = pyMax(envol, (k) => ancho(rects[k]) * alto(rects[k]))
    }
    if (linea !== null) { i = linea; r = rects[linea] }
    const wCm = ancho(r) / U / CM, hCm = alto(r) / U / CM
    if (wCm * hCm < areaMin || Math.min(wCm, hCm) < ladoMin) continue
    const cont = contornoDeDrawing(dibujos[cands[i]].items, r, cb, U, mesa, talle)
    if (linea !== null) cont.linea_corte = true
    piezas.push([Math.min(...grupo), cont])
  }
  piezas.sort((a, b) => a[0] - b[0])     // estable, como `sort(key=…)` de Python
  return piezas.map((p) => p[1])
}

function respaldoPorTrazados(dibujos, geo, mesa, talle, areaMin, ladoMin) {
  const { cb, U } = geo
  const idx = [], rects = []
  dibujos.forEach((d, k) => {
    if (!['f', 's', 'fs'].includes(d.type) || d.layer !== talle) return
    const r = rectDe(d)
    if (!r || ancho(r) <= 0 || alto(r) <= 0) return
    idx.push(k)
    rects.push(r)
  })
  if (!rects.length) return []
  const piezas = []
  for (const grupo of agruparPorSolape(rects)) {
    const i = pyMax(grupo, (k) => ancho(rects[k]) * alto(rects[k]))
    const r = rects[i]
    const wCm = ancho(r) / U / CM, hCm = alto(r) / U / CM
    if (wCm * hCm < areaMin || Math.min(wCm, hCm) < ladoMin) continue
    piezas.push([Math.min(...grupo), contornoDeDrawing(dibujos[idx[i]].items || [], r, cb, U, mesa, talle)])
  }
  piezas.sort((a, b) => a[0] - b[0])
  return piezas.map((p) => p[1])
}

// ─── el orden de las piezas: el del talle de referencia ─────────────────────────────────────
/** `motor_pedido._emparejar_por_solape`: Map(nombre → [j, false]). */
export function emparejarPorSolape(piezasRef, nombresRef, piezas) {
  const bb = (p) => (p.bbox_mu && p.bbox_mu.length === 4 ? p.bbox_mu : null)
  const pares = []
  for (const [nom, i] of nombresRef) {
    if (i === null || i === undefined || i >= piezasRef.length) continue
    const a = bb(piezasRef[i])
    if (!a) continue
    piezas.forEach((pz, j) => {
      const b = bb(pz)
      if (!b) return
      const ix = Math.max(0.0, Math.min(a[2], b[2]) - Math.max(a[0], b[0]))
      const iy = Math.max(0.0, Math.min(a[3], b[3]) - Math.max(a[1], b[1]))
      const inter = ix * iy
      if (inter <= 0) return
      const union = ((a[2] - a[0]) * (a[3] - a[1])) + ((b[2] - b[0]) * (b[3] - b[1])) - inter
      if (union > 0) pares.push([inter / union, nom, j])
    })
  }
  pares.sort((x, y) => -compararTuplas(x, y))      // sort(reverse=True)
  const eleccion = new Map(), usados = new Set()
  for (const [, nom, j] of pares) {
    if (eleccion.has(nom) || usados.has(j)) continue
    eleccion.set(nom, [j, false])
    usados.add(j)
  }
  return eleccion
}

/** `canonizar_orden`: `[conts, cambió]`, con `conts` = Map(talle → piezas). */
export function canonizarOrden(conts, talles) {
  const orden = [...talles.filter((t) => conts.has(t)), ...[...conts.keys()].filter((t) => !talles.includes(t))]
  if (orden.length < 2) return [conts, false]
  const refT = pyMax(orden, (t) => [conts.get(t).length, -orden.indexOf(t)])
  const ref = conts.get(refT)
  const n = ref.length
  const salida = new Map()
  let cambio = false
  for (const t of orden) {
    const pz = conts.get(t)
    if (t === refT || pz.length !== n) { salida.set(t, pz); continue }
    const nombres = new Map()
    for (let i = 0; i < n; i++) nombres.set(i, i)
    const eleccion = emparejarPorSolape(ref, nombres, pz)
    const mapa = new Map()
    for (const [i, [j]] of eleccion) mapa.set(i, j)
    const usados = new Set(mapa.values())
    const libres = []
    for (let j = 0; j < n; j++) if (!usados.has(j)) libres.push(j)
    for (let i = 0; i < n; i++) {
      if (mapa.has(i)) continue
      const j = libres.includes(i) ? i : libres[0]
      mapa.set(i, j)
      libres.splice(libres.indexOf(j), 1)
    }
    for (let i = 0; i < n; i++) if (mapa.get(i) !== i) cambio = true
    salida.set(t, Array.from({ length: n }, (_, i) => pz[mapa.get(i)]))
  }
  return [salida, cambio]
}

/**
 * `correspondencia_incompletos`: para los talles con OTRA cantidad de piezas que la referencia
 * (a los que `canonizarOrden` no puede reordenar), qué pieza de ese talle es cada pieza *i* de la
 * referencia: Map(talle → Map(i → j)). Una *i* sin homóloga (la pieza que a ese talle le falta)
 * no aparece. Los talles completos no figuran: ahí *i* ya es *i*.
 *
 * 🔴 POR QUÉ (2026-09-21, «SHORT PR GOLERA»): al talle XS le falta una pieza. El registro tomaba
 * «la pieza i de cada talle» por posición, así que de la pieza que falta en adelante XS quedaba
 * CORRIDO: se nombraba la espalda y en XS se nombraba el frente («nombro unas piezas y me nombra
 * otras que no se tocan»), y lo mismo con la tela y la tizada. La homóloga sale del dibujo
 * (superposición, la misma regla), no de la posición.
 */
export function correspondenciaIncompletos(conts, talles) {
  const orden = [...talles.filter((t) => conts.has(t)), ...[...conts.keys()].filter((t) => !talles.includes(t))]
  const out = new Map()
  if (orden.length < 2) return out
  const refT = pyMax(orden, (t) => [conts.get(t).length, -orden.indexOf(t)])
  const ref = conts.get(refT)
  const n = ref.length
  for (const t of orden) {
    const pz = conts.get(t)
    if (t === refT || pz.length === n) continue
    const nombres = new Map()
    for (let i = 0; i < n; i++) nombres.set(i, i)
    const mapa = new Map()
    for (const [i, [j]] of emparejarPorSolape(ref, nombres, pz)) mapa.set(i, j)
    out.set(t, mapa)
  }
  return out
}

// ─── la mesa desplegada (sólo contornos) ─────────────────────────────────────────────────────
/** Lo que `desplegar_mesa(contornos=True, paginas=False)` escribe en `m{mesa}.json` (sin el sello). */
export function contornosDeMesa(dibujos, geo, mesa, talles, completos = null) {
  const conts = new Map()
  for (const t of talles) {
    const pzs = piezasDeMesaCruda(dibujos, geo, mesa, t, 0.25, 0.3, completos)
    if (pzs.length) conts.set(t, pzs)
  }
  const [canon, reordenado] = canonizarOrden(conts, talles)
  return { talles: canon, reordenado, marco: geo.marco, U: geo.U }
}

// ─── el registro, el visor ───────────────────────────────────────────────────────────────────
export function anclaPorDefecto(cont) {
  const [x0, , x1, y1] = cont.bbox_mu
  const size = 3.0 * (CM / 10.0)
  return { x: pyRound((x0 + x1) / 2, 1), y: pyRound(y1 - size * 0.25, 1), angulo: 0.0,
    size_pt: pyRound(size, 2), fuente: 'Arial-BoldMT' }
}

/** `acomodo_mesas`: `{mesas: Map(mesa → [x0, y0, x, y]), w, h}`. `porMesa` = Map(mesa → Map(talle → piezas)). */
export function acomodoMesas(porMesa, sepCm = 2.0) {
  let sep = sepCm * CM
  const cajas = new Map()
  for (const [mesa, porT] of porMesa) {
    const xs0 = [], ys0 = [], xs1 = [], ys1 = []
    for (const conts of porT.values()) {
      for (const c of conts || []) {
        const [x0, y0, x1, y1] = c.bbox_mu
        xs0.push(x0); ys0.push(y0); xs1.push(x1); ys1.push(y1)
      }
    }
    if (xs0.length) cajas.set(mesa, [Math.min(...xs0), Math.min(...ys0), Math.max(...xs1), Math.max(...ys1)])
  }
  if (!cajas.size) return { mesas: new Map(), w: 1.0, h: 1.0 }
  const orden = [...cajas.keys()].sort((a, b) => a - b)
  sep = Math.max(sep, Math.max(...[...cajas.values()].map((c) => c[3] - c[1])) * 0.05)
  const armar = (anchoObjetivo) => {
    const pos = new Map()
    let x = sep, y = sep, altoFila = 0.0, an = 0.0
    for (const m of orden) {
      const [x0, y0, x1, y1] = cajas.get(m)
      const w = x1 - x0, h = y1 - y0
      if (x > sep && x + w > anchoObjetivo) { x = sep; y = y + altoFila + sep; altoFila = 0.0 }
      pos.set(m, [x0, y0, x, y])
      x += w + sep
      altoFila = Math.max(altoFila, h)
      an = Math.max(an, x)
    }
    return [pos, an + sep - sep, y + altoFila + sep]
  }
  const anchos = orden.map((m) => cajas.get(m)[2] - cajas.get(m)[0])
  const total = anchos.reduce((a, b) => a + b, 0) + sep * (anchos.length + 1)
  let mejor = null
  for (let k = 1; k <= orden.length; k++) {
    const [pos, w, h] = armar(Math.max(Math.max(...anchos) + 2 * sep, total / k))
    const r = Math.abs((w / Math.max(h, 1e-9)) - 16 / 9)
    if (mejor === null || r < mejor[0]) mejor = [r, pos, w, h]
  }
  return { mesas: mejor[1], w: mejor[2], h: mejor[3] }
}

/** `motor_pedido._item_visor`. */
export function itemVisor(cont, idx, clip, cb, U, zoom) {
  const [x0, y0, x1, y1] = cont.bbox_mu
  const f = (v) => pyFixed(v, 1)
  const X = (cx) => ((cx - cb[0]) * U - clip[0]) * zoom
  const Y = (cy) => ((cb[3] - cy) * U - clip[1]) * zoom
  const path = []
  for (const s of cont.segmentos) {
    const op = s[0]
    if (op === 'm' || op === 'l') path.push(`${op.toUpperCase()} ${f(X(s[1]))} ${f(Y(s[2]))}`)
    else if (op === 'c') path.push(`C ${f(X(s[1]))} ${f(Y(s[2]))} ${f(X(s[3]))} ${f(Y(s[4]))} ${f(X(s[5]))} ${f(Y(s[6]))}`)
    else if (op === 're') {
      const pw = s[3] * U * zoom, ph = s[4] * U * zoom
      path.push(`M ${f(X(s[1]))} ${f(Y(s[2]))} h ${f(pw)} v ${f(-ph)} h ${f(-pw)} Z`)
    } else if (op === 'h') path.push('Z')
  }
  return { idx, px: pyRound((x0 - clip[0]) * zoom, 1), py: pyRound((y0 - clip[1]) * zoom, 1),
    pw: pyRound((x1 - x0) * zoom, 1), ph: pyRound((y1 - y0) * zoom, 1),
    w_cm: pyRound(cont.w / CM, 1), h_cm: pyRound(cont.h / CM, 1), path_svg: path.join(' ') }
}

/** `layout_visor`. `geos` = Map(mesa → geometriaPagina), `piezasMesa` = [[mesa, i, cont], …]. */
export function layoutVisor(geos, piezasMesa, talleRef, talles, sepCm = 2.0, acomodo = null) {
  const zoom = 10.0 / CM
  if (!acomodo) {
    const pm = new Map()
    for (const [m] of piezasMesa) pm.set(m, new Map([[talleRef, piezasMesa.filter(([mm]) => mm === m).map(([, , c]) => c)]]))
    acomodo = acomodoMesas(pm, sepCm)
  }
  const items = piezasMesa.map(([mesa, i, cont], idx) => {
    const { cb, U } = geos.get(mesa)
    const [cx0, cy0, dx, dy] = acomodo.mesas.get(mesa) || [0.0, 0.0, 0.0, 0.0]
    const clip = [cx0 - dx, cy0 - dy, cx0 - dx + 1, cy0 - dy + 1]
    const it = itemVisor(cont, idx, clip, cb, U, zoom)
    it.mesa = mesa
    it.t_idx = i
    return it
  })
  return { mesa: null, talle_ref: talleRef, talles, unidad: 'mm',
    img_w: pyRound(acomodo.w * zoom, 1), img_h: pyRound(acomodo.h * zoom, 1),
    piezas: items, sin_variantes: false, origen: 'con_diseno', formato: 'anidado' }
}

/**
 * `alta_molde_con_diseno(paginas=False)` sin escribir nada: recibe, por mesa, los contornos ya
 * desplegados (`contornosDeMesa`) y devuelve el registro, el visor y el resumen del alta.
 * `porMesa` = Map(mesa → Map(talle → piezas)), `geos` = Map(mesa → geometriaPagina).
 */
export function altaDesdeContornos(porMesa, geos, talles, nMesas) {
  const registro = new Map()
  const problemas = []
  if (!talles.length) {
    problemas.push('El archivo no declara ninguna capa: no se pueden separar los talles. ' +
      'Cada talle tiene que ser una capa con su nombre (M, 3XL, 16…).')
  }
  const mesas = [...porMesa.keys()].sort((a, b) => a - b)
  const antes = new Map(), acum = new Map()
  for (const mesa of mesas) {
    for (const talle of talles) {
      antes.set(`${talle}\u0000${mesa}`, acum.get(talle) || 0)
      acum.set(talle, (acum.get(talle) || 0) + ((porMesa.get(mesa).get(talle) || []).length))
    }
  }
  let n = 0
  for (const mesa of mesas) {
    const pm = porMesa.get(mesa)
    const cuantas = Math.max(...[...pm.values()].map((v) => v.length))
    // los talles con una pieza de menos: cada pieza por su homóloga del dibujo, no por posición
    const eq = correspondenciaIncompletos(pm, talles)
    for (let i = 0; i < cuantas; i++) {
      n += 1
      const nombre = `Pieza ${n}`
      for (const [talle, pzs] of pm) {
        const j = eq.has(talle) ? eq.get(talle).get(i) : i
        if (j === undefined || j >= pzs.length) continue     // este talle no tiene esa pieza: no se inventa
        const cont = pzs[j]
        if (!registro.has(nombre)) registro.set(nombre, new Map())
        registro.get(nombre).set(talle, {
          mesa, pieza_idx: antes.get(`${talle}\u0000${mesa}`) + j, idx_mesa: j,
          w_cm: pyRound(cont.w / cont.user_unit / CM, 1), h_cm: pyRound(cont.h / cont.user_unit / CM, 1),
          bbox_mu: cont.bbox_mu.map((v) => pyRound(v, 2)), ancla: anclaPorDefecto(cont),
        })
      }
    }
  }
  if (!registro.size && !problemas.length) {
    problemas.push('No se detectó ninguna pieza. ¿El archivo trae el diseño adentro de ' +
      'cada pieza, con su máscara de recorte?')
  }
  const visor = new Map()
  const aco = acomodoMesas(porMesa)
  for (const talle of talles) {
    const pm = []
    for (const mesa of mesas) (porMesa.get(mesa).get(talle) || []).forEach((cont, i) => pm.push([mesa, i, cont]))
    if (!pm.length) continue
    visor.set(talle, layoutVisor(geos, pm, talle, talles, 2.0, aco))
  }
  const completos = talles.filter((t) => [...registro.values()].every((pt) => pt.has(t)))
  const detalle = new Map()
  for (const [pieza, porTalle] of registro) {
    const mayor = pyMax([...porTalle.values()], (v) => v.h_cm)
    detalle.set(pieza, {
      mesas: [...new Set([...porTalle.values()].map((v) => v.mesa))].sort((a, b) => a - b),
      talles: talles.filter((t) => porTalle.has(t)),
      talle_mayor_cm: { w: mayor.w_cm, h: mayor.h_cm },
    })
  }
  // AVISAR lo que a un talle le falta (no se inventa ni se reemplaza por otra pieza)
  const con = talles.filter((t) => [...registro.values()].some((pt) => pt.has(t)))
  const faltan = new Map()
  for (const [pieza, porTalle] of registro) {
    for (const t of con) if (!porTalle.has(t)) { if (!faltan.has(t)) faltan.set(t, []); faltan.get(t).push(pieza) }
  }
  const advertencias = [...faltan].map(([t, ps]) => `Al talle ${t} le falta${ps.length > 1 ? 'n' : ''} ${ps.join(', ')}: ` +
    `en ese talle no se registra${ps.length > 1 ? 'n' : ''}.`)
  return { mesas: nMesas, talles, piezas: [...registro.keys()].sort(), completos, registro, problemas,
    advertencias, piezas_detalle: detalle, origen: 'con_diseno', visor }
}

/** Map → objeto plano, recursivo (para escribir JSON como lo escribe Python). */
export function aJSON(v) {
  if (v instanceof Map) {
    const o = {}
    for (const [k, x] of v) o[k] = aJSON(x)
    return o
  }
  if (Array.isArray(v)) return v.map(aJSON)
  if (v && typeof v === 'object') {
    const o = {}
    for (const [k, x] of Object.entries(v)) o[k] = aJSON(x)
    return o
  }
  return v
}
