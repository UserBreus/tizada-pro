// «EDITAR DISEÑO» EN ESTA COMPUTADORA — 2026-09-22.
//
// 🔴 POR QUÉ: «el servidor será sólo para sostener el sistema y la base». Agregar un objeto al
// diseño, colocarlo en una pieza y quitarlo reescribían el arte con pikepdf en el servidor
// (`objetos_agregados.py`: `normalizar_a_pdf`, `inyectar_editable`, `quitar_editable`). Acá se hace
// lo mismo con MuPDF (mismo resultado: el objeto entra como una capa OCG «Editable <nombre>» con un
// Form XObject, en un content stream propio de cada mesa) y el servidor sólo GUARDA la versión
// nueva del arte (el original del usuario nunca se toca: `arte.v<N>.ai`).
import { formDePagina, rectPagina } from '../pieza/caminoA.js'
import { mapeoVariantesArte } from './mapeo.js'

const PT_A_CM = 2.54 / 72.0
const nulo = (o) => !o || (o.isNull && o.isNull())
const fx6 = (v) => (Math.round(v * 1e6) / 1e6).toFixed(6)
const fx3 = (v) => (Math.round(v * 1e3) / 1e3).toFixed(3)

/**
 * `normalizar_a_pdf` para lo que MuPDF sabe abrir: un PDF/.ai (su 1ª página) o una imagen PNG/JPG
 * (a su tamaño físico: los dpi que trae, 96 si no trae). Devuelve `{pdf, w_cm, h_cm, tipo}`. El SVG
 * llega ya convertido a PDF (`svgPdf.js`, en la pantalla: el hilo no tiene lector de XML).
 */
export function normalizarObjeto(mupdf, bytes, nombreArchivo) {
  const ext = String(nombreArchivo || '').toLowerCase().split('.').pop()
  if (['pdf', 'ai', 'svg'].includes(ext)) {
    const src = new mupdf.PDFDocument(bytes)
    try {
      if (src.countPages() === 0) throw new Error('el PDF/AI no tiene páginas')
      const una = new mupdf.PDFDocument()
      try {
        una.graftPage(0, src, 0)
        const pg = src.loadPage(0)
        const r = pg.getBounds()
        pg.destroy()
        const pdf = una.saveToBuffer('compress').asUint8Array().slice()
        return { pdf, w_cm: (r[2] - r[0]) * PT_A_CM, h_cm: (r[3] - r[1]) * PT_A_CM, tipo: 'vector' }
      } finally { una.destroy() }
    } finally { src.destroy() }
  }
  if (['png', 'jpg', 'jpeg'].includes(ext)) {
    const img = new mupdf.Image(bytes)
    try {
      const w = img.getWidth(), h = img.getHeight()
      // los dpi REALES si los trae (un PNG a 300 dpi para sublimar entra con su medida física)
      let dpi = Number(img.getYResolution && img.getYResolution()) || 0
      if (!(dpi > 1) || dpi === 72 && !tieneDpi(bytes, ext)) dpi = 96.0
      const doc = new mupdf.PDFDocument()
      try {
        const ref = doc.addImage(img)
        const res = doc.newDictionary(), xo = doc.newDictionary()
        xo.put('Im0', ref)
        res.put('XObject', xo)
        doc.insertPage(0, doc.addPage([0, 0, w, h], 0, res, `q ${w} 0 0 ${h} 0 0 cm /Im0 Do Q`))
        const pdf = doc.saveToBuffer('compress').asUint8Array().slice()
        return { pdf, w_cm: w / dpi * 2.54, h_cm: h / dpi * 2.54, tipo: 'imagen' }
      } finally { doc.destroy() }
    } finally { img.destroy() }
  }
  throw new Error(`formato no soportado: ${nombreArchivo} (usá PNG, JPG, SVG, PDF o .ai)`)
}

