// LA BASE DE UNA PIEZA DEL CAMINO A (arte SEPARADO y arte CLÁSICO) — PLAN_NAVEGADOR.md, etapa 3.
//
// Traducción de los ramales de `motor_pedido._armar_base` que no son del camino B, con sus
// ayudantes: `pagina_arte_pieza` (la mesa del arte sin guías ni placeholders, `suprimir_capas` +
// `sanear_oc`), `pagina_arte_solo` (una capa «Editable …» aislada, recoloreada si hace falta),
// `mesa_arte` (#talle exacto > #rango > mapeo de la variable > base), `cm_encajar` /
// `cm_tamano_editable` / `_bbox_arte` (el diseño encajado en la pieza por la dimensión que
// manda), `_encaje` / `_pos_en_pieza` / `_centro_editable` / `_matriz_editable` (dónde cae cada
// editable), `_ops_cruz_proceso` (la cruz de 3 cm de TPU/Bordado/DTF), `_dibujar_objetos_agregados`
// (los PDF sueltos que el usuario agregó) y `_form_de` (`as_form_xobject` de qpdf). Los porqués
// están en el Python; acá se copian las cuentas y las cadenas (mismos `:.3f`/`:.6f`, mismo
// orden) para que `base_stream` y `clip` salgan letra por letra iguales, y el PDF de la pieza
// dibuje igual. El contrato es `verificar_navegador_pieza_a.py`.
//
// Uso: `const ctx = contextoCaminoA(mupdf, {...})` una vez por (arte, configuración) y después
// `ctx.armarBase({cont, pieza, talle, variante})` por cada (pieza, talle, variable); el documento
// de la pieza (para la vista previa o los contratos) sale de `documentoPiezaCaminoA(mupdf, base,
// estampado)`. Las mesas de origen que nombra `base.fuentesXo` (`{origen, pagina, doc}`) son las
// que la hoja comparte (`hoja/componer.js`, el sello).
import { instrucciones as parsear, escribir } from '../pdf/contenido.js'
import { recursosLigeros, sanearOc } from '../molde/paginas.js'
import { suprimirCapas, aislarCapa, recolorarCapa, aislarObjeto, aislarCapaObjetos,
  limpiarCapasConservandoTalle } from '../molde/capas.js'
import { MM, CM, opsCont, configBorde, componerBase } from './base.js'
import { normNombre } from './estampar.js'
import { pyFixed } from '../py.js'

// ─── capas del arte (motor_pedido) ───────────────────────────────────────────────────────────
export const CAPAS_NO_PERS = new Set(['diseño', 'diseno', 'personalizable', 'guias', 'guías', 'guides',
  'guia', 'guía', 'fondo', 'capa 1', 'referencia', '0'])
/** `_es_capa_guia`. */
export const esCapaGuia = (n) => ['guias', 'guia', 'guides'].includes(normNombre(n))
/** `_es_capa_editable`. */
export const esCapaEditable = (n) => normNombre(n).startsWith('editable')
/** `_nombre_editable`: quita el prefijo «editable» (con o sin separador). */
export function nombreEditable(capa) {
  const s = String(capa).trim()
  const m = /^\s*editable\b[\s\-_]*/i.exec(s)
  return (m ? s.slice(m[0].length).trim() : s) || 'Editable'
}

// ─── marcas de proceso ───────────────────────────────────────────────────────────────────────
export const MARCAS_PROCESO = {
  tpu: { letra: 'T', nombre: 'TPU' },
  bordado: { letra: 'B', nombre: 'Bordado' },
  dtf: { letra: 'D', nombre: 'DTF' },
}
export const CRUZ_MM = 30.0          // 3 cm de punta a punta
export const CRUZ_TRAZO_MM = 1.6
export const CRUZ_LETRA_MM = 7.0

/** `_ops_cruz_proceso`: la cruz de 3 cm + la letra del proceso, en negro puro. */
const esMarca = (m) => Object.prototype.hasOwnProperty.call(MARCAS_PROCESO, String(m || '').toLowerCase())

export function opsCruzProceso(cx, cy, marca, fuente = null) {
  const info = esMarca(marca) ? MARCAS_PROCESO[String(marca || '').toLowerCase()] : null
  if (!info) return ''
  const r = (CRUZ_MM * MM) / 2.0
  const w = CRUZ_TRAZO_MM * MM
  const ops = ['q', '0 0 0 1 K', `${pyFixed(w, 3)} w`, '0 J',
    `${pyFixed(cx - r, 3)} ${pyFixed(cy, 3)} m ${pyFixed(cx + r, 3)} ${pyFixed(cy, 3)} l S`,
    `${pyFixed(cx, 3)} ${pyFixed(cy - r, 3)} m ${pyFixed(cx, 3)} ${pyFixed(cy + r, 3)} l S`]
  if (fuente) {
    try {
      const size = fuente.sizeParaAlto(CRUZ_LETRA_MM * MM)
      let an = 0.0
      try { an = fuente.anchoTexto(info.letra, size) } catch { an = CRUZ_LETRA_MM * MM * 0.7 }
      const qx = cx + r / 2.0, qy = cy + r / 2.0
      ops.push('0 0 0 1 k')
      ops.push(fuente.opsTexto(info.letra, size, qx - an / 2.0, qy - (CRUZ_LETRA_MM * MM) / 2.0))
      ops.push('f')
    } catch { /* como el Python: la cruz sale sin letra */ }
  }
  ops.push('Q')
  return ops.join('\n') + '\n'
}

// ─── el encaje del diseño en la pieza ────────────────────────────────────────────────────────
/** `_manda_ancho`. */
export const mandaAncho = (referencia) => String(referencia).toLowerCase().startsWith('anch')

/** `_encaje`: `[awf, ahf, offx, offy]` en fracciones de la pieza. */
export function encaje(aw, ah, pw, ph, referencia = 'alto') {
  if (Math.min(aw, ah, pw, ph) <= 0) return [1.0, 1.0, 0.0, 0.0]
  if (mandaAncho(referencia)) {
    const ahf = (ah * (pw / aw)) / ph
    return [1.0, ahf, 0.0, (1 - ahf) / 2]
  }
  const awf = (aw * (ph / ah)) / pw
  return [awf, 1.0, (1 - awf) / 2, 0.0]
}

