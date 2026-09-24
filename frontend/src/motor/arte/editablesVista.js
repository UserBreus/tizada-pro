// LOS EDITABLES DEL ARTE PARA EL EDITOR, ARMADOS EN ESTA COMPUTADORA — 2026-09-22.
//
// 🔴 POR QUÉ: «el servidor será sólo para sostener el sistema y la base». `GET
// /api/productos/editables` recorría el arte entero en el pool de procesos del servidor
// (`extraer_editables` + `editables_recolorables` + `mapeo_variantes_arte`, 3-4 s) y dibujaba el
// SVG de cada objeto con pikepdf + PyMuPDF (`svg_editable`, `preview_svg`). Acá se hace lo mismo
// con las traducciones que ya usa la tizada del camino A:
//   · los objetos: `arte/editables.js extraerEditables` (el mismo `_extraer_editables_crudo`);
//   · qué capas admiten color: `molde/capas.js capaAdmiteColor` (`capa_admite_color`);
//   · el dibujo de cada objeto (aislado y, si tiene, RECOLOREADO): `aislarCapaObjetos` /
//     `aislarObjeto` sobre una copia de la página, como `svg_editable`, y el escritor SVG de MuPDF
//     recortado al objeto ±2 pt (el `set_cropbox` de allá);
//   · las mesas por talle del arte (`#talle`/`#rango`): `arte/mapeo.js mapeoVariantesArte`.
// El servidor sólo entrega los datos (`/api/productos/editables_datos`): el mapeo, el registro, la
// config de la variable y qué capas agregó el usuario. La respuesta tiene la MISMA forma que tenía
// el endpoint, así ninguna pantalla cambia.
import { extraerEditables } from './editables.js'
import { mapeoVariantesArte } from './mapeo.js'
import { leerPagina, reescribirPagina, resolutorXObjects } from '../pieza/caminoA.js'
import { analizarCapa, aislarCapaObjetosDe, aislarObjetoDe, capaAdmiteColor } from '../molde/capas.js'
import { sanearOc } from '../molde/paginas.js'
import { normNombre } from '../nombres.js'
import { base64DeTexto } from '../cache.js'
import { svgDePdf } from '../pieza/svg.js'

// MEMORIA POR ARTE (en este hilo): el editor se recarga con cada cambio de color o de variable, y
// recorrer el arte y dibujar los objetos sólo depende del ARCHIVO (su sello) y del color. Es la
// caché que el servidor tenía por (archivo, mtime, tamaño) en `_editables_cacheados`.
const MEMO = new Map()        // clave del arte → {crudos, admite: Map, mv, svgs: Map}
const TOPE_MEMO = 4

function memoDe(clave) {
  if (!clave) return { svgs: new Map(), admite: new Map() }
  let m = MEMO.get(clave)
  if (!m) {
    if (MEMO.size >= TOPE_MEMO) MEMO.delete(MEMO.keys().next().value)
    m = { svgs: new Map(), admite: new Map() }
    MEMO.set(clave, m)
  }
  return m
}

/**
 * La MESA lista para dibujar sus objetos, UNA vez por mesa: copiada del arte ya abierto a un
 * documento chico (`graftPage`), con sus instrucciones leídas y el OC de sus dibujos saneado.
 *
 * 🔴 POR QUÉ (2026-09-23, «me lo tranca todo»): antes cada dibujo ABRÍA EL ARTE ENTERO y releía su
 * mesa. Con un arte real de 16 MB y 352 mesas (y el árbol de páginas roto: «Page tree load failed.
 * Falling back to slow lookup»), 64 objetos + 832 partes = 896 aperturas → el editor tardaba 57 s
 * en armarse (medido en esta PC). Una mesa pesada (1.943 dibujos, 700 KB) se leía 14 veces. La
 * copia es necesaria: aislar REESCRIBE la página y `sanearOc` le saca el OC a sus dibujos, y eso no
 * puede tocar el arte abierto, que se sigue usando para las otras mesas.
 */
