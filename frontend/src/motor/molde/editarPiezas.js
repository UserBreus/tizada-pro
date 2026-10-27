// EDITAR PIEZAS DEL MOLDE: REEMPLAZAR SU FORMA o MOVERLAS, EN SU LUGAR (MAPA 746) — 2026-10-23.
//
// Pedido del usuario: «elegir piezas y actualizarlas: cargar un archivo nuevo a un molde, reubicar las
// piezas donde quiera y reemplazarlas». Decidió: se cambia la FORMA conservando todo lo configurado
// (nombre, variables, telas, etiqueta, arte); la forma viene de un archivo; la posición queda GUARDADA;
// en todos los talles o en los que elija.
//
// 🔴 POR QUÉ SE EDITA EN EL LUGAR Y NO «SE SACA Y SE AGREGA»: el número de una pieza (`pieza_idx`) ES su
// posición en el ORDEN DE DIBUJO de su capa (MAPA 182). Sacar la vieja y agregar la nueva al final
// renumeraría a todas las que siguen, y con ellas el registro, las variables, los grupos y el emparejado.
// Acá la pieza se toca DONDE ESTÁ en el content stream: mover = envolverla en `q … cm … Q`; reemplazar =
// cambiar SUS operadores de trazado por los de la forma nueva (con su mismo operador de pintado). Ninguna
// otra pieza cambia de lugar en el orden → nadie se renumera.
//
// Lo que acompaña a la pieza (marcas internas: piquetes, línea de hilo; y los textos que tiene adentro)
// se mueve con ella; al REEMPLAZAR, las marcas viejas se sacan (eran de la forma anterior) y los textos se
// corren lo mismo que la pieza. Otra pieza que caiga adentro de su caja NO se toca (`otras`).
//
// El archivo del usuario no se toca: esto devuelve los bytes de una VERSIÓN nueva. Y no se guarda nada
// sin verificar (`verificarEdicion`): se vuelve a leer el molde y, si alguna pieza que no se tocó cambió
// de número o de lugar, o la cantidad no da, se rechaza. Gemelo: `piezas_molde.editar_piezas`.
import { instrucciones, escribir, contenidoCrudo } from '../pdf/contenido.js'
import { pyFixed } from '../py.js'
import { ocgPorNombre, nombreEnRecursos } from './herramientas.js'

const nulo = (o) => !o || (o.isNull && o.isNull())
const CONSTRUCCION = new Set(['m', 'l', 'c', 'v', 'y', 're', 'h'])
const PINTADO = new Set(['S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*', 'n'])
const TEXTO = new Set(['Tj', 'TJ', "'", '"'])
const num = (v) => (v && v.i !== undefined ? Number(v.i) : v && v.r !== undefined ? Number(v.r) : NaN)
const mul = (a, b) => [a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3], a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3],
  a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5]]
const aplicar = (m, x, y) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]]
const R = (v) => ({ r: pyFixed(v, 4) })

/** Nombre de recurso (`MC0`) → nombre de la capa (`M`), de `/Resources/Properties` de la página. */
export function capasDeRecursos(pageObj) {
  const m = new Map()
  let res = pageObj.get('Resources')
  if (nulo(res)) res = pageObj.getInheritable ? pageObj.getInheritable('Resources') : null
  if (nulo(res)) return m
  const props = res.get('Properties')
  if (nulo(props)) return m
  props.forEach((v, k) => { try { m.set(String(k), v.get('Name').asString()) } catch { /* no es una capa */ } })
  return m
}

/**
 * Las unidades del contenido: cada trazado pintado y cada bloque de texto, con su CAPA (la OC más
 * interna que lo envuelve), la CTM con que se dibuja y dónde cae en el lienzo (coordenadas crudas,
 * y hacia arriba, las mismas de `bbox_raw`). Gemelo: `piezas_molde._unidades_con_capa`.
 */