/** `_pos_en_pieza`: `{rx, ry, rw, rh, awf, ahf}` o null. */
export function posEnPieza(mesaRect, bboxMu, piezaBbox, referencia = 'alto') {
  try {
    const [ax0, ay0, aw, ah] = mesaRect.map(Number)
    const [ox0, oy0, ox1, oy1] = bboxMu.map(Number)
    const [px0, py0, px1, py1] = piezaBbox.map(Number)
    const pw = px1 - px0, ph = py1 - py0
    if (aw <= 0 || ah <= 0 || pw <= 0 || ph <= 0) return null
    const [awf, ahf, offx, offy] = encaje(aw, ah, pw, ph, referencia)
    return { rx: offx + ((ox0 - ax0) / aw) * awf, ry: offy + ((oy0 - ay0) / ah) * ahf,
      rw: ((ox1 - ox0) / aw) * awf, rh: ((oy1 - oy0) / ah) * ahf, awf, ahf }
  } catch { return null }
}

/** `pos_agregado_en_diseno`: la posición base de un objeto AGREGADO (centrado en el diseño). */
export function posAgregadoEnDiseno(obj, cont, mesaRect, referencia = 'alto') {
  try {
    const [, , aw, ah] = mesaRect.map(Number)
    const [px0, py0, px1, py1] = cont.bbox_mu.map(Number)
    const pw = px1 - px0, ph = py1 - py0
    const phCm = Number(cont.h) / CM
    const ow = Number(obj.w_cm || 0), oh = Number(obj.h_cm || 0)
    if (Math.min(aw, ah, pw, ph, phCm, ow, oh) <= 0) return null
    const [awf, ahf] = encaje(aw, ah, pw, ph, referencia)
    const pwCm = Number(cont.w) / CM
    const dAltoCm = ahf * phCm, dAnchoCm = awf * pwCm
    if (Math.min(dAltoCm, dAnchoCm) <= 0) return null
    const fw = ow / dAnchoCm, fh = oh / dAltoCm
    const rw = fw * awf, rh = fh * ahf
    return { rx: 0.5 - rw / 2, ry: 0.5 - rh / 2, rw, rh, awf, ahf }
  } catch { return null }
}

const num0 = (v) => Number(v || 0)

/** `_centro_editable`: el centro del objeto en coordenadas de página (pivote + desplazamiento). */
export function centroEditable(tf, obj, cont, W, H, B, posOverride = null, referencia = 'alto') {
  tf = tf || {}
  const pos = posOverride || posEnPieza(obj.mesa_rect, obj.bbox_mu, cont.bbox_mu, referencia)
  if (!pos) return null
  const Cx = B + (pos.rx + pos.rw / 2) * W
  const Cy = B + (1 - (pos.ry + pos.rh / 2)) * H
  const dx = num0(tf.dx), dy = num0(tf.dy)
  return [Cx + dx * (pos.awf ?? 1.0) * W, Cy - dy * (pos.ahf ?? 1.0) * H]
}

/** `_matriz_editable`: la `cm` del transform del usuario alrededor del centro; '' si es identidad. */
export function matrizEditable(tf, obj, cont, W, H, B, posOverride = null, referencia = 'alto') {
  tf = tf || {}
  const dx = num0(tf.dx), dy = num0(tf.dy)
  const rot = num0(tf.rot), sc = Number(tf.scale ?? 1) || 1
  const sx = tf.sx !== null && tf.sx !== undefined ? Number(tf.sx) : sc
  const sy = tf.sy !== null && tf.sy !== undefined ? Number(tf.sy) : sc
  if (Math.abs(dx) < 1e-6 && Math.abs(dy) < 1e-6 && Math.abs(rot) < 1e-6 && Math.abs(sx - 1) < 1e-6 && Math.abs(sy - 1) < 1e-6) return ''
  const pos = posOverride || posEnPieza(obj.mesa_rect, obj.bbox_mu, cont.bbox_mu, referencia)
  if (!pos) return ''
  const Cx = B + (pos.rx + pos.rw / 2) * W
  const Cy = B + (1 - (pos.ry + pos.rh / 2)) * H
  const r = -rot * (Math.PI / 180)                             // `math.radians(-rot)`
  const cs = Math.cos(r), sn = Math.sin(r)
  const a = sx * cs, b = sx * sn, c = -sy * sn, d = sy * cs
  const tdx = dx * (pos.awf ?? 1.0) * W, tdy = -dy * (pos.ahf ?? 1.0) * H
  const e = Cx + tdx - (a * Cx + c * Cy)
  const f = Cy + tdy - (b * Cx + d * Cy)
  return `${pyFixed(a, 6)} ${pyFixed(b, 6)} ${pyFixed(c, 6)} ${pyFixed(d, 6)} ${pyFixed(e, 3)} ${pyFixed(f, 3)} cm\n`
}

/** `_tf_identidad`. */
export function tfIdentidad(tf) {
  if (!tf) return true
  return Math.abs(num0(tf.dx)) < 1e-6 && Math.abs(num0(tf.dy)) < 1e-6 && Math.abs(num0(tf.rot)) < 1e-6 && Math.abs(Number(tf.scale ?? 1) - 1) < 1e-6
}

/** `_cfg_var`: la config de editables de ESTA fila (variable elegida, «*» legacy, o la única). */
export function cfgVar(mapa, variante) {
  if (!mapa || !Object.keys(mapa).length) return {}
  if (variante) return mapa[variante] || mapa['*'] || {}
  if (mapa['*'] && Object.keys(mapa['*']).length) return mapa['*']
  const cs = Object.keys(mapa).filter((k) => mapa[k] && Object.keys(mapa[k]).length)
  return cs.length === 1 ? (mapa[cs[0]] || {}) : {}
}

/** `_cmyk4`: 4 canales 0..1 o null. */
export function cmyk4(v) {
  try {
    if (!v || v.length < 4) return null
    const out = Array.from(v).map(Number).slice(0, 4)
    return out.some((x) => !Number.isFinite(x)) ? null : out
  } catch { return null }
}

