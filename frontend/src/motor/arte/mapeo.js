// EL MAPEO DEL ARTE SEPARADO A LAS PIEZAS, LA DETECCIÓN Y LA VALIDACIÓN — PLAN_NAVEGADOR.md,
// etapa 3, camino A. Traducción de `motor_pedido.mapeo_por_nombre`, `mapeo_variantes_arte`
// (`_variantes_token`, `_parse_pieza_hash`), `_texto_mesa`, `_capas_mesa`, `_match_pieza(s)`,
// `arte_es_separado`, `detectar_arte`, `fuentes_requeridas_arte`, `validar_arte_separado` y
// `validar_arte`. Los textos de cada «check» son los mismos, letra por letra: la pantalla los
// muestra tal cual.
//
// Donde Python recorre un `set` (el orden es arbitrario y cambia entre corridas) acá se recorre
// en orden de aparición: `_capas_mesa` (`list(set(capas))`), las tintas de `_separaciones` y el
// desempate de `min(libres, key=_dist)` en `detectar_arte`. El contrato lo tiene en cuenta.
import { pyRound, pyStrip } from '../py.js'
import { dibujosDePagina } from '../pdf/dibujos.js'
import { resolverFuente } from '../texto/fuentes.js'
import { abrir, capasUi, configurarCapa, nombresOcgs, normNombre, normGenerico, textoDict, esDigitoPy, esLetraPy,
         ordenarPy, masLargaPy, splitPy, reprPy, textoPikepdf, mesaTieneDiseno, pixmapMesa, desvioMedio, base64De, WS_PY } from './texto.js'
import { extraerPersonalizacion, esCapaEditable, CAPAS_GRAFICAS } from './personalizacion.js'

export const CM = 28.3465
import { CAPAS_SISTEMA, esCapaGuia } from '../nombres.js'
export { CAPAS_SISTEMA, esCapaGuia }
const STOP_ROTULO = new Set(['diseno', 'guia', 'guias', 'numero', 'nombre', 'palabra', 'personalizable', 'editable', 'texto'])
const RX_PREFIJO_HASH = new RegExp('^[' + WS_PY + ']*#[^' + WS_PY + ']+[' + WS_PY + ']+', 'u')
const RX_RANGO = new RegExp('^[' + WS_PY + ']*#([^' + WS_PY + ']+)', 'u')

/** `_texto_mesa(doc, mesa)`: las líneas de texto (no vacías) de la mesa, en orden. */
export function textoMesa(page) {
  const lineas = []
  for (const b of textoDict(page)) {
    for (const l of b.lines) {
      const t = pyStrip(l.spans.map((s) => s.text).join(''))
      if (t) lineas.push(t)
    }
  }
  return lineas
}

/** `_capas_mesa(doc, mesa)`: las capas con dibujos (`get_drawings`), sin repetir. */
export function capasMesa(mupdf, page) {
  const capas = []
  const vistas = new Set()
  try {
    for (const d of dibujosDePagina(mupdf, page, { ligero: true })) {
      if (d.type !== 'f' && d.type !== 's' && d.type !== 'fs') continue
      const ly = d.layer
      if (ly && !vistas.has(ly)) { vistas.add(ly); capas.push(ly) }
    }
  } catch { /* como el except de Python */ }
  return capas
}

/** `_match_pieza`: la pieza que nombra alguna línea (exacta; si no, por genérico). */
export function matchPieza(lineas, piezas) {
  const objetivos = new Map()
  for (const p of piezas) objetivos.set(normNombre(p), p)
  for (const t of lineas) { const k = normNombre(t); if (objetivos.has(k)) return objetivos.get(k) }
  const porgen = porGenerico(piezas)
  for (const t of lineas) {
    const g = normGenerico(t)
    if (g && porgen.has(g)) return porgen.get(g)[0]
  }
  return null
}

function porGenerico(piezas) {
  const porgen = new Map()
  for (const p of piezas) {
    const g = normGenerico(p)
    if (!porgen.has(g)) porgen.set(g, [])
    porgen.get(g).push(p)
  }
  return porgen
}