export function unidadesConCapa(inst, capas) {
  let ctm = [1, 0, 0, 1, 0, 0]
  const pila = [], pilaMC = [], out = []
  const capaActual = () => { for (let k = pilaMC.length - 1; k >= 0; k--) if (pilaMC[k]) return pilaMC[k]; return null }
  let ini = null, pts = [], clip = false
  // TEXTO POR TRAMOS: un bloque BT…ET puede llevar las etiquetas de VARIAS piezas (cada una con su Tm);
  // la unidad es el tramo que arranca en un posicionamiento (Tm/Td/TD/T*/'/") y llega hasta el próximo
  let bt = null, tlm = [1, 0, 0, 1, 0, 0], tl = 0, tramo = null
  const lin = (m, tx, ty) => [m[0], m[1], m[2], m[3], m[4] + tx * m[0] + ty * m[2], m[5] + tx * m[1] + ty * m[3]]
  const cerrarTramo = (fin) => {
    if (tramo && tramo.muestra) out.push({ ...tramo, fin, tipo: 'texto', capa: capaActual(), ctm: ctm.slice() })
    tramo = null
  }
  inst.forEach((it, i) => {
    const op = it.op
    const f = () => (it.args || []).map(num)
    if (op === 'q') pila.push(ctm)
    else if (op === 'Q') ctm = pila.length ? pila.pop() : ctm
    else if (op === 'cm') { const a = f(); if (a.length === 6 && a.every(Number.isFinite)) ctm = mul(a, ctm) }
    else if (op === 'BDC' || op === 'BMC') {
      let c = null
      const a = it.args || []
      if (op === 'BDC' && a[0] && a[0].n === 'OC' && a[1] && a[1].n !== undefined) c = capas.get(a[1].n) || null
      pilaMC.push(c)
    } else if (op === 'EMC') pilaMC.pop()
    else if (op === 'TL') { const a = f(); if (a.length === 1 && Number.isFinite(a[0])) tl = a[0] }
    else if (op === 'BT') { bt = i; tlm = [1, 0, 0, 1, 0, 0]; tramo = { bt: i, pos: null, op: null, ini: i + 1, antes: tlm.slice(), tlm: tlm.slice(), muestra: false } }
    else if (bt !== null && (op === 'Tm' || op === 'Td' || op === 'TD' || op === 'T*' || op === "'" || op === '"')) {
      cerrarTramo(i - 1)
      const a = f()
      const antes = tlm.slice()                             // la matriz de línea JUSTO antes de posicionar
      if (op === 'Tm') { if (a.length === 6 && a.every(Number.isFinite)) tlm = a }
      else if (op === 'Td' || op === 'TD') {
        if (a.length === 2 && a.every(Number.isFinite)) { if (op === 'TD') tl = -a[1]; tlm = lin(tlm, a[0], a[1]) }
      } else tlm = lin(tlm, 0, -tl)                         // T*, ' y ": a la línea siguiente (interlineado)
      tramo = { bt, pos: i, op, ini: i, antes, tlm: tlm.slice(), muestra: op === "'" || op === '"' }
      if (tramo.muestra) tramo.pt = aplicar(ctm, tlm[4], tlm[5])
    } else if (TEXTO.has(op)) {
      if (tramo) { tramo.muestra = true; if (!tramo.pt) tramo.pt = aplicar(ctm, tramo.tlm[4], tramo.tlm[5]) }
    } else if (op === 'ET') { cerrarTramo(i - 1); bt = null }
    else if (CONSTRUCCION.has(op)) {
      if (ini === null) { ini = i; pts = []; clip = false }
      const a = f()
      if (op === 're' && a.length === 4) {
        const [x, y, w, h] = a
        for (const [px, py] of [[x, y], [x + w, y], [x, y + h], [x + w, y + h]]) pts.push(aplicar(ctm, px, py))
      } else for (let k = 0; k + 1 < a.length; k += 2) pts.push(aplicar(ctm, a[k], a[k + 1]))
    } else if (op === 'W' || op === 'W*') clip = true
    else if (PINTADO.has(op)) {
      if (ini !== null && pts.length) {
        const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1])
        out.push({ ini, fin: i, tipo: 'trazado', capa: capaActual(), ctm: ctm.slice(), clip, pinta: op,
                   bbox: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)] })
      }
      ini = null; pts = []; clip = false
    }
  })
  return out
}