// ─── mapeo ───────────────────────────────────────────────────────────────────────────────────
/**
 * Normaliza `mapeo_arte` como `generar_pedido`: plano `{pieza: mesa}` o por variable
 * `{mapeo, por_variable}`. Devuelve `{base: {pieza: mesa}, porVariable: {v: {pieza: mesa}}}`
 * (`base` vacío = no hay arte separado).
 */
export function normalizarMapeo(mapeoArte) {
  let base = {}, porVariable = {}
  if (!mapeoArte || !Object.keys(mapeoArte).length) return { base, porVariable }
  const esPorVariable = Object.values(mapeoArte).some((v) => v && typeof v === 'object' && !Array.isArray(v))
  if (!esPorVariable) {
    for (const [p, m] of Object.entries(mapeoArte)) base[p] = m
    return { base, porVariable }
  }
  for (const [c, mm] of Object.entries(mapeoArte.por_variable || {})) {
    const d = {}
    for (const [p, m] of Object.entries(mm || {})) if (m) d[p] = Math.trunc(Number(m))
    porVariable[String(c)] = d
  }
  for (const [p, m] of Object.entries(mapeoArte.mapeo || {})) if (m) base[p] = Math.trunc(Number(m))
  if (!Object.keys(base).length) {
    for (const mm of Object.values(porVariable)) for (const [p, m] of Object.entries(mm)) if (!(p in base)) base[p] = m
  }
  return { base, porVariable }
}

/** `mesa_arte`: #talle exacto > #rango (`mapeoVar = {pieza: {talle: mesa}}`) > mapeo de la variable > base. */
export function mesaArteDe({ base, porVariable }, mapeoVar, pieza, talle, variante = null) {
  const mp = (variante && porVariable[variante]) ? porVariable[variante] : (base || {})
  return ((mapeoVar || {})[pieza] || {})[talle] || mp[pieza] || null
}

// ─── objetos PDF (mupdf.js) ──────────────────────────────────────────────────────────────────
const nulo = (o) => !o || o.isNull()
/** `float(v)` de pikepdf: el texto del archivo → double. `asNumber()` pasa por float32 (2214.33 →
 *  2214.330078) y la escala del arte (`H / alto`) cambiaba en la 6ª cifra. `toString()` devuelve la
 *  escritura más corta que vuelve a ese float: para lo que escribe Illustrator, el texto original. */
export function numeroExacto(o) {
  if (o.isInteger()) return o.asNumber()
  const v = Number(o.toString())
  return Number.isFinite(v) ? v : o.asNumber()
}

function leerCaja(pageObj, clave, heredable) {
  const v = heredable ? pageObj.getInheritable(clave) : pageObj.get(clave)
  if (nulo(v) || !v.isArray() || v.length !== 4) return null
  const out = []
  for (let i = 0; i < 4; i++) out.push(numeroExacto(v.get(i)))
  return out
}

/** Los bytes del contenido de una página (los streams se unen con un salto de línea). */
export function contenidoDePagina(pageObj) {
  const cont = pageObj.get('Contents')
  if (nulo(cont)) return new Uint8Array(0)
  if (cont.isArray()) {
    const partes = []
    for (let i = 0; i < cont.length; i++) partes.push(cont.get(i).readStream().asUint8Array().slice())
    let n = 0
    for (const p of partes) n += p.length + 1
    const bytes = new Uint8Array(n)
    let k = 0
    for (const p of partes) { bytes.set(p, k); k += p.length; bytes[k++] = 10 }
    return bytes
  }
  return cont.readStream().asUint8Array().slice()
}

/**
 * Lo que `as_form_xobject()` de qpdf escribe para una página: `{caja, mtx}` — BBox = TrimBox →
 * CropBox → MediaBox; `/Matrix` sólo si hay `/Rotate` o `/UserUnit` (`getMatrixForTransformations`).
 */
export function infoFormPagina(pageObj) {
  const caja = leerCaja(pageObj, 'TrimBox', false) || leerCaja(pageObj, 'CropBox', true) || leerCaja(pageObj, 'MediaBox', true) || [0, 0, 612, 792]
  const rotO = pageObj.getInheritable('Rotate'), uuO = pageObj.get('UserUnit')
  const hayRot = !nulo(rotO), hayUU = !nulo(uuO)
  let mtx = null
  if (hayRot || hayUU) {
    const [llx, lly, urx, ury] = caja
    const width = urx - llx, height = ury - lly
    const scale = hayUU && uuO.isNumber() ? numeroExacto(uuO) : 1.0
    const rotate = hayRot && rotO.isNumber() ? Math.trunc(rotO.asNumber()) : 0
    switch (rotate) {
      case 90: mtx = [0, -scale, scale, 0, 0, width * scale]; break
      case 180: mtx = [-scale, 0, 0, -scale, width * scale, height * scale]; break
      case 270: mtx = [0, scale, -scale, 0, height * scale, 0]; break
      default: mtx = [scale, 0, 0, scale, 0, 0]
    }
  }
  return { caja, mtx }
}

/** `_bbox_arte` / `_bbox_de_xo`: `[x0, x1, y0, y1]` del BBox ya transformado por la Matrix. */
export function bboxForm({ caja, mtx }) {
  const bx = caja.map(Number)
  const [a, b, c, d, e, f] = mtx ? mtx.map(Number) : [1, 0, 0, 1, 0, 0]
  const xs = [], ys = []
  for (const [px, py] of [[bx[0], bx[1]], [bx[2], bx[1]], [bx[2], bx[3]], [bx[0], bx[3]]]) {
    xs.push(a * px + c * py + e); ys.push(b * px + d * py + f)
  }
  return [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)]
}

