// LAS TIPOGRAFÍAS INSTALADAS EN ESTA PC — MAPA 670.
//
// Pedido del usuario (2026-10-12): «que convivan las 2: que se puedan subir pero también te reconozca las
// fuentes de la PC». Chrome y Edge dejan que una página, con PERMISO de la persona, liste las tipografías
// instaladas y lea sus archivos (`window.queryLocalFonts()`, «Local Font Access»). La tizada se arma en esta
// computadora, así que una fuente instalada se puede usar tal cual, sin subirla.
//
// 🔴 CONVIVEN: las fuentes de la PC son la ÚLTIMA fuente del catálogo — primero las subidas al pedido,
// después las del sistema, al final las de la PC (mismo criterio que «las primeras pisan a las últimas»).
// Una tipografía subida siempre gana. Lo de acá sólo SUMA entradas al catálogo; el resolvedor
// (`resolverFuente`) y el estampado no cambian.
//
// Dos usos:
//   · nombres solos (revisar el arte, «qué falta»): `catalogoConPc(catalogo)` suma TODAS las de la PC, sin
//     leer ningún archivo (sólo nombres);
//   · para estampar (vista previa, tizada, caracteres de la planilla): `fuentesConPc(fuentes, nombres)` suma
//     SÓLO las que el diseño pide y el catálogo no tiene, con sus bytes leídos una vez (`bytesPc`). A los
//     hilos del motor les llegan como cualquier otra (`archivo: 'pc:<PostScript>'`).
// Sin el permiso, en otro navegador (Firefox, Safari) o en el robot (Node): no suma nada y todo sigue igual.
import { resolverFuente, nombreInternoMupdf, nombresFuente } from './fuentes.js'

export const PREFIJO_PC = 'pc:'

/** ¿Este navegador puede leer las tipografías instaladas? (Chrome/Edge, en https o localhost) */
export const pcDisponible = () => typeof window !== 'undefined' && typeof window.queryLocalFonts === 'function'

/** El permiso: 'granted' | 'prompt' | 'denied' | 'no' (este navegador no puede). */
export async function permisoPc() {
  if (!pcDisponible()) return 'no'
  try {
    const s = await navigator.permissions.query({ name: 'local-fonts' })
    return s.state
  } catch {
    return 'prompt'
  }
}

let _lista = null          // promesa de la lista de FontData (una vez por sesión)
const _bytes = new Map()   // PostScript → promesa de Uint8Array
const _oyentes = new Set()

/** Avisa cuando la lista de la PC cambia (al dar el permiso): la pantalla vuelve a mirar qué falta. */
export function alCambiarPc(fn) { _oyentes.add(fn); return () => _oyentes.delete(fn) }

/**
 * Las tipografías de la PC (`FontData`). Sin permiso dado, `pedir` lo pide: SÓLO desde un clic de la persona
 * (el navegador muestra su cartel). Sin `pedir` y sin permiso, devuelve [] sin preguntar nada.
 */
export async function listarPc({ pedir = false } = {}) {
  if (!pcDisponible()) return []
  if (!_lista) {
    if (!pedir && (await permisoPc()) !== 'granted') return []
    _lista = window.queryLocalFonts().then((l) => {
      _oyentes.forEach((fn) => { try { fn() } catch { /* nada */ } })
      return l || []
    }).catch(() => { _lista = null; return [] })
  }
  return _lista
}

/** Una tipografía de la PC como entrada del catálogo (sin leer el archivo: el interno, aproximado). */
function entradaDe(fd) {
  return { interno: `${fd.family || ''} ${fd.style || ''}`.trim().slice(0, 31), completo: fd.fullName || '', ps: fd.postscriptName || '',
           archivo: PREFIJO_PC + (fd.postscriptName || fd.fullName || ''), hash: 'pc', pc: true, propia: false }
}