/** `_match_piezas`: las piezas del genérico que nombra la PRIMERA línea que matchea. */
export function matchPiezas(lineas, piezas) {
  const porgen = porGenerico(piezas)
  for (const t of lineas) {
    const g = normGenerico(t)
    if (g && porgen.has(g)) return [porgen.get(g), false]
  }
  return [[], false]
}

/** `mapeo_por_nombre(path_arte, registro_molde)`: {pieza: mesa}. */
export function mapeoPorNombre(mupdf, bytes, registro) {
  const doc = abrir(mupdf, bytes)
  const mapeo = new Map()
  try {
    const piezas = ordenarPy(Object.keys(registro))
    const exactos = new Set()
    const huerfanas = []
    const n = doc.countPages()
    for (let i = 0; i < n; i++) {
      const page = doc.loadPage(i)
      try {
        const txt = textoMesa(page).map((t) => t.replace(RX_PREFIJO_HASH, ''))
        let [matches, esExacto] = matchPiezas(txt, piezas)
        if (!matches.length) [matches, esExacto] = matchPiezas(capasMesa(mupdf, page), piezas)
        if (!matches.length) {
          const toks = new Set()
          for (const t of txt) for (const w of splitPy(normGenerico(t))) if (w && !esDigitoPy(w) && !STOP_ROTULO.has(w)) toks.add(w)
          if (toks.size) huerfanas.push([i + 1, toks])
          continue
        }
        for (const nom of matches) {
          if (exactos.has(nom)) continue
          if (esExacto) { mapeo.set(nom, i + 1); exactos.add(nom) }
          else if (!mapeo.has(nom)) mapeo.set(nom, i + 1)
        }
      } finally { page.destroy() }
    }
    // PASE DE SUBCONJUNTO — rótulos incompletos sobre un único genérico huérfano
    const porgen = porGenerico(piezas)
    for (const [mesa, toks] of huerfanas) {
      const cands = []
      for (const [g, ps] of porgen) {
        if (!g) continue
        const palabras = new Set(splitPy(g))
        if ([...toks].every((t) => palabras.has(t)) && !ps.some((pp) => mapeo.has(pp))) cands.push(g)
      }
      if (cands.length === 1) for (const nom of porgen.get(cands[0])) if (!mapeo.has(nom)) mapeo.set(nom, mesa)
    }
  } finally { doc.destroy() }
  return Object.fromEntries(mapeo)
}

/** `_variantes_token`: `[variantes, esExacta]` o `[null, false]`. */
export function variantesToken(token, variantesOrden) {
  token = pyStrip(String(token))
  const norm = {}
  for (const v of variantesOrden) norm[normNombre(v)] = v
  if (variantesOrden.includes(token)) return [[token], true]
  if (normNombre(token) in norm) return [[norm[normNombre(token)]], true]
  if (token.includes('-')) {
    const k = token.indexOf('-')
    const a = pyStrip(token.slice(0, k)), b = pyStrip(token.slice(k + 1))
    const va = variantesOrden.includes(a) ? a : norm[normNombre(a)]
    const vb = variantesOrden.includes(b) ? b : norm[normNombre(b)]
    if (va && vb) {
      const i = variantesOrden.indexOf(va), j = variantesOrden.indexOf(vb)
      return [variantesOrden.slice(Math.min(i, j), Math.max(i, j) + 1), false]
    }
  }
  return [null, false]
}

/** `str.split(None, 1)` de Python. */
function splitUnaVez(s) {
  const c = Array.from(s)
  const esWs = (ch) => new RegExp('[' + WS_PY + ']').test(ch)
  let i = 0
  while (i < c.length && esWs(c[i])) i++
  if (i >= c.length) return []
  let j = i
  while (j < c.length && !esWs(c[j])) j++
  const primero = c.slice(i, j).join('')
  let k = j
  while (k < c.length && esWs(c[k])) k++
  return k >= c.length ? [primero] : [primero, c.slice(k).join('')]
}