/** `as_form_xobject()` + `del xo["/OC"]`: la página `pagina` de `srcDoc` como Form XObject dentro de `out`. */
export function formDePagina(out, mapa, srcDoc, pagina) {
  const pageObj = srcDoc.findPage(pagina)
  const { caja, mtx } = infoFormPagina(pageObj)
  const dict = out.newDictionary()
  dict.put('Type', out.newName('XObject'))
  dict.put('Subtype', out.newName('Form'))
  const bbox = out.newArray()
  for (const v of caja) bbox.push(out.newReal(v))
  dict.put('BBox', bbox)
  if (mtx) {
    const arr = out.newArray()
    for (const v of mtx) arr.push(out.newReal(v))
    dict.put('Matrix', arr)
  }
  const res = pageObj.get('Resources')
  if (!nulo(res)) dict.put('Resources', mapa.graftObject(res))
  const grupo = pageObj.get('Group')
  if (!nulo(grupo)) dict.put('Group', mapa.graftObject(grupo))
  return out.addStream(contenidoDePagina(pageObj), dict)
}

/** `cm_encajar`: el diseño (BBox×Matrix `info`) escalado a la dimensión que manda y centrado en la otra. */
export function cmEncajar(info, W, H, B, referencia = 'alto') {
  const [tx0, tx1, ty0, ty1] = bboxForm(info)
  if (mandaAncho(referencia)) {
    const e = tx1 !== tx0 ? W / (tx1 - tx0) : 1.0
    const ah = (ty1 - ty0) * e
    return `${pyFixed(e, 6)} 0 0 ${pyFixed(e, 6)} ${pyFixed(B - e * tx0, 3)} ${pyFixed(B + (H - ah) / 2 - e * ty0, 3)} cm`
  }
  const e = ty1 !== ty0 ? H / (ty1 - ty0) : 1.0
  const aw = (tx1 - tx0) * e
  return `${pyFixed(e, 6)} 0 0 ${pyFixed(e, 6)} ${pyFixed(B + (W - aw) / 2 - e * tx0, 3)} ${pyFixed(B - e * ty0, 3)} cm`
}

/** `cm_tamano_editable`: el objeto a escala ABSOLUTA `sf`, donde caería escalado con el diseño. */
export function cmTamanoEditable(info, W, H, B, bboxMu, sf, referencia = 'alto') {
  const [tx0, tx1, ty0, ty1] = bboxForm(info)
  let s, cx0, cy0
  if (mandaAncho(referencia)) {
    s = tx1 !== tx0 ? W / (tx1 - tx0) : 1.0
    cx0 = B; cy0 = B + (H - (ty1 - ty0) * s) / 2
  } else {
    s = ty1 !== ty0 ? H / (ty1 - ty0) : 1.0
    cx0 = B + (W - (tx1 - tx0) * s) / 2; cy0 = B
  }
  const ox = (Number(bboxMu[0]) + Number(bboxMu[2])) / 2.0
  const oy = ty1 - (Number(bboxMu[1]) + Number(bboxMu[3])) / 2.0
  const ex = (s - sf) * ox + cx0 - s * tx0
  const ey = (s - sf) * oy + cy0 - s * ty0
  return `${pyFixed(sf, 6)} 0 0 ${pyFixed(sf, 6)} ${pyFixed(ex, 3)} ${pyFixed(ey, 3)} cm`
}

/** `doc.get_ocgs()`: los nombres de TODAS las capas (OCG) del documento. */
export function capasDelDocumento(doc) {
  const out = new Set()
  try {
    const ocp = doc.getTrailer().get('Root').get('OCProperties')
    if (nulo(ocp)) return out
    const ocgs = ocp.get('OCGs')
    if (nulo(ocgs) || !ocgs.isArray()) return out
    for (let i = 0; i < ocgs.length; i++) {
      try {
        const nm = ocgs.get(i).get('Name')
        if (!nulo(nm)) out.add(nm.asString())
      } catch { /* una entrada rota no tumba el resto */ }
    }
  } catch { /* sin capas */ }
  return out
}

/** `fitz.Page.rect` como `[x0, y0, ancho, alto]` (`arte_rect` / `mesa_rect_arte`). */
export function rectPagina(doc, pagina) {
  const page = doc.loadPage(pagina)
  try {
    const [x0, y0, x1, y1] = page.getBounds()
    return [x0, y0, x1 - x0, y1 - y0]
  } finally { page.destroy() }
}