/** ¿La imagen declara su resolución? (MuPDF devuelve 72 cuando no la trae; Pillow no la da.) */
function tieneDpi(bytes, ext) {
  const u = bytes
  if (ext === 'png') {
    // chunk pHYs
    for (let i = 8; i + 8 < u.length && i < 4096;) {
      const len = (u[i] << 24) | (u[i + 1] << 16) | (u[i + 2] << 8) | u[i + 3]
      const t = String.fromCharCode(u[i + 4], u[i + 5], u[i + 6], u[i + 7])
      if (t === 'pHYs') return true
      if (t === 'IDAT') return false
      i += 12 + len
    }
    return false
  }
  // JPEG: JFIF con unidades (byte 13 del APP0 ≠ 0) o EXIF
  for (let i = 2; i + 4 < u.length && i < 65536;) {
    if (u[i] !== 0xFF) break
    const m = u[i + 1], len = (u[i + 2] << 8) | u[i + 3]
    if (m === 0xE0 && String.fromCharCode(u[i + 4], u[i + 5], u[i + 6], u[i + 7]) === 'JFIF') return u[i + 11] !== 0
    if (m === 0xE1) return true
    i += 2 + len
  }
  return false
}

/**
 * Dónde va el objeto en cada mesa del arte (lo que calculaba `objeto_agregado_colocar`): la mesa
 * del mapeo base y las de cada rango (`#talle`), con el objeto a su medida real dentro de cada una.
 * `fx/fy` = el punto tocado en fracciones de la PIEZA (y hacia abajo). Devuelve
 * `[[mesa, [x0, y0, x1, y1]], …]` en coordenadas de página (y hacia arriba).
 */
export function colocacionesObjeto(mupdf, arteBytes, { registro, mapeoBase, pieza, fx, fy, wCm, hCm }) {
  const talles = [...new Set(Object.values(registro || {}).flatMap((v) => Object.keys(v || {})))].sort((a, b) => (a < b ? -1 : a > b ? 1 : 0))
  const mesaTalles = new Map()
  let mv = {}
  try { mv = (mapeoVariantesArte(mupdf, arteBytes, registro, talles) || {})[pieza] || {} } catch { mv = {} }
  for (const [t, m] of Object.entries(mv)) {
    const k = Number(m)
    if (!mesaTalles.has(k)) mesaTalles.set(k, [])
    mesaTalles.get(k).push(t)
  }
  if (mapeoBase && mapeoBase[pieza]) {
    const mb = Number(mapeoBase[pieza])
    const sin = talles.filter((t) => !(t in mv))
    if (!mesaTalles.has(mb)) mesaTalles.set(mb, [])
    mesaTalles.get(mb).push(...(talles.length ? (sin.length ? sin : [talles[0]]) : []))
  }
  if (!mesaTalles.size) throw new Error('esa pieza no tiene mesa de arte asignada')
  const doc = new mupdf.PDFDocument(arteBytes)
  const out = [], errores = []
  try {
    for (const mesa of [...mesaTalles.keys()].sort((a, b) => a - b)) {
      try {
        const mr = rectPagina(doc, mesa - 1)
        if (!mr) continue
        const [ax0, ay0, aw, ah] = mr
        const porT = registro[pieza] || {}
        const tm = (mesaTalles.get(mesa) || []).find((t) => porT[t])
        const inf = (tm ? porT[tm] : Object.values(porT)[0]) || {}
        const phCm = Number(inf.h_cm || 0)
        if (!(phCm > 0)) continue
        const bw = wCm > 0 ? (wCm / ((aw / ah) * phCm)) * aw : aw * 0.3
        const bh = hCm > 0 ? (hCm / phCm) * ah : ah * 0.3
        const cx = ax0 + aw * 0.5 + (fx - 0.5) * aw
        const cyTop = ay0 + ah * fy
        const cy = (ay0 + ah) - cyTop + ay0
        out.push([mesa, [cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2]])
      } catch (e) { errores.push(`mesa ${mesa}: ${e.message || e}`) }
    }
  } finally { doc.destroy() }
  if (!out.length) throw new Error('No se pudo agregar al diseño. ' + (errores.join(' · ') || 'sin detalle'))
  return out
}

function nombreLibre(dict, prefijo) {
  const usados = new Set()
  if (!nulo(dict)) dict.forEach((_v, k) => usados.add(String(k)))
  let i = 0
  while (usados.has(prefijo + i)) i++
  return prefijo + i
}