/** `_parse_pieza_hash`: `#<variante-o-rango> <pieza>` → `[piezas, variantes, esExacta]` o null. */
export function parsePiezaHash(linea, piezas, variantesOrden) {
  const t = pyStrip(String(linea))
  if (!t.startsWith('#')) return null
  const parts = splitUnaVez(pyStrip(t.slice(1)))
  if (parts.length < 2) return null
  const [variantes, esExacta] = variantesToken(parts[0], variantesOrden)
  if (!variantes || !variantes.length) return null
  const [piezasMatch] = matchPiezas([parts[1]], piezas)
  if (!piezasMatch.length) return null
  return [piezasMatch, variantes, esExacta]
}

/** `mapeo_variantes_arte`: {pieza: {variante: mesa}} de las mesas `#variante PIEZA`. */
export function mapeoVariantesArte(mupdf, bytes, registro, variantesOrden) {
  const doc = abrir(mupdf, bytes)
  const rango = new Map(), exacta = new Map()
  try {
    const piezas = ordenarPy(Object.keys(registro))
    const n = doc.countPages()
    for (let i = 0; i < n; i++) {
      const page = doc.loadPage(i)
      try {
        for (const ln of [...textoMesa(page), ...capasMesa(mupdf, page)]) {
          const r = parsePiezaHash(ln, piezas, variantesOrden || [])
          if (!r) continue
          const [piezasMatch, variantes, esExacta] = r
          const target = esExacta ? exacta : rango
          for (const pieza of piezasMatch) {
            if (!target.has(pieza)) target.set(pieza, new Map())
            const d = target.get(pieza)
            for (const v of variantes) if (!d.has(v)) d.set(v, i + 1)
          }
          break                                        // una mesa = un rótulo
        }
      } finally { page.destroy() }
    }
  } finally { doc.destroy() }
  const out = {}
  for (const pieza of new Set([...rango.keys(), ...exacta.keys()])) {
    const d = new Map(rango.get(pieza) || [])
    for (const [v, m] of (exacta.get(pieza) || [])) d.set(v, m)      // exacta pisa rango
    out[pieza] = Object.fromEntries(d)
  }
  return out
}

/** `arte_es_separado(path_arte, path_plantilla)`. */
export function arteEsSeparado(mupdf, bytesArte, bytesPlantilla) {
  const da = abrir(mupdf, bytesArte), db = abrir(mupdf, bytesPlantilla)
  try {
    if (da.countPages() === db.countPages()) {
      const cb = new Set(nombresOcgs(db)), ca = new Set(nombresOcgs(da))
      const tallesMolde = [...cb].filter((x) => !CAPAS_SISTEMA.has(x))
      if (tallesMolde.length && tallesMolde.every((t) => ca.has(t))) return false
    }
    return true
  } finally { da.destroy(); db.destroy() }
}

/** `_mesa_tiene_diseno`, exportado para el contrato. */
export { mesaTieneDiseno }

/**
 * `detectar_arte(path_arte, registro_molde, ancho_thumb=240)`: {mesas: [{mesa, w_cm, h_cm,
 * tiene_diseno, rango, rotulo, nombre_detectado, thumb, svg, thumb_w, thumb_h, sugerencia}],
 * piezas}. `thumb` = PNG en base64 dibujado con mupdf.js (guías, editables y capas de
 * personalización ocultas), a la misma escala que PyMuPDF.
 */
