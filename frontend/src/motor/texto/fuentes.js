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
 * `nombres_fuente` de motor_pedido: los nombres de la tabla `name` de la tipografía,
 * `{familia, estilo, completo, ps}` ('' lo que no se pueda leer). El `completo` (familia + estilo)
 * distingue los estilos de una familia; el `ps` es el que escribe Illustrator en el arte.
 */
export function nombresFuente(bytes) {
  const out = { familia: '', estilo: '', completo: '', ps: '' }
  try {
    const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
    const nTablas = dv.getUint16(4)
    let tabla = -1
    for (let i = 0; i < nTablas; i++) {
      const o = 12 + 16 * i
      if (String.fromCharCode(dv.getUint8(o), dv.getUint8(o + 1), dv.getUint8(o + 2), dv.getUint8(o + 3)) === 'name') {
        tabla = dv.getUint32(o + 8)
        break
      }
    }
    if (tabla < 0) return out
    const cuenta = dv.getUint16(tabla + 2), base = dv.getUint16(tabla + 4)
    const mejor = new Map()            // nameID → [prioridad, texto]; menor = mejor
    const utf16 = (o, n) => { let s = ''; for (let k = 0; k + 1 < n; k += 2) s += String.fromCharCode(dv.getUint16(o + k)); return s }
    const latin = (o, n) => { let s = ''; for (let k = 0; k < n; k++) s += String.fromCharCode(dv.getUint8(o + k)); return s }
    for (let i = 0; i < cuenta; i++) {
      const o = tabla + 6 + 12 * i
      const plat = dv.getUint16(o), enc = dv.getUint16(o + 2), idioma = dv.getUint16(o + 4)
      const nid = dv.getUint16(o + 6), largo = dv.getUint16(o + 8), off = dv.getUint16(o + 10)
      if (![1, 2, 4, 6, 16, 17].includes(nid)) continue
      const ini = tabla + base + off
      let prio, txt
      if (plat === 3 && idioma === 0x409) { prio = 0; txt = utf16(ini, largo) }
      else if (plat === 0 || plat === 3) { prio = 1; txt = utf16(ini, largo) }
      else if (plat === 1 && enc === 0) { prio = 2; txt = latin(ini, largo) }   // (Python: mac_roman; los nombres son ASCII)
      else continue
      txt = txt.replace(/\u0000/g, '').trim()
      if (txt && (!mejor.has(nid) || prio < mejor.get(nid)[0])) mejor.set(nid, [prio, txt])
    }
    const g = (k) => (mejor.get(k) || [0, ''])[1]
    out.familia = g(16) || g(1)
    out.estilo = g(17) || g(2)
    out.completo = g(4) || [out.familia, out.estilo].filter(Boolean).join(' ')
    out.ps = g(6)
  } catch { /* fuente rara: sin nombres */ }
  return out
}

/** `identidad_fuente`: con qué se decide que dos tipografías son LA MISMA (los estilos de una familia no). */
export function identidadFuente(info) {
  return normFuente((info || {}).completo || (info || {}).interno || '')
}

/**
 * `resolver_fuente`: el nombre PostScript → la entrada del catálogo (`{interno, archivo, …}`) o
 * null. `catalogo` = lista en el ORDEN del servidor (las del pedido primero); `alias` = los
 * reemplazos elegidos en el pedido.
 */
export function resolverFuente(nombrePs, catalogo, alias = {}) {
  nombrePs = (alias || {})[nombrePs] || nombrePs
  // FAMILIAS (2026-10-01): el PostScript (`ps`) y el nombre completo separan los estilos de una
  // familia que el `interno` de MuPDF (cortado en 31 letras) confunde. Después del interno en cada
  // vuelta, como `resolver_fuente`.
  for (const f of catalogo) if ((f.interno || '') === nombrePs) return f
  for (const f of catalogo) if (nombrePs && (f.ps === nombrePs || f.completo === nombrePs)) return f
  const objetivo = normFuente(nombrePs)
  for (const f of catalogo) if (normFuente(f.interno || '') === objetivo) return f
  for (const f of catalogo) {
    if (objetivo && (normFuente(f.ps || '') === objetivo || normFuente(f.completo || '') === objetivo)) return f
  }
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
      // …y la ORIGINAL del diseño aunque haya reemplazo: con ella se mide a qué altura van las
      // letras de la que la reemplaza (`tamanoMismaAltura`, como `fuente(…, sin_alias=True)`)
      const e0 = resolverFuente(n, catalogo, {})
      if (e0) entradas.add(e0)
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
    f._entrada = entrada                 // de qué archivo salió (`_ruta` en Python)
    conRespaldo.set(clave, f)
    return f
  }
  // la entrada del catálogo de la tipografía ORIGINAL del diseño, sin reemplazos (o null): para
  // saber si se está estampando con otra (`_rutas_originales` en Python)
  abrir.original = (nombrePs) => (nombrePs ? resolverFuente(nombrePs, catalogo, {}) : null)
  return { abrir, precargar }
}
