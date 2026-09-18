// LOS PLACEHOLDERS DE PERSONALIZACIÓN DEL ARTE (Nombre, Número, Palabra…) — PLAN_NAVEGADOR.md,
// etapa 3, camino A. Traducción de `motor_pedido.extraer_personalizacion` y de sus tres lectores
// del content-stream: `_colores_personalizable` (relleno nativo), `_trazo_personalizable`
// (borde) y `_pasadas_personalizable` (la PILA de apariencias ordenada, que es la que manda).
//
// Devuelve EXACTAMENTE lo que devuelve Python: `{mesa: {campo: {cx, baseline_y, size, fuente,
// ancho, color, colorn, trazo, pasadas, baseline_pts}}}`, con los mismos redondeos (`pyRound`).
// El contrato `verificar_navegador_arte.py` lo compara valor por valor.
//
// 🔴 La clave que manda es la CAPA (`CLAVE_CAPA`), no el texto del `Tj`: con una fuente CID el
// texto son ids de glifo y nunca coincide con «nombre»/«00» (ver MAPA, 2026-09-10). Las claves
// por texto se mantienen igual que en Python para los desempates.
import { pyRound, pyStrip } from '../py.js'
import { instrucciones, contenidoCrudo } from '../pdf/contenido.js'
import { abrir, capasUi, configurarCapa, nombresOc, normNombre, textoDict, strOperando, floatOperando } from './texto.js'

// `CAPAS_NO_PERS` de motor_pedido: cualquier OTRA capa es un campo de personalización
export const CAPAS_NO_PERS = new Set(['diseño', 'diseno', 'personalizable', 'guias', 'guías', 'guides',
  'guia', 'guía', 'fondo', 'capa 1', 'referencia', '0'])
export const CAPAS_GRAFICAS = new Set([...CAPAS_NO_PERS].filter((x) => x !== 'personalizable'))
export const CLAVE_CAPA = '\x00capa:'
export const CAMPO_ALIAS = { '00': 'numero', nro: 'numero', num: 'numero', jugador: 'nombre', apellido: 'nombre' }

/** `_es_capa_editable`: la capa es un OBJETO editable (mover/rotar/escalar), no un campo. */
export const esCapaEditable = (nombre) => normNombre(nombre).startsWith('editable')

/** `_texto_de_tj`: el texto de un Tj/TJ/'/" tal como lo decodifica pikepdf. */
export function textoDeTj(ins) {
  const op = ins.op
  try {
    if (op === 'TJ') {
      const arr = ins.args[0]
      if (!Array.isArray(arr)) throw new Error('TJ')
      const partes = []
      for (const x of arr) {
        try { floatOperando(x) } catch { partes.push(strOperando(x)) }
      }
      return partes.join('')
    }
    if (!ins.args.length) return ''
    return strOperando(ins.args[ins.args.length - 1])
  } catch {
    return ''
  }
}

/** `_n_de_cs` de los tres lectores: nº de componentes de un ColorSpace de la página, por nombre. */
function nDeColorSpaces(page) {
  const cache = new Map()
  let csres = null
  try { csres = page.getObject().get('Resources').get('ColorSpace') } catch { csres = null }
  const nulo = (o) => !o || o.isNull()
  return (nombreConBarra) => {
    if (cache.has(nombreConBarra)) return cache.get(nombreConBarra)
    let n = null
    try {
      if (!nulo(csres) && nombreConBarra.startsWith('/')) {
        const o = csres.get(nombreConBarra.slice(1))
        if (!nulo(o)) {
          if (o.isArray()) {
            const base = '/' + o.get(0).asName()
            if (base === '/ICCBased' && o.length > 1) {
              const nO = o.get(1).get('N')
              n = (nulo(nO) ? 0 : Math.trunc(nO.asNumber())) || null
            } else if (base === '/DeviceN' && o.length > 1) {
              n = o.get(1).length
            } else n = { '/CalRGB': 3, '/CalGray': 1, '/Separation': 1 }[base] ?? null
          } else {
            n = { '/DeviceCMYK': 4, '/DeviceRGB': 3, '/DeviceGray': 1 }[o.isName() ? '/' + o.asName() : ''] ?? null
          }
        }
      }
    } catch { n = null }
    cache.set(nombreConBarra, n)
    return n
  }
}

