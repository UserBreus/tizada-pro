// LAS TIPOGRAFÍAS DEL PEDIDO, RESUELTAS EN ESTA COMPUTADORA — 2026-09-22.
//
// 🔴 POR QUÉ: «el servidor será sólo para sostener el sistema y la base; el resto lo hace la PC de
// quien se conectó». Dos pantallas le pedían al servidor que leyera el arte o el molde:
//   · `GET /api/pedido/fuentes_estado` (paso Arte): qué tipografías pide el diseño, cuáles faltan
//     y cuál tiene elegida cada campo. Leía el arte entero (`extraer_personalizacion`) y de paso
//     calentaba los editables en su pool de procesos;
//   · `GET /api/pedido/fuente_chars` (Planilla): qué caracteres DIBUJA la tipografía de cada campo,
//     para pintar en rojo los que no. Abría cada fuente y probaba glifo por glifo.
// Acá se hace lo mismo con los datos que el servidor ya entrega servidos (`/motor_b`: la
// personalización guardada, el catálogo, los reemplazos del pedido) y el mismo resolvedor de
// tipografías que usa la tizada (`texto/fuentes.js`). Misma forma de respuesta que tenían esos
// endpoints, así la pantalla no cambia.
import { resolverFuente } from '../texto/fuentes.js'
import { claveFuenteCampo, fuenteDeCampo } from '../pieza/estampar.js'
import { FuenteCurvas } from '../texto/curvas.js'
import { traerConCache } from '../cache.js'

const ordenPy = (a, b) => (a < b ? -1 : a > b ? 1 : 0)

async function json(url) {
  const r = await fetch(url)
  const d = await r.json().catch(() => ({}))
  if (!r.ok) { const e = new Error(d.error || `${url}: ${r.status}`); e.datos = d; throw e }
  return d
}

/**
 * Los datos del molde (`/motor_b`) SIN abrir el motor: `motorDe` rearma su hilo si cambian los
 * reemplazos, y esto sólo necesita leer. `reemplazos` = los del par (diseño, molde) del pedido.
 */
async function infoMolde(pid, rutaApi, reemplazos) {
  const q = reemplazos ? '?fuentes_reemplazo=' + encodeURIComponent(JSON.stringify(reemplazos)) : ''
  return json(rutaApi(`/api/productos/${encodeURIComponent(pid)}/motor_b${q}`))
}

/** ¿El molde con diseño todavía no tiene sus páginas por talle? (antes: `desplegado_listo`) */
function preparandoB(info) {
  return !!info.paginas_pendientes || (info.mesas || []).some((m) => !m.paginas)
}

/** La personalización `{mesa: {campo: placeholder}}` que rige: la del molde (B) o la del arte (A). */
function persDe(info, diseno) {
  if (info.camino_b) return info.pers || {}
  const d = (info.disenos || []).find((x) => x.id === (diseno || 'principal'))
  return d ? (d.pers || {}) : null                      // null = ese diseño no tiene arte
}

/** Las fuentes de cada campo, en el orden en que aparecen (con las de cada talle del camino B). */
function fuentesPorCampo(pers) {
  const por = new Map()
  for (const m of Object.values(pers || {})) {
    for (const [campo, c] of Object.entries(m || {})) {
      if (!c || typeof c !== 'object') continue
      const k = String(campo)
      if (!por.has(k)) por.set(k, [])
      const fs = por.get(k)
      for (const f of [c.fuente, ...Object.values(c.por_talle || {}).map((pt) => (pt || {}).fuente)]) {
        if (f && !fs.includes(f)) fs.push(f)
      }
    }
  }
  return por
}

/**
 * `GET /api/pedido/fuentes_estado`, armado acá. `reemplazos` = `{faltante|@campo:x: interno}` del
 * par (diseño, molde). Devuelve `{ok, preparando?, requeridas, faltantes, reemplazables,
 * originales, campos, catalogo, reemplazos}`.
 */