const centro = (b) => [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2]
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1])
const tolDe = (b) => Math.max(1.0, 0.15 * Math.min(Math.abs(b[2] - b[0]), Math.abs(b[3] - b[1])))
const adentro = (pt, b, m) => pt[0] >= b[0] - m && pt[0] <= b[2] + m && pt[1] >= b[1] - m && pt[1] <= b[3] + m
const cajaAdentro = (a, b, m) => a[0] >= b[0] - m && a[2] <= b[2] + m && a[1] >= b[1] - m && a[3] <= b[3] + m
const iou = (a, b) => {
  const ix = Math.max(0, Math.min(a[2], b[2]) - Math.max(a[0], b[0])), iy = Math.max(0, Math.min(a[3], b[3]) - Math.max(a[1], b[1]))
  const inter = ix * iy, un = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
  return un > 0 ? inter / un : 0
}

/**
 * CADA PIEZA DEL TALLE ↔ SU TRAZO EN EL CONTENIDO, todas a la vez (MAPA 747). Comparar sólo centros
 * confundía a una pieza chica y finita que cae adentro de la caja de otra con una «marca» de esa otra (y
 * se movía con ella: lo frenó la verificación). Acá cada pieza detectada (`cajas`, en el orden del molde)
 * se queda con el trazo que más se le superpone (las más grandes eligen primero); vale si se superponen la
 * mitad o si los centros están cerca. → `[unidad | undefined]` por pieza. Gemelo: `_emparejar_trazos`.
 */
export function emparejarTrazos(trazos, cajas) {
  const usados = new Set(), out = []
  const orden = cajas.map((b, i) => [i, (b[2] - b[0]) * (b[3] - b[1])]).sort((a, b) => b[1] - a[1] || a[0] - b[0])
  for (const [i] of orden) {
    const b = cajas[i]
    let mejor = null
    for (const u of trazos) {
      if (usados.has(u)) continue
      const s = iou(u.bbox, b), d = dist(centro(u.bbox), centro(b))
      if (s < 0.5 && d > tolDe(b)) continue
      const p = s - d * 1e-6
      if (!mejor || p > mejor[0]) mejor = [p, u]
    }
    if (mejor) { usados.add(mejor[1]); out[i] = mejor[1] }
  }
  return out
}

/** Traslado en el espacio del usuario de la CTM `m` que mueve (dx, dy) en el lienzo. */
function trasladoUsuario(m, dx, dy) {
  const det = m[0] * m[3] - m[1] * m[2]
  if (!det) throw new Error('una pieza del molde se dibuja con una transformación que no se puede invertir')
  return [(m[3] * dx - m[2] * dy) / det, (-m[1] * dx + m[0] * dy) / det]
}

/** Segmentos crudos del lienzo → instrucciones de trazado en el espacio de usuario de la CTM `m`. */
function trazadoEnUsuario(segs, m) {
  const det = m[0] * m[3] - m[1] * m[2]
  if (!det) throw new Error('una pieza del molde se dibuja con una transformación que no se puede invertir')
  const inv = (X, Y) => [(m[3] * (X - m[4]) - m[2] * (Y - m[5])) / det, (-m[1] * (X - m[4]) + m[0] * (Y - m[5])) / det]
  const out = []
  for (const s of segs || []) {
    const op = s[0]
    if (op === 'm' || op === 'l') { const p = inv(s[1], s[2]); out.push({ op, args: [R(p[0]), R(p[1])] }) }
    else if (op === 'c') {
      const a = inv(s[1], s[2]), b = inv(s[3], s[4]), c = inv(s[5], s[6])
      out.push({ op: 'c', args: [R(a[0]), R(a[1]), R(b[0]), R(b[1]), R(c[0]), R(c[1])] })
    } else if (op === 're') {
      // un rectángulo del lienzo puede no serlo en el espacio de usuario (rotación): va como polígono
      const [x, y, w, h] = [s[1], s[2], s[3], s[4]]
      const q = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]].map(([X, Y]) => inv(X, Y))
      out.push({ op: 'm', args: [R(q[0][0]), R(q[0][1])] })
      for (const p of q.slice(1)) out.push({ op: 'l', args: [R(p[0]), R(p[1])] })
      out.push({ op: 'h', args: [] })
    } else if (op === 'h') out.push({ op: 'h', args: [] })
  }
  return out
}