const OP_N = { 4: 'k', 3: 'rg', 1: 'g' }
const N_OP = { k: 4, rg: 3, g: 1 }

function colorDevice(op, args) {
  // `(op, tuple(round(float(x), 4) for x in operands))`; con un operando no numérico → None
  try { return [op, args.map((x) => pyRound(floatOperando(x), 4))] } catch { return null }
}

function colorNombrado(nCs, args) {
  // `scn`/`sc` (o SCN/SC): sólo si son números y la cantidad coincide con k/rg/g
  let vals
  try { vals = args.map(floatOperando) } catch { return undefined }
  const o2 = OP_N[nCs || vals.length]
  if (o2 && vals.length === N_OP[o2]) return [o2, vals.map((v) => pyRound(v, 4))]
  return undefined
}

/** El estado común de los tres lectores: `q`/`Q`, colores, ancho de trazo, y la pila de capas OC. */
function recorrerMesa(page) {
  const insts = [...instrucciones(contenidoCrudo(page))]
  const nCs = nDeColorSpaces(page)
  const nombresDe = (ins) => (ins.args.length === 2 && ins.args[0].n === 'OC') ? nombresOc(page, ins.args[1]).map(normNombre) : null
  return { insts, nCs, nombresDe }
}

/** `_colores_personalizable`: {mesa: {texto_norm | CLAVE_CAPA+capa: [op, [vals]]}}. */
export function coloresPersonalizable(doc) {
  const res = {}
  const n = doc.countPages()
  for (let i = 0; i < n; i++) {
    const page = doc.loadPage(i)
    try {
      const { insts, nCs, nombresDe } = recorrerMesa(page)
      let dentro = 0, cur = null, curCsN = null, capa = ''
      const per = new Map()
      const gstack = []
      for (const ins of insts) {
        const op = ins.op
        if (op === 'q') { gstack.push([cur, curCsN]); continue }
        if (op === 'Q') { if (gstack.length) [cur, curCsN] = gstack.pop(); continue }
        if (op === 'cs') curCsN = ins.args.length ? nCs(strOperando(ins.args[0])) : null
        else if (op === 'k' || op === 'rg' || op === 'g') cur = colorDevice(op, ins.args)
        else if (op === 'scn' || op === 'sc') { const c = colorNombrado(curCsN, ins.args); if (c !== undefined) cur = c }
        if (op === 'BDC' && ins.args.length === 2 && ins.args[0].n === 'OC') {
          const nombres = nombresDe(ins)
          if (nombres.some((x) => !CAPAS_GRAFICAS.has(x))) {
            if (dentro === 0) capa = nombres.find((x) => !CAPAS_GRAFICAS.has(x)) || ''
            dentro += 1; continue
          } else if (dentro) dentro += 1
        } else if ((op === 'BDC' || op === 'BMC') && dentro) dentro += 1
        else if (op === 'EMC' && dentro) { dentro -= 1; continue }
        if (dentro && (op === 'Tj' || op === 'TJ' || op === "'" || op === '"') && cur !== null) {
          const k = normNombre(textoDeTj(ins))
          if (k && !per.has(k)) per.set(k, [cur[0], [...cur[1]]])
          if (capa && !per.has(CLAVE_CAPA + capa)) per.set(CLAVE_CAPA + capa, [cur[0], [...cur[1]]])
        }
      }
      if (per.size) res[String(i + 1)] = per
    } finally {
      page.destroy()
    }
  }
  return res
}