export async function fuentesEstadoLocal({ pid, diseno = 'principal', reemplazos = {}, rutaApi }) {
  const info = await infoMolde(pid, rutaApi, reemplazos)
  const todas = (info.fuentes || {}).catalogo || []
  const alias = (info.fuentes || {}).alias || {}
  // el catálogo del modal: sólo el del SISTEMA (como `catalogo_fuentes(FUENTES)`), por nombre
  const catalogo = todas.filter((c) => !c.propia).map((c) => ({ interno: c.interno, archivo: c.archivo }))
    .sort((a, b) => ordenPy(String(a.interno).toLowerCase(), String(b.interno).toLowerCase()))
  const vacio = { ok: true, requeridas: [], faltantes: [], reemplazables: [], originales: {}, campos: [], catalogo, reemplazos: alias }
  if (!info.camino_a && !info.camino_b) return vacio
  if (info.camino_b && preparandoB(info)) return { ...vacio, preparando: true }
  const pers = persDe(info, diseno)
  if (pers === null) return { ...vacio, reemplazos: {} }
  let req = [...new Set(Object.values(pers).flatMap((m) => Object.values(m || {})
    .flatMap((c) => [c && c.fuente, ...Object.values((c && c.por_talle) || {}).map((pt) => (pt || {}).fuente)])
    .filter(Boolean)))].sort(ordenPy)
  if (info.camino_a && !Object.keys(pers).length) {
    // sin placeholders de personalización: las fuentes que pide el diseño (lo que el servidor
    // sacaba con `fuentes_requeridas_arte`; la validación del arte ya las trae calculadas)
    const d = (info.disenos || []).find((x) => x.id === (diseno || 'principal')) || {}
    req = Object.keys(((d.validacion || {}).fuentes_requeridas) || {}).sort(ordenPy)
  }
  const originales = {}
  for (const f of req) { const e = resolverFuente(f, todas, {}); originales[f] = e ? e.interno : null }
  let faltantes = req.filter((f) => !resolverFuente(f, todas, alias)).sort(ordenPy)
  const campos = []
  if (Object.keys(pers).length) {
    // `_campos_de_fuentes`: una fuente falta sólo si algún campo que la usa no tiene una elegida
    // para él y el resolvedor tampoco la encuentra
    const faltan = new Set()
    const por = fuentesPorCampo(pers)
    for (const campo of [...por.keys()].sort(ordenPy)) {
      const fs = por.get(campo)
      const clave = claveFuenteCampo(campo)
      const elegida = alias[clave] || null
      const e0 = fs.length ? resolverFuente(fs[0], todas, {}) : null
      if (!elegida) for (const f of fs) if (!resolverFuente(f, todas, alias)) faltan.add(f)
      campos.push({ campo, clave, fuentes: fs, original: e0 ? e0.interno : null, elegida,
                    por_fuente: (fs.find((f) => alias[f]) && alias[fs.find((f) => alias[f])]) || null })
    }
    faltantes = [...faltan].sort(ordenPy)
  }
  return { ok: true, requeridas: req, faltantes, reemplazables: req, originales, campos, catalogo, reemplazos: alias }
}

// `str.isprintable()` de Python: fuera los de control, formato, sin asignar y separadores (menos el
// espacio común).
const noImprimible = (ch) => ch !== ' ' && /^[\p{C}\p{Z}]$/u.test(ch)

/**
 * `GET /api/pedido/fuente_chars`, armado acá: los caracteres que TODAS las tipografías con las que
 * se estampan los campos pueden DIBUJAR de verdad (estar en el cmap no alcanza: un glifo con los
 * datos rotos revienta recién al estampar). Devuelve `{ok, preparando?, chars, fuentes, faltantes}`.
 */
export async function fuenteCharsLocal({ pid, rutaApi }) {
  const info = await infoMolde(pid, rutaApi, null)
  if (info.camino_b && preparandoB(info)) return { ok: false, preparando: true, chars: '', fuentes: [], faltantes: [] }
  const pers = persDe(info, 'principal') || {}
  const todas = (info.fuentes || {}).catalogo || []
  const alias = (info.fuentes || {}).alias || {}
  const pares = []
  for (const m of Object.values(pers)) {
    for (const [campo, c] of Object.entries(m || {})) {
      if (!c) continue
      const fs = info.camino_b ? [c.fuente, ...Object.values(c.por_talle || {}).map((pt) => (pt || {}).fuente)] : [c.fuente]
      for (const f of fs) if (f) pares.push([campo, f])
    }
  }
  // la tipografía de CADA CAMPO (la elegida para el campo, si hay): es con la que se estampa
  const elegidas = new Map()
  for (const [campo, f] of pares) {
    const [fc, pc] = fuenteDeCampo(campo, f, alias)
    elegidas.set(fc, (elegidas.get(fc) || false) || pc)
  }
  const fuentes = [...elegidas.keys()].sort(ordenPy)
  const sets = [], ok = [], falta = []
  for (const f of fuentes) {
    const e = resolverFuente(f, todas, elegidas.get(f) ? {} : alias)
    if (!e) { falta.push(f); continue }
    try {
      const url = rutaApi(`/api/fuente/archivo/${encodeURIComponent(e.archivo)}` + (e.propia ? `?pid=${encodeURIComponent(pid)}` : ''))
      const bytes = await traerConCache(`fuente|${e.hash}|${e.archivo}`, url)
      const fc = new FuenteCurvas(bytes.slice(), null)
      const s = new Set()
      for (const cp of fc.cmap.keys()) {
        const ch = String.fromCodePoint(cp)
        try { fc._glifo(ch); s.add(ch) } catch { /* mapeado pero sin dibujo: no sirve */ }
      }
      sets.push(s); ok.push(f)
    } catch {
      falta.push(f)
    }
  }
  if (!sets.length) return { ok: false, chars: '', fuentes, faltantes: falta }
  let inter = sets[0]
  for (const s of sets.slice(1)) inter = new Set([...inter].filter((c) => s.has(c)))
  const chars = [...inter].filter((c) => !noImprimible(c)).sort(ordenPy).join('')
  return { ok: true, chars, fuentes: ok, faltantes: falta }
}
