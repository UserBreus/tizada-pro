// EL CATÁLOGO DE TIPOGRAFÍAS, RESUELTO EN EL NAVEGADOR — PLAN_NAVEGADOR.md, etapa 3.
//
// El servidor sigue siendo el que TIENE las tipografías (`/api/fuentes` → `catalogo`,
// `/api/fuente/archivo/<archivo>` → el .ttf/.otf); acá se elige cuál usar con la misma regla que
// `motor_pedido.resolver_fuente` (la elección del pedido manda; una coincidencia exacta le gana a
// una parecida) y se abre con `texto/curvas.js`. Cada archivo se baja una vez.

/** `_norm` de motor_pedido: sólo alfanuméricos, sin «regular» ni «mt». */
export function normFuente(n) {
  let s = ''
  for (const ch of String(n).toLowerCase()) if (/[\p{L}\p{N}]/u.test(ch)) s += ch
  return s.replace(/regular/g, '').replace(/mt/g, '')
}

/**
 * `resolver_fuente`: el nombre PostScript → la entrada del catálogo (`{interno, archivo, …}`) o
 * null. `catalogo` = lista en el ORDEN del servidor (las del pedido primero); `alias` = los
 * reemplazos elegidos en el pedido.
 */
export function resolverFuente(nombrePs, catalogo, alias = {}) {
  nombrePs = (alias || {})[nombrePs] || nombrePs
  for (const f of catalogo) if ((f.interno || '') === nombrePs) return f
  const objetivo = normFuente(nombrePs)
  for (const f of catalogo) if (normFuente(f.interno || '') === objetivo) return f
  for (const f of catalogo) {
    const n = normFuente(f.interno || '')
    if (objetivo.includes(n) || n.includes(objetivo)) return f
  }
  return null
}

/**
 * Un abridor de tipografías con caché: `abrir(nombrePs, {sinAlias})` → `FuenteCurvas`.
 *   · `catalogo`, `alias` — como arriba;
 *   · `traer(entrada)` — devuelve los bytes (Uint8Array) del archivo de esa entrada del catálogo;
 *   · `FuenteCurvas` — la clase de `texto/curvas.js`;
 *   · `respaldo` — el nombre de la tipografía de respaldo (Anton Regular), como en el motor.
 * Es la traducción de `fuente(nombre_ps)` de `generar_pedido`: sin la fuente en el catálogo se
 * estampa con Anton Regular; sin Anton, error claro.
 */
export function crearAbridor({ catalogo, alias = {}, traer, FuenteCurvas, respaldo = 'Anton Regular' }) {
  const bytes = new Map()             // archivo → Uint8Array (bajado una vez)
  const sueltas = new Map()           // archivo → FuenteCurvas SIN respaldo (para ser respaldo de otras)
  const conRespaldo = new Map()       // clave → FuenteCurvas con respaldo
  const cargar = async (entrada) => {
    if (!bytes.has(entrada.archivo)) bytes.set(entrada.archivo, await traer(entrada))
  }
  const precargar = async (nombres) => {
    // baja todo lo que se va a usar ANTES de estampar (el estampado es sincrónico)
    const entradas = new Set()
    const r = resolverFuente(respaldo, catalogo, {})
    if (r) entradas.add(r)
    for (const n of nombres) {
      const e = resolverFuente(n, catalogo, alias) || r
      if (e) entradas.add(e)
    }
    await Promise.all([...entradas].map(cargar))
  }
  const suelta = (entrada) => {
    if (!sueltas.has(entrada.archivo)) {
      const b = bytes.get(entrada.archivo)
      if (!b) throw new Error(`la tipografía «${entrada.interno}» no se bajó todavía (precargar)`)
      sueltas.set(entrada.archivo, new FuenteCurvas(b, null))
    }
    return sueltas.get(entrada.archivo)
  }
  const abrir = (nombrePs, { sinAlias = false } = {}) => {
    const clave = (sinAlias ? '!' : '') + nombrePs
    if (conRespaldo.has(clave)) return conRespaldo.get(clave)
    let entrada = resolverFuente(nombrePs, catalogo, sinAlias ? {} : alias)
    if (!entrada) entrada = resolverFuente(respaldo, catalogo, {})
    if (!entrada) throw new Error(`tipografía '${nombrePs}' no está en el catálogo (ni el reemplazo temporal ${respaldo})`)
    const b = bytes.get(entrada.archivo)
    if (!b) throw new Error(`la tipografía «${entrada.interno}» no se bajó todavía (precargar)`)
    // como en `generar_pedido`: toda fuente lleva a Anton de respaldo, salvo Anton misma
    const r = resolverFuente(respaldo, catalogo, {})
    const fr = r && r.archivo !== entrada.archivo && bytes.has(r.archivo) ? suelta(r) : null
    const f = new FuenteCurvas(b, fr)
    conRespaldo.set(clave, f)
    return f
  }
  return { abrir, precargar }
}