/** Segmentos crudos corridos (dx, dy). */
export function trasladarSegs(segs, dx, dy) {
  return (segs || []).map((s) => {
    if (s[0] === 'm' || s[0] === 'l') return [s[0], s[1] + dx, s[2] + dy]
    if (s[0] === 'c') return ['c', s[1] + dx, s[2] + dy, s[3] + dx, s[4] + dy, s[5] + dx, s[6] + dy]
    if (s[0] === 're') return ['re', s[1] + dx, s[2] + dy, s[3], s[4]]
    return s.slice()
  })
}

/**
 * DE LO PEDIDO A LAS EDICIONES, CON LA DETECCIÓN DE ESTA PC (MAPA 746 bis): el servidor manda cada cambio
 * por el NÚMERO de la pieza en su talle (`idx`) —o, al agregar, por una pieza de referencia (`ref`)— más
 * el corrimiento y la forma nueva CENTRADA en (0, 0) con su caja (`caja`). La caja de cada pieza y dónde
 * cae la forma salen de la detección que esta misma PC hace del molde (`antes`): así el servidor no tiene
 * que pedir la detección por talle (una ida y vuelta menos) y no se usa una caja vieja.
 * `pedidos` = `[{talle, tipo: 'mover'|'reemplazar'|'agregar', idx?, ref?, dx, dy, forma?, caja?}]`.
 * → `{ediciones, esperado}`. Gemelo: `piezas_molde.resolver_ediciones`.
 */
export function resolverEdiciones(antes, pedidos) {
  const ediciones = [], esperado = [], nuevas = {}
  for (const p of pedidos || []) {
    const cs = antes[p.talle] || []
    const dx = Number(p.dx || 0), dy = Number(p.dy || 0)
    const otras = cs.map((c) => c.bbox_raw)
    if (p.tipo === 'agregar') {
      const r = cs[p.ref]
      if (!r) throw new Error(`no está la pieza de referencia en el talle ${p.talle}`)
      const c = centro(r.bbox_raw), x = c[0] + dx, y = c[1] + dy
      if (nuevas[p.talle] === undefined) nuevas[p.talle] = cs.length
      ediciones.push({ talle: p.talle, tipo: 'agregar', segmentos: trasladarSegs(p.forma, x, y) })
      esperado.push({ talle: p.talle, idx: nuevas[p.talle]++, nueva: true, bbox: [p.caja[0] + x, p.caja[1] + y, p.caja[2] + x, p.caja[3] + y] })
      continue
    }
    const v = cs[p.idx]
    if (!v) throw new Error(`la pieza ${Number(p.idx) + 1} no está en el talle ${p.talle}`)
    const b = v.bbox_raw
    if (p.tipo === 'mover') {
      ediciones.push({ talle: p.talle, tipo: 'mover', idx: p.idx, bbox: b, dx, dy, otras })
      esperado.push({ talle: p.talle, idx: p.idx, bbox: [b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy] })
    } else if (p.tipo === 'reemplazar') {
      const c = centro(b), x = c[0] + dx, y = c[1] + dy
      ediciones.push({ talle: p.talle, tipo: 'reemplazar', idx: p.idx, bbox: b, dx, dy, otras, segmentos: trasladarSegs(p.forma, x, y) })
      esperado.push({ talle: p.talle, idx: p.idx, bbox: [p.caja[0] + x, p.caja[1] + y, p.caja[2] + x, p.caja[3] + y] })
    } else throw new Error(`cambio desconocido: ${p.tipo}`)
  }
  return { ediciones, esperado }
}