/** Los recursos PROPIOS de la página (si los hereda del árbol, se copian a la página). */
function recursosPropios(doc, pageObj) {
  let res = pageObj.get('Resources')
  if (nulo(res)) {
    const her = pageObj.getInheritable('Resources')
    res = nulo(her) ? doc.newDictionary() : doc.graftObject(her)
    pageObj.put('Resources', res)
  }
  return res
}
function sub(doc, dict, clave) {
  let d = dict.get(clave)
  if (nulo(d)) { d = doc.newDictionary(); dict.put(clave, d) }
  return d
}

/**
 * `inyectar_editable`: el objeto (`objPdf`, su 1ª página) entra al arte como la capa OCG
 * «Editable <nombre>» (con sufijo si ya hay una igual) en cada mesa de `colocaciones`, en un
 * content stream PROPIO de cada mesa (`q /OC /OCn BDC … cm /OAn Do EMC Q`). Devuelve
 * `{bytes, capa, mesas}` con el arte nuevo.
 */
export function inyectarEditable(mupdf, arteBytes, colocaciones, objPdf, nombre) {
  const doc = new mupdf.PDFDocument(arteBytes)
  const src = new mupdf.PDFDocument(objPdf)
  try {
    const root = doc.getTrailer().get('Root')
    let ocp = root.get('OCProperties')
    const usados = new Set()
    if (!nulo(ocp) && !nulo(ocp.get('OCGs'))) {
      const og = ocp.get('OCGs')
      for (let i = 0; i < og.length; i++) { try { usados.add(og.get(i).get('Name').asString()) } catch { /* nada */ } }
    }
    let capa = `Editable ${nombre}`.trim()
    if (usados.has(capa)) { let i = 2; while (usados.has(`${capa} ${i}`)) i++; capa = `${capa} ${i}` }
    const d = doc.newDictionary()
    d.put('Type', doc.newName('OCG'))
    d.put('Name', doc.newString(capa))
    const intent = doc.newArray(); intent.push(doc.newName('View')); intent.push(doc.newName('Design'))
    d.put('Intent', intent)
    const ocg = doc.addObject(d)
    if (nulo(ocp)) {
      ocp = doc.newDictionary()
      ocp.put('OCGs', doc.newArray())
      const dd = doc.newDictionary(); dd.put('ON', doc.newArray()); dd.put('Order', doc.newArray())
      ocp.put('D', dd)
      root.put('OCProperties', ocp)
    }
    if (nulo(ocp.get('OCGs'))) ocp.put('OCGs', doc.newArray())
    ocp.get('OCGs').push(ocg)
    let dd = ocp.get('D')
    if (nulo(dd)) { dd = doc.newDictionary(); ocp.put('D', dd) }
    for (const k of ['ON', 'Order']) { if (nulo(dd.get(k))) dd.put(k, doc.newArray()); dd.get(k).push(ocg) }

    // el objeto como Form XObject (`as_form_xobject` + `copy_foreign`)
    const xo = formDePagina(doc, doc.newGraftMap(), src, 0)
    const bb = xo.get('BBox'), mt = xo.get('Matrix')
    const bx = [0, 1, 2, 3].map((i) => Number(bb.get(i).asNumber()))
    const M = !nulo(mt) && mt.isArray() && mt.length === 6 ? [0, 1, 2, 3, 4, 5].map((i) => Number(mt.get(i).asNumber())) : [1, 0, 0, 1, 0, 0]
    const xs = [], ys = []
    for (const [px, py] of [[bx[0], bx[1]], [bx[2], bx[1]], [bx[2], bx[3]], [bx[0], bx[3]]]) {
      xs.push(M[0] * px + M[2] * py + M[4]); ys.push(M[1] * px + M[3] * py + M[5])
    }
    const ox0 = Math.min(...xs), ox1 = Math.max(...xs), oy0 = Math.min(...ys), oy1 = Math.max(...ys)
    const hechas = []
    for (const [mesa, rect] of colocaciones) {
      const pageObj = doc.findPage(Number(mesa) - 1)
      const res = recursosPropios(doc, pageObj)
      const xod = sub(doc, res, 'XObject'), prd = sub(doc, res, 'Properties')
      const xn = nombreLibre(xod, 'OA'), pn = nombreLibre(prd, 'OC')
      xod.put(xn, xo); prd.put(pn, ocg)
      const [rx0, ry0, rx1, ry1] = rect.map(Number)
      const sx = ox1 !== ox0 ? (rx1 - rx0) / (ox1 - ox0) : 1.0
      const sy = oy1 !== oy0 ? (ry1 - ry0) / (oy1 - oy0) : 1.0
      const tx = rx0 - sx * ox0, ty = ry0 - sy * oy0
      const st = doc.addStream(`\nq /OC /${pn} BDC\n${fx6(sx)} 0 0 ${fx6(sy)} ${fx3(tx)} ${fx3(ty)} cm\n/${xn} Do\nEMC Q\n`, doc.newDictionary())
      const cont = pageObj.get('Contents')
      if (nulo(cont)) pageObj.put('Contents', st)
      else if (cont.isArray()) cont.push(st)
      else { const a = doc.newArray(); a.push(cont); a.push(st); pageObj.put('Contents', a) }
      hechas.push(Number(mesa))
    }
    if (!hechas.length) throw new Error('ninguna mesa válida para colocar el objeto')
    const bytes = doc.saveToBuffer('compress').asUint8Array().slice()
    return { bytes, capa, mesas: hechas }
  } finally {
    try { src.destroy() } catch { /* nada */ }
    try { doc.destroy() } catch { /* nada */ }
  }
}