/** `_trazo_personalizable`: {mesa: {clave: [op, [vals], ancho]}}. */
export function trazoPersonalizable(doc) {
  const res = {}
  const n = doc.countPages()
  for (let i = 0; i < n; i++) {
    const page = doc.loadPage(i)
    try {
      const { insts, nCs, nombresDe } = recorrerMesa(page)
      let dentro = 0, scol = null, scsN = null, sw = null, ultTxt = '', capa = ''
      const per = new Map()
      const gstack = []
      for (const ins of insts) {
        const op = ins.op
        if (op === 'q') { gstack.push([scol, scsN, sw]); continue }
        if (op === 'Q') { if (gstack.length) [scol, scsN, sw] = gstack.pop(); continue }
        if (op === 'CS') scsN = ins.args.length ? nCs(strOperando(ins.args[0])) : null
        else if (op === 'K' || op === 'RG' || op === 'G') scol = colorDevice(op.toLowerCase(), ins.args)
        else if (op === 'SCN' || op === 'SC') { const c = colorNombrado(scsN, ins.args); if (c !== undefined) scol = c }
        else if (op === 'w') { try { sw = floatOperando(ins.args[0]) } catch { /* pass */ } }
        if (op === 'BDC' && ins.args.length === 2 && ins.args[0].n === 'OC') {
          const nombres = nombresDe(ins)
          if (nombres.some((x) => !CAPAS_GRAFICAS.has(x))) {
            if (dentro === 0) { scol = null; sw = null; capa = nombres.find((x) => !CAPAS_GRAFICAS.has(x)) || '' }
            dentro += 1; continue
          } else if (dentro) dentro += 1
        } else if ((op === 'BDC' || op === 'BMC') && dentro) dentro += 1
        else if (op === 'EMC' && dentro) { dentro -= 1; continue }
        if (dentro && (op === 'Tj' || op === 'TJ' || op === "'" || op === '"')) {
          const t = normNombre(textoDeTj(ins))
          if (t) ultTxt = t
        }
        if (dentro && (op === 'S' || op === 's' || op === 'B' || op === 'B*' || op === 'b' || op === 'b*') && scol !== null && sw && sw > 0) {
          if (ultTxt && !per.has(ultTxt)) per.set(ultTxt, [scol[0], [...scol[1]], pyRound(sw, 3)])
          if (capa && !per.has(CLAVE_CAPA + capa)) per.set(CLAVE_CAPA + capa, [scol[0], [...scol[1]], pyRound(sw, 3)])
        }
      }
      if (per.size) res[String(i + 1)] = per
    } finally {
      page.destroy()
    }
  }
  return res
}

const mismaPasada = (a, b) => a.t === b.t && a.w === b.w && a.color[0] === b.color[0] &&
  a.color[1].length === b.color[1].length && a.color[1].every((v, i) => v === b.color[1][i])