/** NOMBRES SOLOS: el catálogo + todas las de la PC que no estén ya (por PostScript), al final. */
export async function catalogoConPc(catalogo) {
  const pcs = await listarPc()
  if (!pcs.length) return catalogo || []
  const ya = new Set((catalogo || []).map((c) => c.ps).filter(Boolean))
  return [...(catalogo || []), ...pcs.filter((fd) => fd.postscriptName && !ya.has(fd.postscriptName)).map(entradaDe)]
}

/** Los bytes de una tipografía de la PC (por su entrada del catálogo), leídos una vez. */
export async function bytesPc(entrada) {
  const ps = String(entrada.archivo || '').slice(PREFIJO_PC.length)
  if (!_bytes.has(ps)) {
    _bytes.set(ps, (async () => {
      const fd = (await listarPc()).find((x) => x.postscriptName === ps || x.fullName === ps)
      if (!fd) throw new Error(`la tipografía «${ps}» ya no está instalada en esta PC`)
      return soloEsaCara(new Uint8Array(await (await fd.blob()).arrayBuffer()), fd.postscriptName || ps)
    })())
    _bytes.get(ps).catch(() => _bytes.delete(ps))
  }
  return (await _bytes.get(ps)).slice()
}

// COLECCIONES (.ttc): Windows trae muchas tipografías así (Cambria, Sitka, las asiáticas…) y el navegador
// entrega el archivo ENTERO, con varias caras adentro. El estampado (`FuenteCurvas`) y MuPDF leen una sola
// cara por archivo, así que se arma un .ttf/.otf suelto con las tablas de la cara pedida (por su PostScript).
// Las tablas se copian tal cual (vector original): sólo cambia dónde están dentro del archivo.
function caraSuelta(u8, dv, base) {
  const nT = dv.getUint16(base + 4)
  const dir = []
  for (let i = 0; i < nT; i++) {
    const o = base + 12 + 16 * i
    dir.push({ tag: u8.subarray(o, o + 4), chk: dv.getUint32(o + 4), off: dv.getUint32(o + 8), len: dv.getUint32(o + 12) })
  }
  let tam = 12 + 16 * nT
  const pos = dir.map((t) => { const p = tam; tam += (t.len + 3) & ~3; return p })
  const out = new Uint8Array(tam)
  const ov = new DataView(out.buffer)
  out.set(u8.subarray(base, base + 12), 0)
  dir.forEach((t, i) => {
    const o = 12 + 16 * i
    out.set(t.tag, o); ov.setUint32(o + 4, t.chk); ov.setUint32(o + 8, pos[i]); ov.setUint32(o + 12, t.len)
    out.set(u8.subarray(t.off, t.off + t.len), pos[i])
  })
  return out
}

/** Si los bytes son una colección (.ttc), la cara de ese PostScript como archivo suelto; si no, tal cual. */
export function soloEsaCara(u8, ps) {
  if (u8.length < 16 || String.fromCharCode(u8[0], u8[1], u8[2], u8[3]) !== 'ttcf') return u8
  const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength)
  let primera = null
  for (let i = 0, n = dv.getUint32(8); i < n; i++) {
    const cara = caraSuelta(u8, dv, dv.getUint32(12 + 4 * i))
    if (!primera) primera = cara
    const nm = nombresFuente(cara)
    if (ps && (nm.ps === ps || nm.completo === ps)) return cara
  }
  return primera || u8
}

/** La extensión según el contenido: CFF (`OTTO`) → otf; TrueType → ttf. */
export const extensionDe = (u8) => (String.fromCharCode(u8[0], u8[1], u8[2], u8[3]) === 'OTTO' ? 'otf' : 'ttf')

/** Una tipografía de la PC lista para SUBIRLA al sistema (Configuración → Fuentes): un `File` .ttf/.otf. */
export async function archivoPc(ps) {
  const b = await bytesPc({ archivo: PREFIJO_PC + ps })
  const ext = extensionDe(b)
  return new File([b], `${String(ps).replace(/[^\w.-]+/g, '_')}.${ext}`, { type: 'font/' + ext })
}