/**
 * `ediciones` = `[{talle, tipo: 'mover'|'reemplazar'|'agregar', bbox, dx, dy, segmentos?, otras}]` (crudas):
 *  · `bbox` = la caja de la pieza a tocar (`bbox_raw` de la detección) — con eso se la encuentra;
 *  · `dx`/`dy` = cuánto se corre en el lienzo (y hacia arriba); al reemplazar, cuánto se corren sus textos;
 *  · `segmentos` = la forma nueva, YA en su lugar final (sólo `reemplazar`);
 *  · `otras` = las cajas de las DEMÁS piezas de ese talle (las que caen adentro no son «marcas»).
 * → `{bytes}` de la versión nueva. Gemelo: `piezas_molde.editar_piezas`.
 */
export function editarPiezas(mupdf, bytes, ediciones, mesa = 1) {
  if (!ediciones || !ediciones.length) throw new Error('no hay nada que cambiar')
  const doc = new mupdf.PDFDocument(bytes)
  try {
    const pageObj = doc.findPage(mesa - 1)
    const inst = [...instrucciones(contenidoCrudo(doc.loadPage(mesa - 1)))]
    const unidades = unidadesConCapa(inst, capasDeRecursos(pageObj))
    const usadas = new Set()
    const antes = new Map(), despues = new Map(), reemplazo = new Map(), borrar = new Set()
    const tramosMovidos = new Map()                          // tramo → [tu, tv] en el espacio del usuario
    const envolver = (u, dx, dy) => {
      if (u.tipo === 'texto') { tramosMovidos.set(u, trasladoUsuario(u.ctm, dx, dy)); return }
      const [tu, tv] = trasladoUsuario(u.ctm, dx, dy)
      if (!antes.has(u.ini)) antes.set(u.ini, [])
      antes.get(u.ini).push({ op: 'q', args: [] }, { op: 'cm', args: [{ i: 1 }, { i: 0 }, { i: 0 }, { i: 1 }, R(tu), R(tv)] })
      if (!despues.has(u.fin)) despues.set(u.fin, [])
      despues.get(u.fin).push({ op: 'Q', args: [] })
    }
    const agregadas = []
    const porTalle = new Map()               // talle → {trazos, pares}: el emparejado de TODAS sus piezas
    const igual = (a, b) => a.every((v, k) => Math.abs(v - b[k]) < 0.5)
    for (const e of ediciones) {
      if (e.tipo === 'agregar') { agregadas.push(e); continue }
      const cajas = e.otras && e.otras.length ? e.otras : [e.bbox]
      if (!porTalle.has(e.talle)) {
        const trazosT = unidades.filter((u) => u.capa === e.talle && u.tipo === 'trazado' && !u.clip && u.pinta !== 'n')
        porTalle.set(e.talle, { trazos: trazosT, pares: emparejarTrazos(trazosT, cajas) })
      }
      const { trazos: trazosT, pares } = porTalle.get(e.talle)
      const k = e.idx != null ? e.idx : cajas.findIndex((b) => igual(b, e.bbox))
      const pieza = k >= 0 ? pares[k] : undefined
      if (!pieza || usadas.has(pieza)) throw new Error(`no se encontró la pieza dentro del molde (talle ${e.talle}): este molde no se puede editar así`)
      const deCapa = unidades.filter((u) => u.capa === e.talle && !usadas.has(u))
      const trazos = trazosT.filter((u) => !usadas.has(u))
      // el MISMO contorno pintado dos veces (relleno y trazo por separado) es la misma pieza
      const iguales = trazos.filter((u) => u !== pieza && igual(u.bbox, pieza.bbox) && !pares.includes(u))
      // las OTRAS piezas (y sus copias pintadas dos veces) nunca son marcas de ésta
      const deOtras = pares.filter((u, j) => u && j !== k)
      const esOtra = (u) => deOtras.includes(u) || deOtras.some((o) => igual(o.bbox, u.bbox))
      const m = 0.01 * Math.max(pieza.bbox[2] - pieza.bbox[0], pieza.bbox[3] - pieza.bbox[1])
      const marcas = trazos.filter((u) => u !== pieza && !iguales.includes(u) && !esOtra(u) && cajaAdentro(u.bbox, pieza.bbox, m))
      const textos = deCapa.filter((u) => u.tipo === 'texto' && adentro(u.pt, pieza.bbox, m))
      for (const u of [pieza, ...iguales, ...marcas, ...textos]) usadas.add(u)
      const dx = Number(e.dx || 0), dy = Number(e.dy || 0)
      if (e.tipo === 'mover') {
        for (const u of [pieza, ...iguales, ...marcas, ...textos]) envolver(u, dx, dy)
      } else if (e.tipo === 'reemplazar') {
        if (!e.segmentos || !e.segmentos.length) throw new Error('falta la forma nueva de la pieza')
        for (const u of [pieza, ...iguales]) reemplazo.set(u.ini, { fin: u.fin, inst: [...trazadoEnUsuario(e.segmentos, u.ctm), { op: inst[u.fin].op, args: [] }] })
        for (const u of marcas) { for (let k = u.ini; k <= u.fin; k++) borrar.add(k) }
        if (dx || dy) for (const u of textos) envolver(u, dx, dy)
      } else throw new Error(`cambio desconocido: ${e.tipo}`)
    }
    // TEXTO: antes de cada tramo movido va un Tm ABSOLUTO con su lugar corrido (si el tramo se posicionaba
    // con un Tm, se corre ése mismo); antes del tramo SIGUIENTE —si no se mueve y se posicionaba relativo
    // al anterior (Td/TD/T*/'/")— va un Tm con la matriz de línea que tenía, así ninguna etiqueta de otra
    // pieza se corre. Los operadores originales quedan como estaban.
    const tmDe = (m, t = [0, 0]) => ({ op: 'Tm', args: [R(m[0]), R(m[1]), R(m[2]), R(m[3]), R(m[4] + t[0]), R(m[5] + t[1])] })
    const sust = new Map(), meter = new Map()
    const porBloque = new Map()
    for (const u of unidades) if (u.tipo === 'texto') { if (!porBloque.has(u.bt)) porBloque.set(u.bt, []); porBloque.get(u.bt).push(u) }
    for (const tramos of porBloque.values()) {
      tramos.forEach((u, k) => {
        const prev = tramos[k - 1]
        if (tramosMovidos.has(u)) {
          const t = tramosMovidos.get(u)
          if (u.op === 'Tm') sust.set(u.pos, [tmDe(u.tlm, t)])
          else meter.set(u.pos === null ? u.ini : u.pos, [tmDe(u.antes, t)])
        } else if (prev && tramosMovidos.has(prev) && u.op && u.op !== 'Tm') {
          meter.set(u.pos, [tmDe(u.antes)])
        }
      })
    }
    const nuevo = []
    for (let i = 0; i < inst.length; i++) {
      if (meter.has(i)) nuevo.push(...meter.get(i))
      if (sust.has(i)) { nuevo.push(...sust.get(i)); continue }
      if (antes.has(i)) nuevo.push(...antes.get(i))
      if (reemplazo.has(i)) {
        const r = reemplazo.get(i)
        nuevo.push(...r.inst)
        if (despues.has(r.fin)) nuevo.push(...despues.get(r.fin))
        i = r.fin
        continue
      }
      if (!borrar.has(i)) nuevo.push(inst[i])
      if (despues.has(i)) nuevo.push(...despues.get(i))
    }
    // AGREGAR: al final del contenido y ADENTRO de la capa de su talle (la misma OCG que ya existe: no se
    // crea ninguna capa ni se cambia el orden de las capas). Al final = la última de su talle = nadie se
    // renumera (como `agregarPieza`). Trazo fino y negro, como el resto del contorno.
    for (const e of agregadas) {
      const ocg = ocgPorNombre(doc, e.talle)
      if (!ocg) throw new Error(`el talle ${e.talle} no existe como capa en el molde`)
      const nom = nombreEnRecursos(doc, pageObj, ocg, 'OCpz')
      nuevo.push({ op: 'q', args: [] }, { op: 'BDC', args: [{ n: 'OC' }, { n: nom }] },
        { op: 'RG', args: [{ i: 0 }, { i: 0 }, { i: 0 }] }, { op: 'w', args: [{ i: 1 }] },
        ...trazadoEnUsuario(e.segmentos, [1, 0, 0, 1, 0, 0]), { op: 'S', args: [] }, { op: 'EMC', args: [] }, { op: 'Q', args: [] })
    }
    pageObj.put('Contents', doc.addStream(escribir(nuevo), doc.newDictionary()))
    return { bytes: doc.saveToBuffer('compress').asUint8Array().slice() }
  } finally { doc.destroy() }
}