/**
 * `quitar_editable`: saca del arte una capa que agregó el usuario (el OCG y SÓLO los content
 * streams que escribió `inyectarEditable`, que empiezan con `q /OC /<nombre> BDC`: los del arte
 * original nunca tienen esa forma). Devuelve `{bytes, borrados}`.
 */
export function quitarEditable(mupdf, arteBytes, capa) {
  const doc = new mupdf.PDFDocument(arteBytes)
  try {
    const ocp = doc.getTrailer().get('Root').get('OCProperties')
    if (nulo(ocp)) throw new Error('el arte no tiene capas')
    const og = ocp.get('OCGs')
    const ids = new Set()
    for (let i = 0; i < (nulo(og) ? 0 : og.length); i++) {
      const o = og.get(i)
      try { if (o.get('Name').asString() === capa && o.isIndirect()) ids.add(o.asIndirect()) } catch { /* nada */ }
    }
    if (!ids.size) throw new Error(`no existe la capa «${capa}» en el arte`)
    const esDeLaCapa = (o) => o && o.isIndirect && o.isIndirect() && ids.has(o.asIndirect())
    const filtrar = (arr) => {
      const a = doc.newArray()
      for (let i = 0; i < arr.length; i++) if (!esDeLaCapa(arr.get(i))) a.push(arr.get(i))
      return a
    }
    ocp.put('OCGs', filtrar(og))
    const dd = ocp.get('D')
    if (!nulo(dd)) for (const k of ['ON', 'OFF', 'Order']) { const x = dd.get(k); if (!nulo(x) && x.isArray()) dd.put(k, filtrar(x)) }
    let borrados = 0
    const dec = new TextDecoder('latin1')
    for (let p = 0; p < doc.countPages(); p++) {
      const pageObj = doc.findPage(p)
      const res = pageObj.get('Resources')
      const props = nulo(res) ? null : res.get('Properties')
      const nombres = []
      if (!nulo(props)) props.forEach((v, k) => { if (esDeLaCapa(v)) nombres.push(String(k)) })
      if (!nombres.length) continue
      const cont = pageObj.get('Contents')
      if (nulo(cont)) continue
      const streams = cont.isArray() ? Array.from({ length: cont.length }, (_, i) => cont.get(i)) : [cont]
      const quedan = []
      for (const st of streams) {
        let txt = ''
        try { txt = dec.decode(st.readStream().asUint8Array()) } catch { quedan.push(st); continue }
        if (nombres.some((n) => txt.includes(`/OC /${n} BDC`)) && txt.trim().startsWith('q /OC')) { borrados++; continue }
        quedan.push(st)
      }
      if (quedan.length === 1) pageObj.put('Contents', quedan[0])
      else { const a = doc.newArray(); for (const q of quedan) a.push(q); pageObj.put('Contents', a) }
      for (const n of nombres) { try { props.delete(n) } catch { /* nada */ } }
    }
    const bytes = doc.saveToBuffer('compress').asUint8Array().slice()
    return { bytes, borrados }
  } finally {
    try { doc.destroy() } catch { /* nada */ }
  }
}