/** `_pasadas_personalizable`: la pila de apariencias {mesa: {clave: [{t, color, w}, …]}}. */
export function pasadasPersonalizable(doc) {
  const res = {}
  const n = doc.countPages()
  for (let i = 0; i < n; i++) {
    const page = doc.loadPage(i)
    try {
      const { insts, nCs, nombresDe } = recorrerMesa(page)
      let fcol = null, fcsN = null, scol = null, scsN = null, sw = null
      let dentro = 0, capa = '', acum = '', pl = []
      const per = new Map()
      const gstack = []
      const add = (p) => { if (pl.length && mismaPasada(pl[pl.length - 1], p)) return; pl.push(p) }
      for (const ins of insts) {
        const op = ins.op
        if (op === 'q') { gstack.push([fcol, fcsN, scol, scsN, sw]); continue }
        if (op === 'Q') { if (gstack.length) [fcol, fcsN, scol, scsN, sw] = gstack.pop(); continue }
        if (op === 'cs') fcsN = ins.args.length ? nCs(strOperando(ins.args[0])) : null
        else if (op === 'CS') scsN = ins.args.length ? nCs(strOperando(ins.args[0])) : null
        else if (op === 'k' || op === 'rg' || op === 'g') fcol = colorDevice(op, ins.args)
        else if (op === 'K' || op === 'RG' || op === 'G') scol = colorDevice(op.toLowerCase(), ins.args)
        else if (op === 'scn' || op === 'sc') { const c = colorNombrado(fcsN, ins.args); if (c !== undefined) fcol = c }
        else if (op === 'SCN' || op === 'SC') { const c = colorNombrado(scsN, ins.args); if (c !== undefined) scol = c }
        else if (op === 'w') { try { sw = floatOperando(ins.args[0]) } catch { /* pass */ } }

        if (op === 'BDC' && ins.args.length === 2 && ins.args[0].n === 'OC') {
          const nombres = nombresDe(ins)
          if (nombres.some((x) => !CAPAS_GRAFICAS.has(x))) {
            if (dentro === 0) { scol = null; sw = null; acum = ''; pl = []; capa = nombres.find((x) => !CAPAS_GRAFICAS.has(x)) || '' }
            dentro += 1; continue
          } else if (dentro) dentro += 1
        } else if ((op === 'BDC' || op === 'BMC') && dentro) dentro += 1
        else if (op === 'EMC' && dentro) {
          dentro -= 1
          if (!dentro) {
            // AL SALIR DE LA CAPA se vuelca todo (no depende del `ET`, ver Python)
            const t = normNombre(acum)
            if (t && pl.length && !per.has(t)) per.set(t, pl.map((p) => ({ t: p.t, color: [p.color[0], [...p.color[1]]], w: p.w })))
            if (capa && pl.length && !per.has(CLAVE_CAPA + capa)) per.set(CLAVE_CAPA + capa, pl.map((p) => ({ t: p.t, color: [p.color[0], [...p.color[1]]], w: p.w })))
            acum = ''; pl = []
          }
          continue
        }
        if (!dentro) continue
        if (op === 'Tj' || op === 'TJ' || op === "'" || op === '"') {
          acum += textoDeTj(ins) || ''
          if (fcol !== null) add({ t: 'f', color: [fcol[0], [...fcol[1]]], w: 0.0 })
        } else if ((op === 'S' || op === 's') && scol !== null && sw && sw > 0) {
          add({ t: 'S', color: [scol[0], [...scol[1]]], w: pyRound(sw, 3) })
        } else if (op === 'B' || op === 'B*' || op === 'b' || op === 'b*') {
          if (fcol !== null) add({ t: 'f', color: [fcol[0], [...fcol[1]]], w: 0.0 })
          if (scol !== null && sw && sw > 0) add({ t: 'S', color: [scol[0], [...scol[1]]], w: pyRound(sw, 3) })
        }
      }
      if (per.size) res[String(i + 1)] = per
    } finally {
      page.destroy()
    }
  }
  return res
}

/** `_match_texto`: primero por capa, después por texto (exacto, contención, único). */
function matchTexto(dmesa, tn, capa) {
  if (!dmesa || !dmesa.size) return null
  if (capa) {
    const v = dmesa.get(CLAVE_CAPA + capa)
    if (v !== undefined) return v
  }
  const txt = [...dmesa].filter(([k]) => !String(k).startsWith(CLAVE_CAPA))
  let v = txt.find(([k]) => k === tn)?.[1]
  if (v === undefined) v = txt.find(([k]) => k && (tn.includes(k) || k.includes(tn)))?.[1]
  if (v === undefined && txt.length === 1) v = txt[0][1]
  return v === undefined ? null : v
}

const copia = (v) => (v === null || v === undefined) ? null : JSON.parse(JSON.stringify(v))

/**
 * `extraer_personalizacion(path_arte, campos=None)` sobre los bytes del arte. `campos` = lista de
 * nombres de campo a buscar; sin ella se auto-descubren las capas que no son de sistema ni
 * «Editable …» (en un arte separado no hay talles como capas: eso es del camino B).
 */