function mesaParaDibujar(mupdf, fuente, mesa) {
  const doc = new mupdf.PDFDocument()
  doc.graftPage(-1, fuente, mesa - 1)
  const pageObj = doc.findPage(0)
  const { inst, R } = leerPagina(pageObj)
  const xi = resolutorXObjects(pageObj)
  sanearOc(pageObj, new Set())     // no depende del contenido: una vez alcanza para todos los dibujos
  // el análisis de cada capa (lo caro: recorre la mesa entera), una vez por capa y no por figura
  const analisis = new Map()
  const analisisDe = (capa) => {
    const k = normNombre(capa)
    if (!analisis.has(k)) analisis.set(k, analizarCapa(inst, R, k, xi))
    return analisis.get(k)
  }
  return { doc, pageObj, inst, R, xi, analisisDe }
}

/**
 * El SVG (base64) de una capa editable ENTERA —o de UNA figura con `objId`— aislada del arte y,
 * con `colores` `{obj_id: [fill, stroke]}`, recoloreada. Recortado a `bbox` (coords de la página,
 * y hacia abajo) ±2 pt, como `svg_editable`. `m` = `mesaParaDibujar`. null si falla.
 * Da EXACTAMENTE el mismo SVG que abriendo el arte en cada dibujo (comparado: 896 de 896 iguales).
 */
function svgAislado(mupdf, m, capa, bbox, { objId = null, colores = null } = {}) {
  try {
    let inst
    const a = m.analisisDe(capa)
    if (objId) {
      const c = (colores || {})[objId] || [null, null]
      inst = aislarObjetoDe(m.inst, a, objId, c[0], c[1])
    } else {
      inst = aislarCapaObjetosDe(m.inst, a, colores || {})
    }
    reescribirPagina(m.doc, m.pageObj, inst)
    const x0 = bbox[0] - 2, y0 = bbox[1] - 2, w = (bbox[2] + 2) - x0, h = (bbox[3] + 2) - y0
    const page = m.doc.loadPage(0)
    const buf = new mupdf.Buffer()
    const wr = new mupdf.DocumentWriter(buf, 'svg', 'text=path')
    try {
      const dev = wr.beginPage([0, 0, w, h])
      page.run(dev, mupdf.Matrix.translate(-x0, -y0))
      wr.endPage()
    } finally {
      wr.close()
      page.destroy()
    }
    const s = buf.asString()
    buf.destroy()
    return base64DeTexto(s)
  } catch {
    return null
  }
}

/**
 * Los editables del arte como los devolvía `GET /api/productos/editables`. `datos` =
 * `/api/productos/editables_datos` (mapeo, registro, talles, capas, inyectadas, agregados, sep);
 * `agregados` trae además los bytes del PDF de cada objeto agregado (`bytes`).
 */