export function detectarArte(mupdf, bytes, registro, anchoThumb = 240) {
  const doc = abrir(mupdf, bytes)        // para MINIATURAS (capas ocultas)
  const docTxt = abrir(mupdf, bytes)     // para LEER nombres (todo visible)
  try {
    try {
      for (const c of capasUi(doc)) {
        const nc = normNombre(c.text || '')
        if (esCapaGuia(c.text) || esCapaEditable(c.text) || !CAPAS_GRAFICAS.has(nc)) configurarCapa(doc, c.number, 2)
      }
    } catch { /* como Python */ }
    const piezas = ordenarPy(Object.keys(registro))
    const tamPieza = {}
    for (const p of piezas) {
      let v = null
      for (const x of Object.values(registro[p])) if (v === null || Number(x.h_cm) > Number(v.h_cm)) v = x   // max(key=h_cm): el primero
      tamPieza[p] = [Number(v.w_cm), Number(v.h_cm)]
    }
    const mesas = []
    const n = doc.countPages()
    for (let i = 0; i < n; i++) {
      const pg = doc.loadPage(i), pgTxt = docTxt.loadPage(i)
      try {
        const pr = pg.getBounds()
        const prW = Math.max(0, pr[2] - pr[0]), prH = Math.max(0, pr[3] - pr[1])
        const zoom = anchoThumb / prW
        const pix = pixmapMesa(mupdf, pg, zoom, false)
        let thumb, tw, th
        try { thumb = base64De(pix.asPNG()); tw = pix.getWidth(); th = pix.getHeight() } finally { pix.destroy() }
        const txtMesa = textoMesa(pgTxt)
        const capMesa = capasMesa(mupdf, pgTxt)
        let nomDet = matchPieza(txtMesa, piezas)
        if (!nomDet) nomDet = matchPieza(capMesa, piezas)
        let rango = ''
        for (const t of [...txtMesa, ...capMesa]) {
          const m = RX_RANGO.exec(t || '')
          if (m) { rango = m[1]; break }
        }
        let rotulo = ''
        for (const t of [...txtMesa, ...capMesa]) {
          if (pyStrip(t || '').startsWith('#')) { rotulo = pyStrip(t); break }
        }
        if (!rotulo) {
          const cands = txtMesa.filter((t) => Array.from(t || '').filter(esLetraPy).length >= 3).map((t) => pyStrip(t || ''))
          if (cands.length) rotulo = masLargaPy(cands)
        }
        mesas.push({ mesa: i + 1, w_cm: pyRound(prW / CM, 1), h_cm: pyRound(prH / CM, 1),
                     tiene_diseno: !!mesaTieneDiseno(mupdf, pgTxt), rango, rotulo, nombre_detectado: nomDet,
                     thumb, svg: null, thumb_w: tw, thumb_h: th })
      } finally { pg.destroy(); pgTxt.destroy() }
    }
    // sugerencia: 1) nombre escrito en la mesa · 2) por TAMAÑO para el resto (las grandes primero)
    const libres = new Set(piezas)
    for (const m of mesas) {
      const nd = m.nombre_detectado
      if (nd && libres.has(nd)) { m.sugerencia = nd; libres.delete(nd) }
    }
    for (const m of [...mesas].sort((a, b) => -(a.w_cm * a.h_cm) - -(b.w_cm * b.h_cm))) {
      if (m.sugerencia || !libres.size) continue
      const dist = (p) => { const [pw, ph] = tamPieza[p]; return Math.abs(m.w_cm - pw) / Math.max(pw, 1) + Math.abs(m.h_cm - ph) / Math.max(ph, 1) }
      let mejor = null, md = Infinity
      for (const p of libres) { const d = dist(p); if (d < md) { mejor = p; md = d } }   // min(): el primero de los empatados (en Python, el orden del set)
      m.sugerencia = mejor
      libres.delete(mejor)
    }
    for (const m of mesas) if (m.sugerencia === undefined) m.sugerencia = ''
    return { mesas, piezas }
  } finally { doc.destroy(); docTxt.destroy() }
}