/** La lista de la PC para mostrarla (sólo nombres; sin permiso, vacía). */
export async function nombresPc() {
  return (await listarPc()).filter((fd) => fd.postscriptName)
    .map((fd) => ({ ps: fd.postscriptName, completo: fd.fullName || '', familia: fd.family || '', estilo: fd.style || '' }))
}

/**
 * EL PERMISO SE PIDE SOLO, AL PRIMER CLIC (pedido del usuario 2026-10-12: «que reconozca las de la PC»).
 * El navegador sólo deja preguntarlo desde un gesto de la persona: se engancha al primer clic de la página
 * y, si todavía no se pidió, aparece el cartelito de Chrome UNA vez. Concedido queda guardado para este
 * sitio y no se vuelve a preguntar; bloqueado, tampoco.
 */
export function pedirAlPrimerClic() {
  if (!pcDisponible() || typeof document === 'undefined') return
  let enCurso = false
  const alClic = () => {
    if (enCurso) return
    enCurso = true
    permisoPc().then(async (s) => {
      if (s !== 'prompt') { document.removeEventListener('pointerdown', alClic, true); return }
      try {
        await window.queryLocalFonts()
        document.removeEventListener('pointerdown', alClic, true)
        _lista = null
        await listarPc()          // ya con permiso: la lista de siempre (y avisa a la pantalla)
      } catch (e) {
        // la persona cerró el cartel (NotAllowedError): no se insiste en cada clic — queda el botón
        // «Usar las de esta PC». Cualquier otra cosa (la pestaña no estaba visible…): se vuelve a probar
        // en el próximo clic (medido 2026-10-12: «Page needs to be visible» se comía el único intento)
        if (e && e.name === 'NotAllowedError') document.removeEventListener('pointerdown', alClic, true)
      } finally { enCurso = false }
    })
  }
  document.addEventListener('pointerdown', alClic, true)
}

/** Las tipografías que pide una personalización `{mesa: {campo: {fuente, por_talle}}}` (nombres PostScript). */
export function fuentesDePers(pers) {
  const out = new Set()
  for (const m of Object.values(pers || {})) {
    for (const c of Object.values(m || {})) {
      if (!c || typeof c !== 'object') continue
      if (c.fuente) out.add(c.fuente)
      for (const pt of Object.values(c.por_talle || {})) if (pt && pt.fuente) out.add(pt.fuente)
    }
  }
  return [...out]
}

/**
 * PARA ESTAMPAR: `fuentes` = {catalogo, alias} del molde; `nombres` = las que pide el diseño. Devuelve
 * {catalogo, alias, pc: Map(archivo → bytes)}: el catálogo + SÓLO las de la PC que hacen falta (las que el
 * catálogo no resuelve), con su nombre interno EXACTO (el de MuPDF, de los bytes) y sus bytes ya leídos.
 */
export async function fuentesConPc(fuentes, nombres) {
  const catalogo = (fuentes && fuentes.catalogo) || []
  const alias = (fuentes && fuentes.alias) || {}
  const pc = new Map()
  // la ORIGINAL que el catálogo no tiene (aunque haya un reemplazo elegido: con ella se mide a qué altura van
  // las letras del reemplazo, `tamanoMismaAltura`); el reemplazo, si hay, sigue mandando al estampar
  const faltan = [...new Set(nombres || [])].filter((n) => n && !resolverFuente(n, catalogo, {}))
  if (!faltan.length) return { catalogo, alias, pc }
  const pcs = (await listarPc()).map(entradaDe)
  if (!pcs.length) return { catalogo, alias, pc }
  const extra = []
  for (const n of faltan) {
    const e = resolverFuente(n, pcs, {})
    if (!e || extra.some((x) => x.archivo === e.archivo)) continue
    try {
      const b = await bytesPc(e)
      extra.push({ ...e, interno: nombreInternoMupdf(b) || e.interno })
      pc.set(e.archivo, b)
    } catch { /* no se pudo leer: queda como faltante */ }
  }
  return { catalogo: [...catalogo, ...extra], alias, pc }
}