export function editablesParaEditor(mupdf, bytes, datos) {
  const memo = memoDe(datos.clave)
  // el arte se abre UNA vez y cada mesa se prepara UNA vez para todos sus dibujos (ver `mesaParaDibujar`)
  let fuente = null
  const mesas = new Map()           // mesa → preparada (o null si no se pudo)
  const svg = (mesa, capa, bbox, op) => {
    const k = JSON.stringify([mesa, capa, bbox, op.objId || null, op.colores || null])
    if (!memo.svgs.has(k)) {
      if (!mesas.has(mesa)) {
        let m = null
        try {
          if (!fuente) fuente = mupdf.Document.openDocument(bytes, 'application/pdf').asPDF()
          m = mesaParaDibujar(mupdf, fuente, mesa)
        } catch { m = null }
        mesas.set(mesa, m)
      }
      const m = mesas.get(mesa)
      memo.svgs.set(k, m ? svgAislado(mupdf, m, capa, bbox, op) : null)
    }
    return memo.svgs.get(k)
  }
  const registro = datos.registro || {}
  const talles = datos.talles || []
  const mesa2pieza = new Map()
  for (const [pieza, mesa] of Object.entries(datos.mapeo || {})) if (mesa) mesa2pieza.set(Number(mesa), pieza)
  // ARTE POR RANGO (#talle/#rango): los editables pueden vivir en mesas POR TALLE que no están en el
  // mapeo por defecto; sin esto quedaban sin pieza y el editor no los mostraba
  try {
    const kmv = JSON.stringify([Object.keys(registro).sort(), talles])
    if (!memo.mv || memo.kmv !== kmv) { memo.mv = mapeoVariantesArte(mupdf, bytes, registro, talles) || {}; memo.kmv = kmv }
    const mv = memo.mv
    for (const [pz, porTalle] of Object.entries(mv)) {
      for (const m of Object.values(porTalle || {})) if (!mesa2pieza.has(Number(m))) mesa2pieza.set(Number(m), pz)
    }
  } catch { /* como el servidor: sin las mesas por talle */ }
  const inyectadas = new Set(datos.inyectadas || [])
  const capasCfg = datos.capas || {}
  const sep = datos.sep || '\x1f'
  // `capa_admite_color` por capa: las instrucciones de cada mesa se leen una sola vez
  const paginas = new Map()
  let doc = null
  const admiteColor = (mesa, capa) => {
    const k = `${mesa}|${capa}`
    if (memo.admite.has(k)) return memo.admite.get(k)
    const v = admiteColorCalc(mesa, capa)
    memo.admite.set(k, v)
    return v
  }
  const admiteColorCalc = (mesa, capa) => {
    try {
      if (!doc) doc = mupdf.Document.openDocument(bytes, 'application/pdf').asPDF()
      if (!paginas.has(mesa)) paginas.set(mesa, leerPagina(doc.findPage(mesa - 1)))
      const { inst, R } = paginas.get(mesa)
      return !!capaAdmiteColor(inst, R, normNombre(capa))
    } catch { return false }
  }
  const objetos = []
  try {
    if (!memo.crudos) memo.crudos = extraerEditables(mupdf, bytes)
    for (const o0 of memo.crudos) {
      const o = { ...o0 }
      const obs = o.objetos || []
      delete o.objetos
      const entry = capasCfg[o.nombre] || {}
      const sub = entry.objetos || {}
      o.pieza = mesa2pieza.get(o.mesa) || ''
      o.label = o.nombre; o.obj_id = null
      o.quitable = inyectadas.has(o.capa)
      o.transforms = entry.transforms || {}
      o.color = entry.color ?? null
      o.recolorable = admiteColor(o.mesa, o.capa) || obs.some((b) => b.recolorable)
      o.pos = null                                   // ninguna pantalla lo usa
      // el COLOR de cada figura para ESTA variable (el de la capa vale para las que no tienen)
      const layC = entry.color_c || null
      const cols = {}
      for (const b of obs) {
        const c = ((sub[b.obj_id] || {}).color_c) || layC
        if (c) cols[b.obj_id] = [c.fill ?? null, c.stroke ?? null]
      }
      const hayColor = Object.keys(cols).length > 0
      o.partes = obs.length >= 2 ? obs.map((b, i) => ({
        obj_id: b.obj_id, ident: b.obj_id ? `${o.nombre}${sep}${b.obj_id}` : o.nombre,
        label: `${o.nombre} (${i + 1})`, recolorable: !!b.recolorable,
        color: (sub[b.obj_id] || {}).color ?? null, fill: b.fill,
        svg: svg(o.mesa, o.capa, b.bbox_mu, { objId: b.obj_id, colores: cols[b.obj_id] ? cols : null }),
        w_cm: b.w_cm, h_cm: b.h_cm,
      })) : []
      // el dibujo del objeto en el editor: con su color (si tiene) — LEY arte = tizada
      o.svg = svg(o.mesa, o.capa, o.bbox_mu, { colores: hayColor ? cols : null })
      o.thumb = null
      objetos.push(o)
    }
  } finally {
    if (doc) { try { doc.destroy() } catch { /* nada */ } }
    for (const m of mesas.values()) { if (m) { try { m.doc.destroy() } catch { /* nada */ } } }
    if (fuente) { try { fuente.destroy() } catch { /* nada */ } }
  }
  // los OBJETOS AGREGADOS, con la MISMA forma que uno del arte (el marco lo resuelve cada vista)
  for (const a of datos.agregados || []) {
    let svg = ''
    try { if (a.bytes) svg = base64DeTexto(svgDePdf(mupdf, a.bytes)) } catch { svg = '' }
    objetos.push({
      nombre: a.nombre || a.id, capa: a.nombre || a.id, pieza: a.pieza || '', mesa: 0, svg, thumb: null,
      w_cm: a.w_cm, h_cm: a.h_cm, mesa_rect: null, bbox_mu: null, pos: null,
      transforms: a.transforms || {}, agregado: true, oid: a.id, color: null, recolorable: false,
    })
  }
  return { objetos, talles, piezas: Object.keys(registro).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0)) }
}