/** `fuentes_requeridas_arte`: {fuente: ['etiquetas' | 'personalización', …]} en orden de aparición. */
export function fuentesRequeridasArte(mupdf, bytes) {
  const requeridas = new Map()
  for (const capa of ['Personalizable', null]) {
    const doc = abrir(mupdf, bytes)
    try {
      for (const c of capasUi(doc)) {
        const on = capa ? c.text === capa : ['diseño', 'diseno'].includes(pyStrip(c.text).toLowerCase())
        configurarCapa(doc, c.number, on ? 0 : 1)
      }
      const n = doc.countPages()
      for (let i = 0; i < n; i++) {
        const page = doc.loadPage(i)
        try {
          for (const b of textoDict(page)) for (const l of b.lines) for (const s of l.spans) {
            const k = s.font.split('+').pop()
            if (!requeridas.has(k)) requeridas.set(k, new Set())
            requeridas.get(k).add(capa ? 'personalización' : 'etiquetas')
          }
        } finally { page.destroy() }
      }
    } finally { doc.destroy() }
  }
  const out = {}
  for (const [k, u] of requeridas) out[k] = ordenarPy(u)
  return out
}

/** `_separaciones(pg.obj, vistos)`: las tintas planas alcanzables desde la página (profundidad ≤ 16). */
function separaciones(pageObj) {
  const enc = []
  const vistos = new Set()
  const rec = (o, pr) => {
    if (pr > 16) return
    if (!o || o.isNull()) return
    if (o.isIndirect()) {
      const og = o.asIndirect()
      if (vistos.has(og)) return
      vistos.add(og)
      o = o.resolve()
    }
    if (o.isArray() && o.length >= 2) {
      try {
        const a0 = o.get(0)
        if (a0.isName() && a0.asName() === 'Separation') {
          const a1 = o.get(1)
          const t = a1.isName() ? a1.asName() : a1.isString() ? textoPikepdf(a1.asByteString()).slice(1) : null
          if (t !== null && !enc.includes(t)) enc.push(t)
        }
      } catch { /* pass */ }
    }
    if (o.isDictionary()) {
      const claves = []
      o.forEach((v, k) => claves.push(String(k)))
      claves.sort((a, b) => (a < b ? -1 : a > b ? 1 : 0))          // QPDF: std::map, orden por bytes
      for (const k of claves) { try { rec(o.get(k), pr + 1) } catch { /* pass */ } }
    } else if (o.isArray()) {
      const n = o.length
      for (let i = 0; i < n; i++) { try { rec(o.get(i), pr + 1) } catch { /* pass */ } }
    }
  }
  rec(pageObj, 0)
  return enc
}

const detalleFuentes = (requeridas, catalogo, alias) => {
  const faltan = Object.entries(requeridas).filter(([n]) => !resolverFuente(n, catalogo, alias || {}))
  return { faltan, texto: !faltan.length ? Object.keys(requeridas).join(', ')
    : 'FALTAN: ' + faltan.map(([n, u]) => `${n} (${u.join('/')})`).join(', ') }
}

/**
 * `validar_arte(path_arte, path_plantilla, carpeta_fuentes)` (el arte CLÁSICO, con la estructura
 * del molde). `fuentes` = {catalogo, alias} como los da `/api/productos/<pid>/arte_contexto`.
 */
