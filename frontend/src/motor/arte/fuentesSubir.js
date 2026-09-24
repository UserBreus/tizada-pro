// SUBIR UNA TIPOGRAFÍA: LO QUE SE CALCULA, EN ESTA COMPUTADORA — 2026-09-22.
//
// 🔴 POR QUÉ: «el servidor será sólo para sostener el sistema y la base». Al subir una tipografía el
// servidor la abría con PyMuPDF para saber su nombre, probaba glifo por glifo cuáles se pueden
// dibujar, buscaba si chocaba con otra del catálogo y, de yapa, volvía a validar el arte entero.
// Acá se hace todo eso (`obrero.worker.js` → `fuente_analizar` / `arte_revalidar`) y el servidor
// sólo guarda el archivo con lo que se le dice.
import { enHiloSuelto } from '../hiloSuelto.js'
import { traerConCache, claveDe, urlDe } from '../cache.js'
import { resolverFuente } from '../texto/fuentes.js'

async function json(url, opts) {
  const r = await fetch(url, opts)
  const d = await r.json().catch(() => ({}))
  if (!r.ok) { const e = new Error(d.error || `${url}: ${r.status}`); e.datos = d; throw e }
  return d
}

/**
 * Lo que el servidor necesita saber de la tipografía `archivo` (File) antes de guardarla:
 * `{interno, sin_contorno, choca_con}` como campos del formulario. `pid` = el molde (su catálogo);
 * `destino` = 'sistema' | 'pedido'.
 */
export async function analizarFuente(archivo, { pid, destino = 'sistema', rutaApi }) {
  const ctx = pid ? await json(rutaApi(`/api/productos/${encodeURIComponent(pid)}/arte_contexto`)).catch(() => null) : null
  const todas = ((ctx || {}).fuentes || {}).catalogo || []
  // choca contra las de la MISMA carpeta a la que va (como `alta_fuente(ruta, carpeta)`)
  const catalogo = todas.filter((c) => (destino === 'pedido' ? c.propia : !c.propia))
  const bytes = new Uint8Array(await archivo.arrayBuffer())
  const nombre = 'subida_' + String(archivo.name || 'fuente').split(/[\\/]/).pop()
  const r = await enHiloSuelto('fuente_analizar', { bytes, catalogo, destino: nombre }, [bytes.buffer], 'fuente')
  return { ...r, catalogoAntes: todas, nombreArchivo: nombre }
}

/** Los campos del formulario de subida con lo analizado acá. */
export function adjuntarAnalisis(fd, an) {
  fd.append('interno', an.interno || '')
  fd.append('sin_contorno', JSON.stringify(an.sin_contorno || []))
  fd.append('choca_con', JSON.stringify(an.choca_con || null))
}

/**
 * Qué reemplazos del pedido hay que soltar porque la tipografía recién subida ES la original
 * (cargar su archivo = volver a ella): los que ahora resuelven, SIN alias, a la nueva.
 */
export function aliasQuitados(an, reemplazos, destino) {
  const nueva = { interno: an.interno, archivo: an.nombreArchivo, propia: destino === 'pedido' }
  // en el orden del catálogo del servidor: las del sistema y después las del molde, cada una al
  // final de su carpeta (el archivo nuevo reemplaza al viejo del mismo nombre)
  const resto = (an.catalogoAntes || []).filter((c) => !(c.archivo === nueva.archivo && !!c.propia === nueva.propia))
  const sis = resto.filter((c) => !c.propia), prop = resto.filter((c) => c.propia)
  const cat = nueva.propia ? [...sis, ...prop, nueva] : [...sis, nueva, ...prop]
  return Object.keys(reemplazos || {}).filter((k) => {
    const e = resolverFuente(k, cat, {})
    return e && e.archivo === nueva.archivo && !!e.propia === nueva.propia
  })
}

/**
 * Vuelve a validar el arte PRINCIPAL del molde con el catálogo del sistema (lo que `/api/fuente`
 * hacía después de guardar la tipografía) y guarda el resultado. Sin arte: no hace nada.
 */
export async function revalidarArte({ pid, rutaApi }) {
  if (!pid) return
  const info = await json(rutaApi(`/api/productos/${encodeURIComponent(pid)}/motor_b`))
  if (!info.camino_a) return
  const d = (info.disenos || []).find((x) => x.id === 'principal')
  if (!d) return
  const modo = (d.validacion || {}).modo === 'separado' ? 'separado' : 'clasico'
  const mapeo = (d.mapeo || {}).mapeo || {}
  if (modo === 'separado' && (!Object.keys(info.registro || {}).length || !Object.keys(mapeo).length)) return
  const ctx = await json(rutaApi(`/api/productos/${encodeURIComponent(pid)}/arte_contexto`))
  // sólo el catálogo del SISTEMA, como el servidor (`validar_arte*(…, FUENTES)`)
  const contexto = { ...ctx, fuentes: { catalogo: ((ctx.fuentes || {}).catalogo || []).filter((c) => !c.propia), alias: {} } }
  const arte = (await traerConCache(`arte|${pid}|${d.id}|${(d.sello || []).join(',')}`,
    rutaApi(`/api/productos/${encodeURIComponent(pid)}/arte_archivo`))).slice()
  let plantilla = null
  if (modo !== 'separado') {
    plantilla = (await traerConCache(claveDe.plantilla(pid, (info.plantilla || {}).sello),
      rutaApi(urlDe.plantilla(pid)))).slice()
  }
  const val = await enHiloSuelto('arte_revalidar', { bytes: arte, modo, contexto, mapeo, plantilla },
    [arte.buffer, ...(plantilla ? [plantilla.buffer] : [])], 'arte')
  await json(rutaApi('/api/arte/validacion'), {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pid, diseno: 'principal', validacion: val }),
  })
}