export function extraerPersonalizacion(mupdf, bytes, campos = null) {
  const sys = CAPAS_NO_PERS
  if (campos === null) {
    const d = abrir(mupdf, bytes)
    try {
      campos = capasUi(d).map((c) => c.text).filter((t) => !sys.has(normNombre(t)) && !esCapaEditable(t))
    } finally { d.destroy() }
  }
  const nativos = leerConDoc(mupdf, bytes, coloresPersonalizable)
  const trazos = leerConDoc(mupdf, bytes, trazoPersonalizable)
  const pasadas = leerConDoc(mupdf, bytes, pasadasPersonalizable)
  const pers = {}

  const registrar = (mesa, campo, l, capa) => {
    const s0 = l.spans[0]
    const bb = l.bbox
    const txt = pyStrip(l.spans.map((s) => s.text).join(''))
    const tn = normNombre(txt)
    const m = String(mesa)
    if (!pers[m]) pers[m] = {}
    if (!pers[m][campo]) {
      pers[m][campo] = {
        cx: pyRound((bb[0] + bb[2]) / 2, 1), baseline_y: pyRound(s0.origin[1], 1),
        size: pyRound(s0.size, 1), fuente: s0.font.split('+').pop(),
        ancho: pyRound(Math.max(0, bb[2] - bb[0]), 1), color: s0.color,
        colorn: copia(matchTexto(nativos[m], tn, capa)), trazo: copia(matchTexto(trazos[m], tn, capa)),
        pasadas: copia(matchTexto(pasadas[m], tn, capa)),
        baseline_pts: [], _txt: '', _capa: capa,
      }
    }
    const d = pers[m][campo]
    for (const s of l.spans) {
      if (pyStrip(s.text)) d.baseline_pts.push([pyRound(s.origin[0], 1), pyRound(s.origin[1], 1), pyRound(bb[0], 1), pyRound(bb[2], 1)])
    }
    d._txt += txt
  }

  // 1) Por CAPA: aislar cada capa-campo (mostrarla sola) y leer su texto
  const d0 = abrir(mupdf, bytes)
  let capas
  try { capas = capasUi(d0).map((c) => [c.text, c.number]) } finally { d0.destroy() }
  for (const campo of campos) {
    const cn = normNombre(campo)
    if (!capas.some(([name]) => normNombre(name) === cn)) continue
    const campoCanon = CAMPO_ALIAS[cn] || campo
    const d = abrir(mupdf, bytes)
    try {
      for (const c of capasUi(d)) configurarCapa(d, c.number, normNombre(c.text) === cn ? 0 : 1)
      const n = d.countPages()
      for (let mesa = 1; mesa <= n; mesa++) {
        const page = d.loadPage(mesa - 1)
        try {
          for (const b of textoDict(page)) {
            for (const l of b.lines) {
              if (pyStrip(l.spans.map((s) => s.text).join(''))) registrar(mesa, campoCanon, l, cn)
            }
          }
        } finally { page.destroy() }
      }
    } finally { d.destroy() }
  }

  // Limpiar la línea base (deduplicar, ordenar por x) y RE-MATCHEAR borde/color por el texto completo
  for (const mk of Object.keys(pers)) {
    for (const pl of Object.values(pers[mk])) {
      const bp = pl.baseline_pts || []
      const vistos = new Set(), uniq = []
      for (const p of [...bp].sort((a, b) => a[0] - b[0])) {
        const k = pyRound(p[0], 0) + ',' + pyRound(p[1], 0)
        if (!vistos.has(k)) { vistos.add(k); uniq.push(p) }
      }
      pl.baseline_pts = uniq
      const tn = normNombre(pl._txt || '')
      const cp = pl._capa || null
      if (tn || cp) {
        pl.trazo = copia(matchTexto(trazos[mk], tn, cp)) || pl.trazo
        pl.colorn = copia(matchTexto(nativos[mk], tn, cp)) || pl.colorn
      }
      delete pl._txt
      delete pl._capa
    }
  }
  return pers
}

function leerConDoc(mupdf, bytes, fn) {
  const d = abrir(mupdf, bytes)
  try { return fn(d) } finally { d.destroy() }
}