/** `_bbox_xobject`: `{bbox, matrix}` de un Form XObject de la página, por nombre (`/Fm0`). */
function resolutorXObjects(pageObj) {
  return (nombre) => {
    try {
      const res = pageObj.get('Resources')
      if (nulo(res)) return null
      const xos = res.get('XObject')
      if (nulo(xos)) return null
      const xo = xos.get(String(nombre).replace(/^\//, ''))
      if (nulo(xo)) return null
      const bb = xo.get('BBox')
      if (nulo(bb) || !bb.isArray()) return null
      const bbox = []
      for (let i = 0; i < 4; i++) bbox.push(numeroExacto(bb.get(i)))
      const m = xo.get('Matrix')
      let matrix = null
      if (!nulo(m) && m.isArray() && m.length === 6) { matrix = []; for (let i = 0; i < 6; i++) matrix.push(numeroExacto(m.get(i))) }
      return { bbox, matrix }
    } catch { return null }
  }
}

/** Reescribe el contenido de una página con las instrucciones dadas (`page.Contents = pdf.make_stream(...)`). */
export function reescribirPagina(doc, pageObj, inst) {
  pageObj.put('Contents', doc.addStream(escribir(inst), doc.newDictionary()))
}

/** Las instrucciones y los recursos ligeros de una página. */
export function leerPagina(pageObj) {
  const inst = [...parsear(contenidoDePagina(pageObj))]
  const R = recursosLigeros(pageObj.get('Resources'))
  return { inst, R }
}

function hayImagenes(res, vistos = new Set(), prof = 0) {
  // `page.get_images()`: las imágenes de los recursos de la página y de los Form XObjects anidados
  try {
    if (nulo(res) || prof > 8) return false
    const xos = res.get('XObject')
    if (nulo(xos)) return false
    const claves = []
    xos.resolve().forEach((v, k) => claves.push([String(k), v]))
    for (const [, x] of claves) {
      const clave = x.isIndirect() ? x.asIndirect() : null
      if (clave !== null) { if (vistos.has(clave)) continue; vistos.add(clave) }
      const obj = x.resolve()
      const st = obj.get('Subtype')
      const s = nulo(st) || !st.isName() ? '' : st.asName()
      if (s === 'Image') return true
      if (s === 'Form' && hayImagenes(obj.get('Resources'), vistos, prof + 1)) return true
    }
  } catch { /* como el Python: sin imágenes */ }
  return false
}

/**
 * `_pg.get_drawings() or _pg.get_images() or _pg.get_text().strip()`: ¿la página dibuja algo?
 * (la garantía anti-desaparición de los editables).
 */
export function tieneContenidoReal(mupdf, doc, pagina) {
  const page = doc.loadPage(pagina)
  let dibujos = 0, texto = 0
  try {
    const nada = () => {}
    const dev = new mupdf.Device({
      fillPath() { dibujos++ }, strokePath() { dibujos++ },
      fillText() { texto++ }, strokeText() { texto++ }, clipText() { texto++ }, clipStrokeText() { texto++ }, ignoreText() { texto++ },
      clipPath: nada, clipStrokePath: nada, fillShade: nada, fillImage: nada, fillImageMask: nada, clipImageMask: nada,
      popClip: nada, beginMask: nada, endMask: nada, beginGroup: nada, endGroup: nada, beginTile() { return 0 }, endTile: nada,
      beginLayer: nada, endLayer: nada, beginStructure: nada, endStructure: nada, beginMetatext: nada, endMetatext: nada,
      renderFlags: nada, setDefaultColorSpaces: nada, close: nada,
    })
    try { page.run(dev, mupdf.Matrix.identity) } finally { try { dev.close() } catch { /* nada */ } }
    if (dibujos || texto) return true
    return hayImagenes(doc.findPage(pagina).get('Resources'))
  } catch { return false } finally { page.destroy() }
}

// ─── el contexto: un arte + su configuración ────────────────────────────────────────────────
// `_ident`: nombre de capa + id de figura. 🔴 El separador es el carácter de control U+001F
// (`_EDIT_SEP` del servidor): en el editor del Python se ve como una cadena vacía, pero no lo es;
// y como Python lo cuenta como ESPACIO, `_norm_nombre` lo vuelve un espacio («escudo 11018b89»).
export const SEP = '\x1f'
const ident = (nombre, objId) => (objId ? `${nombre}${SEP}${objId}` : nombre)

/**
 * `contextoCaminoA(mupdf, opciones)` — lo que `generar_pedido` prepara UNA vez para el arte:
 *   · `arte`            — los bytes del arte (.ai) o un `PDFDocument` (se abre una copia por uso);
 *   · `mapeoArte`       — `{pieza: mesa}` o `{mapeo, por_variable}`; `mapeoVar` — `{pieza: {talle: mesa}}`
 *                         de `mapeo_variantes_arte` (#talle / #rango);
 *   · `editables`       — lo que devuelve `extraer_editables(arte, con_thumb=False)`;
 *   · `editablesCfg`, `editablesTamano`, `editablesColor`, `editablesMarca`, `editablesSinMarca`,
 *     `marcasComoCruz` (default true), `referencia` ('alto' | 'ancho'), `borde` (borde de corte);
 *   · `objetosAgregados` — `{objetos: [{id, archivo, pieza, w_cm, h_cm, transforms}], abrir(archivo)}`
 *                          (`abrir` devuelve los bytes o el `PDFDocument` del PDF suelto);
 *   · `fuente(nombrePs)` — el abridor de tipografías (la cruz lleva la letra en Arial-BoldMT);
 *   · `capasMolde`, `geomsBase(mesa, talle)` — sólo para el arte CLÁSICO (ver `armarBaseClasico`).
 */
export function contextoCaminoA(mupdf, opciones) {
  const {
    arte, mapeoArte = null, mapeoVar = {}, editables = [], editablesCfg = null, editablesTamano = null,
    editablesColor = null, editablesMarca = null, editablesSinMarca = null, marcasComoCruz = true,
    referencia = 'alto', borde = null, objetosAgregados = null, fuente = null, capasMolde = null, geomsBase = null,
  } = opciones
  const bc = configBorde(borde)
  const B = bc.B
  // el arte se guarda como BYTES una vez: cada uso (limpio, aislado por capa, crudo) abre su copia,
  // como `_abrir_pike(arte)` abre el archivo de nuevo en el Python
  const arteBytes = arte instanceof Uint8Array ? arte : arte instanceof ArrayBuffer ? new Uint8Array(arte)
    : arte.saveToBuffer('').asUint8Array().slice()
  const abiertos = []
  const nuevoArte = () => { const d = new mupdf.PDFDocument(arteBytes); abiertos.push(d); return d }
  let arteCrudo = null                                   // el archivo tal cual (capas, `arte_rect`)
  const arteTalCual = () => { if (arteCrudo === null) arteCrudo = nuevoArte(); return arteCrudo }
  const mapeo = normalizarMapeo(mapeoArte)
  const separado = Object.keys(mapeo.base).length > 0
  const capasArte = separado ? capasDelDocumento(arteTalCual()) : new Set()   // `CAPAS_ARTE`

  // ── editables: qué se saca del diseño base y se redibuja aparte ──
  const editadosNombres = new Set()
  for (const objs of Object.values(editablesCfg || {})) {
    for (const [nom, porTalle] of Object.entries(objs || {})) {
      if (porTalle && typeof porTalle === 'object' && Object.values(porTalle).some((t) => !tfIdentidad(t))) editadosNombres.add(normNombre(nom))
    }
  }
  const tamano = {}
  for (const [n, porVar] of Object.entries(editablesTamano || {})) {
    const pv = {}
    for (const [v, box] of Object.entries(porVar || {})) if (box) pv[String(v)] = box
    if (Object.keys(pv).length) tamano[normNombre(n)] = pv
  }
  const tamanoNombres = new Set(Object.keys(tamano))
  const ecolor = editablesColor || {}
  const colorDe = (nombre, variante) => {
    const c = cfgVar(ecolor, variante)[nombre] || {}
    const f = cmyk4(c.fill), s = cmyk4(c.stroke)
    return (f || s) ? [f, s] : null
  }
  const coloreadosNombres = new Set()
  for (const objs of Object.values(ecolor)) {
    for (const [nom, c] of Object.entries(objs || {})) {
      const cc = c || {}
      if (cmyk4(cc.fill) || cmyk4(cc.stroke)) coloreadosNombres.add(normNombre(nom))
    }
  }
  const emarca = editablesMarca || {}
  const marcaDe = (nombre, variante) => cfgVar(emarca, variante)[nombre] || null
  const esinmarca = editablesSinMarca || {}
  const sinMarcaDe = (nombre, variante) => !!cfgVar(esinmarca, variante)[nombre]
  const marcadosNombres = new Set()
  for (const objs of Object.values(emarca)) {
    for (const [nom, mk] of Object.entries(objs || {})) if (esMarca(mk)) marcadosNombres.add(normNombre(nom))
  }
  for (const objs of Object.values(esinmarca)) {
    for (const [nom, sm] of Object.entries(objs || {})) if (sm) marcadosNombres.add(normNombre(nom))
  }
  const esRedibujado = (u) => {
    const nm = normNombre(u.ident), lay = normNombre(nombreEditable(u.capa))
    if (editadosNombres.has(nm) || coloreadosNombres.has(nm) || tamanoNombres.has(nm) || tamanoNombres.has(lay) || marcadosNombres.has(nm)) return true
    return (u.objetos || []).some((o) => coloreadosNombres.has(normNombre(o.ident)))
  }
  const coloresDe = (u, variante) => {
    const subs = u.objetos || []
    if (!subs.some((o) => colorDe(o.ident, variante))) return null
    const lay = colorDe(u.ident, variante)
    const out = {}
    for (const o of subs) {
      const c = colorDe(o.ident, variante) || lay
      if (c) out[o.obj_id] = c
    }
    return Object.keys(out).length ? out : null
  }

  // ── `pagina_arte_solo`: una capa aislada (y recoloreada) en una copia del arte ──
  const arteSolo = new Map()
  const paginaArteSolo = (mesa, capa, { color = null, objId = null, colores = null } = {}) => {
    let ck = null
    if (color) { ck = [color[0] ? color[0].slice(0, 4) : null, color[1] ? color[1].slice(0, 4) : null]; if (!ck[0] && !ck[1]) ck = null }
    const ckoList = Object.entries(colores || {})
      .filter(([, v]) => v && (v[0] !== null && v[0] !== undefined || v[1] !== null && v[1] !== undefined))
      .map(([k, v]) => [k, v[0] ? v[0].slice(0, 4) : null, v[1] ? v[1].slice(0, 4) : null])
      .sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))
    const cko = ckoList.length ? ckoList : null
    const key = `${mesa}|${normNombre(capa)}|${objId || ''}|${JSON.stringify(ck)}|${JSON.stringify(cko)}`
    let d = arteSolo.get(key)
    if (!d) {
      d = nuevoArte()
      const pageObj = d.findPage(mesa - 1)
      let { inst, R } = leerPagina(pageObj)
      const xi = resolutorXObjects(pageObj)
      if (cko) {
        const cols = {}
        for (const [k, f, s] of cko) cols[k] = [f, s]
        inst = aislarCapaObjetos(inst, R, normNombre(capa), cols, xi)
      } else if (objId) {
        inst = aislarObjeto(inst, R, normNombre(capa), objId, ck ? ck[0] : null, ck ? ck[1] : null, xi)
      } else {
        // COLOR OVERRIDE: recolorar ANTES de aislar (el aislado borra los marcadores que el recolor necesita)
        if (ck !== null) inst = recolorarCapa(inst, R, normNombre(capa), ck[0], ck[1])
        inst = aislarCapa(inst, R, normNombre(capa))
      }
      reescribirPagina(d, pageObj, inst)
      sanearOc(pageObj, new Set())
      arteSolo.set(key, d)
    }
    return { doc: d, key }
  }

  // ── `_edit_por_mesa` + la validación del aislamiento (`_redibujar_validos`) ──
  const editPorMesa = new Map()
  const redibujarValidos = new Set()
  if (separado && editablesCfg !== null && editablesCfg !== undefined) {
    for (const o of editables || []) {
      if (!editPorMesa.has(o.mesa)) editPorMesa.set(o.mesa, [])
      editPorMesa.get(o.mesa).push({
        capa: o.capa, nombre: o.nombre, obj_id: null, ident: o.nombre, mesa: o.mesa,
        bbox_mu: o.bbox_mu, mesa_rect: o.mesa_rect, w_cm: o.w_cm, h_cm: o.h_cm,
        objetos: (o.objetos || []).map((ob) => ({ obj_id: ob.obj_id, ident: ident(o.nombre, ob.obj_id) })),
      })
    }
    for (const [mesa, units] of editPorMesa) {
      for (const u of units) {
        const id = normNombre(u.ident)
        if (!esRedibujado(u) || redibujarValidos.has(id)) continue
        try {
          const { doc } = paginaArteSolo(mesa, u.capa, { objId: u.obj_id })
          if (tieneContenidoReal(mupdf, doc, mesa - 1)) redibujarValidos.add(id)
        } catch { /* como el Python: queda en el diseño base */ }
      }
    }
  }

  // ── `pagina_arte_pieza`: la mesa del arte con SOLO el diseño ──
  let arteLimpio = null
  const limpias = new Set()
  const paginaArtePieza = (mesa) => {
    if (arteLimpio === null) arteLimpio = nuevoArte()
    if (!limpias.has(mesa)) {
      const pageObj = arteLimpio.findPage(mesa - 1)
      let quitar = new Set()
      for (const c of capasArte) {
        if (esCapaGuia(c) || c === 'Personalizable' || !CAPAS_NO_PERS.has(normNombre(c))) quitar.add(c)
      }
      quitar = new Set([...quitar].filter((c) => !(esCapaEditable(c) && !redibujarValidos.has(normNombre(nombreEditable(c))))))
      const { inst, R } = leerPagina(pageObj)
      reescribirPagina(arteLimpio, pageObj, suprimirCapas(inst, R, quitar))
      sanearOc(pageObj, new Set())
      limpias.add(mesa)
    }
    return arteLimpio
  }

  // ── `pagina_arte`: el arte CLÁSICO (la misma mesa del molde, sólo la capa del talle) ──
  const artePorTalle = new Map(), limpiasClasico = new Set()
  const paginaArteClasico = (mesa, talle) => {
    if (!artePorTalle.has(talle)) artePorTalle.set(talle, nuevoArte())
    const d = artePorTalle.get(talle)
    const k = `${talle}|${mesa}`
    if (!limpiasClasico.has(k)) {
      const pageObj = d.findPage(mesa - 1)
      const capas = new Set([...(capasMolde || [])].filter((c) => c !== 'Fondo' && c !== talle))
      capas.add('Personalizable')
      const { inst, R } = leerPagina(pageObj)
      const geoms = geomsBase ? (geomsBase(mesa, talle) || []) : []
      reescribirPagina(d, pageObj, limpiarCapasConservandoTalle(inst, R, capas, talle, geoms))
      sanearOc(pageObj, new Set())
      limpiasClasico.add(k)
    }
    return d
  }

  const rects = new Map()
  const arteRect = (mesa) => {
    if (!rects.has(mesa)) rects.set(mesa, rectPagina(arteTalCual(), mesa - 1))
    return rects.get(mesa)
  }

  // objetos agregados: los PDF sueltos, abiertos una vez
  const oaDocs = new Map()
  const oaDoc = (archivo) => {
    let d = oaDocs.get(archivo)
    if (!d) {
      const src = objetosAgregados.abrir(archivo)
      d = (src instanceof Uint8Array || src instanceof ArrayBuffer) ? new mupdf.PDFDocument(src) : src
      if (d !== src) abiertos.push(d)
      oaDocs.set(archivo, d)
    }
    return d
  }

  const mesaArte = (pieza, talle, variante = null) => (separado ? mesaArteDe(mapeo, mapeoVar, pieza, talle, variante) : null)

  /** `_dibujar_objetos_agregados`. */
  const dibujarObjetosAgregados = (pieza, variante, talle, cont, W, H, clip, mesaRect, fuentesXo, nombres) => {
    const oa = objetosAgregados
    if (!oa || !oa.objetos || !oa.objetos.length) return ''
    let draw = ''
    for (const o of oa.objetos) {
      if ((o.pieza || '') !== pieza) continue
      const trs = o.transforms || {}
      const pv = trs[variante === null || variante === undefined ? 'None' : String(variante)] || trs['*'] || {}
      let tf = pv[String(talle)]
      if (!tf) tf = Object.values(pv).find((v) => v) || {}
      try {
        const d = oaDoc(o.archivo)
        const info = infoFormPagina(d.findPage(0))
        const nom = `/OA${nombres.oa++}`
        fuentesXo.push([nom, { origen: `oa|${o.archivo}`, pagina: 0, doc: d }])
        const pos = posAgregadoEnDiseno(o, cont, mesaRect, referencia)
        if (!pos) continue
        const [tx0, tx1, ty0, ty1] = bboxForm(info)
        const sxb = tx1 !== tx0 ? (pos.rw * W) / (tx1 - tx0) : 1.0
        const syb = ty1 !== ty0 ? (pos.rh * H) / (ty1 - ty0) : 1.0
        const cxo = (tx0 + tx1) / 2.0, cyo = (ty0 + ty1) / 2.0
        const cx = B + (pos.rx + pos.rw / 2) * W
        const cy = B + (1 - (pos.ry + pos.rh / 2)) * H
        const ex = cx - sxb * cxo, ey = cy - syb * cyo
        const base = `${pyFixed(sxb, 6)} 0 0 ${pyFixed(syb, 6)} ${pyFixed(ex, 3)} ${pyFixed(ey, 3)} cm\n`
        const utf = matrizEditable(tf, null, cont, W, H, B, pos, referencia)
        draw += `q\n${clip}\nW n\n${utf}${base}\n${nom} Do\nQ\n`
      } catch { /* como el Python: ese objeto no se dibuja */ }
    }
    return draw
  }

  /**
   * `_armar_base` (ramales del arte separado). Devuelve `{baseStream, clip, W, H, Hp, x0, y0, x0m,
   * y0m, S, B, mesaA, fuentesXo, cont, pieza, talle, variante, delMolde: false}`.
   */
  const armarBase = ({ cont, pieza, talle, variante = null }) => {
    const mesaA = mesaArte(pieza, talle, variante)
    const [x0, y0] = cont.bbox_raw
    const W = cont.w, H = cont.h
    const [x0m, y0m] = cont.bbox_mu
    const Hp = H + 2 * B
    const fuentesXo = []
    const nombres = { e: 0, oa: 0 }
    const S = cont.user_unit
    const clip = opsCont(cont, S, B - x0 * S, B - y0 * S)
    let arteDraw = ''                                     // pieza sin arte: queda vacío (el aviso lo da el servidor)
    if (separado && mesaA) {
      const dArte = paginaArtePieza(mesaA)
      const info = infoFormPagina(dArte.findPage(mesaA - 1))
      const nom = '/A0'
      fuentesXo.push([nom, { origen: `arte|${mesaA}`, pagina: mesaA - 1, doc: dArte }])
      const td = cmEncajar(info, W, H, B, referencia)
      arteDraw = `q\n${clip}\nW n\n${td}\n${nom} Do\nQ\n`
      const editObj = (editPorMesa.get(mesaA) || []).filter((u) => redibujarValidos.has(normNombre(u.ident)))
      for (const o of editObj) {
        const tf = ((cfgVar(editablesCfg || {}, variante)[o.ident]) || {})[String(talle)] || {}
        const mk = marcaDe(o.ident, variante)
        const sin = sinMarcaDe(o.ident, variante)
        if ((mk || sin) && marcasComoCruz) {
          const c = (mk && !sin) ? centroEditable(tf, o, cont, W, H, B, null, referencia) : null
          if (c) {
            let fcruz
            try { fcruz = fuente ? fuente('Arial-BoldMT') : null } catch { fcruz = null }
            arteDraw += `q\n${clip}\nW n\n` + opsCruzProceso(c[0], c[1], mk, fcruz) + 'Q\n'
          }
          continue
        }
        const utf = matrizEditable(tf, o, cont, W, H, B, null, referencia)
        const box = (tamano[normNombre(o.ident)] || {})[String(talle)] || (tamano[normNombre(nombreEditable(o.capa))] || {})[String(talle)]
        try {
          const cols = coloresDe(o, variante)
          const { doc: ps, key } = paginaArteSolo(mesaA, o.capa, { objId: o.obj_id, color: cols ? null : colorDe(o.ident, variante), colores: cols })
          const infoE = infoFormPagina(ps.findPage(mesaA - 1))
          const noms = `/E${nombres.e++}`
          fuentesXo.push([noms, { origen: `editable|${key}`, pagina: mesaA - 1, doc: ps }])
          const wCm = Number(o.w_cm || 0), hCm = Number(o.h_cm || 0)
          let sf
          if (box && box.mantener) sf = 1.0
          else if (box && wCm > 0 && hCm > 0) {
            const b = (wCm >= hCm ? box.apaisado : box.vertical) || []
            const aw = b.length > 0 ? Number(b[0]) : 0
            const ah = b.length > 1 ? Number(b[1]) : 0
            const r = [aw > 0 ? aw / wCm : null, ah > 0 ? ah / hCm : null].filter((x) => x)
            sf = r.length ? Math.min(...r) : null
          } else sf = null
          const tds = sf ? cmTamanoEditable(infoE, W, H, B, o.bbox_mu, sf, referencia) : cmEncajar(infoE, W, H, B, referencia)
          arteDraw += `q\n${clip}\nW n\n${utf}${tds}\n${noms} Do\nQ\n`
        } catch { /* como el Python: el objeto queda sin redibujar */ }
      }
      arteDraw += dibujarObjetosAgregados(pieza, variante, talle, cont, W, H, clip, arteRect(mesaA), fuentesXo, nombres)
    } else if (!separado) {
      throw new Error('sin mapeo del arte no hay arte separado: usá armarBaseClasico')
    }
    const baseStream = componerBase(bc, cont, S, clip, W, H, arteDraw)
    return { baseStream, clip, W, H, Hp, x0, y0, x0m, y0m, S, B, mesaA, fuentesXo, cont, pieza, talle, variante,
      nom: '/A0', bcActivo: bc.bcActivo, bcColor: bc.bcColor, bcAlin: bc.bcAlin, delMolde: false,
      arteRect: mesaA ? arteRect(mesaA) : null }
  }

  /**
   * `_armar_base`, ramal del ARTE CLÁSICO: el diseño está sobre la MISMA mesa del molde (sin
   * mapeo). Necesita `capasMolde` (las capas del molde, `TODAS`) y `geomsBase(mesa, talle)` (los
   * bboxes en crudas de la moldería base, `geometrias_base`). Sin contrato todavía: no hay un arte
   * clásico entre los archivos de referencia.
   */
  const armarBaseClasico = ({ cont, mesa, talle, pieza = null, variante = null }) => {
    const [x0, y0] = cont.bbox_raw
    const W = cont.w, H = cont.h
    const [x0m, y0m] = cont.bbox_mu
    const Hp = H + 2 * B
    const d = paginaArteClasico(mesa, talle)
    const info = infoFormPagina(d.findPage(mesa - 1))
    const S = info.mtx ? Number(info.mtx[0]) : 1.0
    const ops = opsCont(cont, S)
    const clip = opsCont(cont, S, B - x0 * S, B - y0 * S)
    const nom = '/A0'
    const fuentesXo = [[nom, { origen: `arte_clasico|${mesa}|${talle}`, pagina: mesa - 1, doc: d }]]
    const arteDraw = `q\n1 0 0 1 ${pyFixed(B - x0 * S, 3)} ${pyFixed(B - y0 * S, 3)} cm\n` +
                     `q\n${ops}\nW n\n${nom} Do\nQ\nQ\n`
    const baseStream = componerBase(bc, cont, S, clip, W, H, arteDraw)
    return { baseStream, clip, W, H, Hp, x0, y0, x0m, y0m, S, B, mesaA: null, fuentesXo, cont, pieza, talle, variante,
      nom, bcActivo: bc.bcActivo, bcColor: bc.bcColor, bcAlin: bc.bcAlin, delMolde: false, arteRect: null }
  }

  const cerrar = () => {
    for (const d of abiertos) { try { d.destroy() } catch { /* nada */ } }
    abiertos.length = 0
  }

  return { separado, mapeo, B, bc, referencia, mesaArte, armarBase, armarBaseClasico, arteRect, redibujarValidos, cerrar }
}