export function validarArte(mupdf, bytesArte, bytesPlantilla, fuentes) {
  const { catalogo = [], alias = {} } = fuentes || {}
  const db = abrir(mupdf, bytesPlantilla), da = abrir(mupdf, bytesArte)
  const checks = []
  let ok = true
  try {
    const nb = db.countPages(), na = da.countPages()
    let coincide = nb === na
    if (coincide) {
      for (let i = 0; i < nb; i++) {
        const rb = db.loadPage(i).getBounds(), ra = da.loadPage(i).getBounds()
        const wb = Math.max(0, rb[2] - rb[0]), hb = Math.max(0, rb[3] - rb[1]), wa = Math.max(0, ra[2] - ra[0]), ha = Math.max(0, ra[3] - ra[1])
        if (!(Math.abs(wb - wa) < 2 && Math.abs(hb - ha) < 2)) { coincide = false; break }
      }
    }
    checks.push({ nombre: 'Estructura coincide con la plantilla', ok: coincide, detalle: `${na}/${nb} mesas` })
    ok = ok && coincide

    const cb = new Set(nombresOcgs(db)), ca = new Set(nombresOcgs(da))
    const faltanCapas = ordenarPy([...cb].filter((x) => !ca.has(x)))
    const comunes = [...ca].filter((x) => cb.has(x)).length
    checks.push({ nombre: 'Capas requeridas presentes', ok: !faltanCapas.length,
                  detalle: `${comunes}/${cb.size}` + (faltanCapas.length ? ` — faltan ${reprPy({ lista: faltanCapas })}` : '') })
    ok = ok && !faltanCapas.length

    const tintas = new Map()
    for (let i = 0; i < na; i++) {
      const pg = da.loadPage(i)
      try {
        for (const t of separaciones(pg.getObject())) {
          if (t !== 'All') tintas.set(t, (tintas.get(t) || 0) + 1)
        }
      } finally { pg.destroy() }
    }
    checks.push({ nombre: 'Tintas planas en el PDF', ok: true,
                  detalle: [...tintas].map(([t, n]) => `${t} (${n} mesas)`).join(', ') || 'ninguna (solo proceso)' })

    const d2 = abrir(mupdf, bytesArte)
    const planas = []
    try {
      for (const c of capasUi(d2)) if (c.text !== 'Fondo') configurarCapa(d2, c.number, 2)
      for (let i = 0; i < d2.countPages(); i++) {
        const pg = d2.loadPage(i)
        try {
          const pix = pixmapMesa(mupdf, pg, 0.04, false)
          try { if (desvioMedio(pix) < 8) planas.push(i + 1) } finally { pix.destroy() }
        } finally { pg.destroy() }
      }
    } finally { d2.destroy() }
    checks.push({ nombre: 'Cobertura de diseño', ok: !planas.length,
                  detalle: !planas.length ? 'sin mesas vacías' : `mesas sin diseño: ${reprPy({ lista: planas.map((x) => ({ int: x })) })}` })

    const requeridas = fuentesRequeridasArte(mupdf, bytesArte)
    const { faltan, texto } = detalleFuentes(requeridas, catalogo, alias)
    checks.push({ nombre: 'Tipografías requeridas en catálogo', ok: !faltan.length, detalle: texto })
    ok = ok && !faltan.length

    const pers = extraerPersonalizacion(mupdf, bytesArte)
    const nPers = Object.keys(pers).length
    checks.push({ nombre: 'Placeholders de personalización', ok: nPers > 0,
                  detalle: nPers ? `${nPers} mesas de espalda` : 'no encontrados (pedido sin nombre/número)' })

    return { aprobado: !!ok, checks, tintas: Object.fromEntries(tintas), fuentes_requeridas: requeridas,
             fuentes_faltantes: ordenarPy(faltan.map(([n]) => n)), personalizacion: pers }
  } finally { db.destroy(); da.destroy() }
}

/**
 * `validar_arte_separado(path_arte, registro_molde, carpeta_fuentes, mapeo, variantes_orden=None,
 * piezas_scope=None)`. `fuentes` = {catalogo, alias}.
 */