/**
 * ¿La edición hizo SÓLO lo pedido? `antes`/`despues` = `{talle: [contornos]}` (detección de los dos
 * archivos); `esperado` = `[{talle, idx, bbox}]` con la caja que tiene que tener cada pieza tocada.
 * → lista de problemas en palabras (vacía = bien). Gemelo: `piezas_molde.verificar_edicion`.
 */
export function verificarEdicion(antes, despues, esperado) {
  const mal = []
  const tocadas = new Map(esperado.map((x) => [`${x.talle}|${x.idx}`, x.bbox]))
  const masDe = {}
  for (const x of esperado) if (x.nueva) masDe[x.talle] = (masDe[x.talle] || 0) + 1
  const caja = (nb, esp) => {
    const tol = Math.max(2.0, 0.03 * Math.max(esp[2] - esp[0], esp[3] - esp[1]))
    return dist(centro(nb), centro(esp)) <= tol && Math.abs((nb[2] - nb[0]) - (esp[2] - esp[0])) <= tol && Math.abs((nb[3] - nb[1]) - (esp[3] - esp[1])) <= tol
  }
  for (const t of Object.keys(antes)) {
    const a = antes[t] || [], d = despues[t] || []
    const debe = a.length + (masDe[t] || 0)
    if (d.length !== debe) { mal.push(`en el talle ${t} quedaron ${d.length} piezas y tenían que ser ${debe}`); continue }
    for (let i = a.length; i < d.length; i++) {
      const esp = tocadas.get(`${t}|${i}`)
      if (!esp || !caja(d[i].bbox_raw, esp)) mal.push(`la pieza nueva ${i + 1} del talle ${t} no quedó donde tenía que quedar`)
    }
    a.forEach((c, i) => {
      const nb = d[i].bbox_raw
      const esp = tocadas.get(`${t}|${i}`)
      if (esp) {
        const tol = Math.max(2.0, 0.03 * Math.max(esp[2] - esp[0], esp[3] - esp[1]))
        if (dist(centro(nb), centro(esp)) > tol || Math.abs((nb[2] - nb[0]) - (esp[2] - esp[0])) > tol || Math.abs((nb[3] - nb[1]) - (esp[3] - esp[1])) > tol) {
          mal.push(`la pieza ${i + 1} del talle ${t} no quedó donde tenía que quedar`)
        }
      } else if (c.bbox_raw.some((v, k) => Math.abs(v - nb[k]) > 0.6)) {
        mal.push(`la pieza ${i + 1} del talle ${t} cambió sin que se la tocara`)
      }
    })
  }
  return mal
}