/**
 * El PDF de una pieza del camino A: una página de `(W+2B) × (H+2B)` con los XObjects que nombra
 * `base.fuentesXo` (el arte limpio como `/A0`, los editables `/E…`, los objetos agregados `/OA…`)
 * y el contenido `baseStream + estampado`. Devuelve los bytes.
 */
export function documentoPiezaCaminoA(mupdf, base, estampado = '') {
  const out = new mupdf.PDFDocument()
  const mapas = new Map()
  const res = out.newDictionary()
  const xos = out.newDictionary()
  for (const [nom, ref] of base.fuentesXo || []) {
    let mapa = mapas.get(ref.doc)
    if (!mapa) { mapa = out.newGraftMap(); mapas.set(ref.doc, mapa) }
    xos.put(nom.slice(1), formDePagina(out, mapa, ref.doc, ref.pagina))
  }
  res.put('XObject', xos)
  const contenido = new TextEncoder().encode(base.baseStream + estampado)
  const page = out.addPage([0, 0, base.W + 2 * base.B, base.H + 2 * base.B], 0, res, contenido)
  out.insertPage(out.countPages(), page)
  const bytes = out.saveToBuffer('compress').asUint8Array().slice()
  for (const m of mapas.values()) { try { m.destroy() } catch { /* nada */ } }
  try { out.destroy() } catch { /* nada */ }
  return bytes
}