export function validarArteSeparado(mupdf, bytes, registro, fuentes, mapeo, variantesOrden = null, piezasScope = null) {
  const { catalogo = [], alias = {} } = fuentes || {}
  const doc = abrir(mupdf, bytes)
  try {
    const nDoc = doc.countPages()
    let piezas
    if (piezasScope !== null && piezasScope !== undefined) {
      const sc = new Set(piezasScope)
      piezas = ordenarPy(Object.keys(registro).filter((p) => sc.has(p)))
    } else piezas = ordenarPy(Object.keys(registro))
    const checks = []
    let ok = true

    let mapeoVar = {}
    if (variantesOrden && variantesOrden.length) {
      try { mapeoVar = mapeoVariantesArte(mupdf, bytes, registro, variantesOrden) } catch { mapeoVar = {} }
    }
    const tiene = (d, p) => d && d[p] && (typeof d[p] !== 'object' || Object.keys(d[p]).length > 0)

    const sinAsignar = piezas.filter((p) => !mapeo[p] && !tiene(mapeoVar, p))
    checks.push({ nombre: 'Cada pieza tiene un arte asignado', ok: !sinAsignar.length,
                  detalle: `${piezas.length - sinAsignar.length}/${piezas.length} piezas` + (sinAsignar.length ? ` — faltan: ${sinAsignar.join(', ')}` : '') })
    ok = ok && !sinAsignar.length

    if (variantesOrden && variantesOrden.length) {
      const sinCubrir = []
      for (const p of piezas) {
        if (mapeo[p] || !tiene(mapeoVar, p)) continue
        const faltan = variantesOrden.filter((v) => !(v in mapeoVar[p]))
        if (faltan.length) sinCubrir.push(`${p}: faltan ${faltan.join(', ')}`)
      }
      if (sinCubrir.length) {
        checks.push({ nombre: 'Todas las variantes tienen diseño', ok: false, aviso: true,
                      detalle: 'esas variantes saldrán sin diseño en esa pieza — ' + sinCubrir.join('; ') })
      }
    }

    const fuera = piezas.filter((p) => mapeo[p] && !(1 <= Math.trunc(Number(mapeo[p])) && Math.trunc(Number(mapeo[p])) <= nDoc)).map((p) => `${p}→mesa ${mapeo[p]}`)
    if (fuera.length) {
      checks.push({ nombre: 'Mesas de arte válidas', ok: false, detalle: fuera.join('; ') })
      ok = false
    }

    const vaciasSet = new Set()
    const cacheDiseno = new Map()
    for (const p of piezas) {
      if (!mapeo[p]) continue
      const m = Math.trunc(Number(mapeo[p]))
      if (!(1 <= m && m <= nDoc)) continue
      if (!cacheDiseno.has(m)) {
        const pg = doc.loadPage(m - 1)
        try { cacheDiseno.set(m, mesaTieneDiseno(mupdf, pg)) } finally { pg.destroy() }
      }
      if (!cacheDiseno.get(m)) vaciasSet.add(m)
    }
    const vacias = [...vaciasSet].sort((a, b) => a - b)
    checks.push({ nombre: 'Las mesas asignadas tienen diseño', ok: !vacias.length,
                  detalle: !vacias.length ? 'todas con diseño' : `mesas vacías: ${reprPy({ lista: vacias.map((x) => ({ int: x })) })}` })
    ok = ok && !vacias.length

    const requeridas = fuentesRequeridasArte(mupdf, bytes)
    const textoDiseno = ordenarPy(Object.entries(requeridas).filter(([, u]) => u.includes('etiquetas')).map(([n]) => n))
    checks.push({ nombre: 'Diseño sin texto vivo (en curvas)', ok: !textoDiseno.length,
                  detalle: !textoDiseno.length ? 'sin texto vivo'
                    : 'convertí a curvas el texto del diseño (Texto → Crear contornos). Fuentes: ' + textoDiseno.join(', ') })
    ok = ok && !textoDiseno.length

    const pers = extraerPersonalizacion(mupdf, bytes)
    const fPers = new Set()
    for (const m of Object.values(pers)) for (const c of Object.values(m)) fPers.add(c.fuente)
    const faltanF = ordenarPy([...fPers].filter((f) => !resolverFuente(f, catalogo, alias || {})))
    if (fPers.size) {
      checks.push({ nombre: 'Tipografías de personalización en catálogo', ok: !faltanF.length, aviso: !!faltanF.length,
                    detalle: !faltanF.length ? ordenarPy(fPers).join(', ')
                      : 'no están en el catálogo (ese texto NO se estampará): ' + faltanF.join(', ') })
    }

    return { aprobado: !!ok, checks, modo: 'separado', mapeo, personalizacion: pers, fuentes_requeridas: requeridas,
             fuentes_faltantes: faltanF }
  } finally { doc.destroy() }
}
