// TODOS LOS MOLDES EN ESTA PC — 2026-09-23.
//
// Pedido del usuario: «actualizá nuestro sistema para que baje todos los moldes». Apenas alguien
// entra, esta computadora baja DE FONDO todos los moldes que puede usar y los guarda (IndexedDB,
// `cache.js`) bajo la MISMA clave con la que después los pide el motor: al abrir un molde, armar
// el arte o generar la tizada ya están acá y no se espera ninguna descarga.
//
// - El servidor sólo LISTA (`/api/moldes/para_bajar`: tamaño + fecha de cada archivo).
// - Se guarda POR VERSIÓN: la próxima vez se baja sólo lo que cambió (un molde editado, uno nuevo),
//   y la versión vieja de ESE molde se borra de la PC para no llenar el disco.
// - De a un archivo, los moldes chicos primero: con la subida del servidor como cuello de botella,
//   bajar varios a la vez no termina antes y le quita ancho a lo que el usuario está haciendo.
// - Si el motor pide un molde que justo se está bajando, espera a esa misma descarga
//   (`cache.js` → `_enVuelo`): nunca se baja dos veces.
// - Nada de esto frena la pantalla: es un aviso chico abajo a la izquierda, no un cartel que tapa.
import { bajarAlCache, tieneCache, clavesCache, borrarCache, claveDe, urlDe } from './cache.js'

let _estado = {
  fase: 'nada',          // 'nada' | 'revisando' | 'bajando' | 'listo' | 'error'
  moldes: 0,             // cuántos moldes hay para tener en esta PC
  moldesListos: 0,       // cuántos ya están enteros acá
  bytesTotal: 0,         // lo que faltaba bajar al empezar esta pasada
  bytesHechos: 0,
  actual: null,          // el molde que se está bajando ahora
  fallidos: [],          // [{nombre, error}] de esta pasada
  sinEspacio: false,     // el navegador no tiene lugar para todos
  mbEnPc: 0,             // lo que ocupan en esta PC los moldes que ya están
}
const _oyentes = new Set()
let _corriendo = null
let _otraVez = false

export function estadoDescarga() { return _estado }
/** `fn(estado)` en cada cambio. Devuelve la función para dejar de escuchar. */
export function escucharDescarga(fn) { _oyentes.add(fn); return () => { _oyentes.delete(fn) } }
/** «Cerrar» en el aviso de lo que no se pudo bajar (se vuelve a intentar en la próxima pasada). */
export function cerrarAvisoDescarga() { avisar({ fallidos: [], sinEspacio: false, fase: _estado.fase === 'error' ? 'listo' : _estado.fase }) }
function avisar(parcial) {
  _estado = { ..._estado, ...parcial }
  for (const f of _oyentes) { try { f(_estado) } catch { /* nada */ } }
}

/**
 * Baja lo que falte. Si ya hay una pasada corriendo, se anota otra para cuando termine (algo pudo
 * cambiar en el medio) y devuelve la que corre.
 */
export function bajarTodosLosMoldes(rutaApi = (x) => x) {
  if (typeof indexedDB === 'undefined') return Promise.resolve()
  if (_corriendo) { _otraVez = true; return _corriendo }
  _corriendo = (async () => {
    try {
      do { _otraVez = false; await _pasada(rutaApi) } while (_otraVez)
    } finally { _corriendo = null }
  })()
  return _corriendo
}

/** Lo que hay que tener de cada molde, con la clave del motor. */
function archivosDe(m) {
  const out = []
  for (const a of m.archivos || []) {
    if (a.tipo === 'plantilla') {
      out.push({ clave: claveDe.plantilla(m.id, a.sello), url: urlDe.plantilla(m.id), bytes: a.bytes || 0 })
    } else if (a.tipo === 'mesa') {
      out.push({ clave: claveDe.mesaJson(m.id, a.mesa, a.sello), url: urlDe.mesa(m.id, a.mesa, 'json'), bytes: a.bytes_json || 0 })
      out.push({ clave: claveDe.mesaPdf(m.id, a.mesa, a.sello), url: urlDe.mesa(m.id, a.mesa, 'pdf'), bytes: a.bytes || 0 })
    }
  }
  return out
}

/** ¿Esta clave es de un archivo de ESTE molde que se baja acá (cualquier versión)? */
function esDelMolde(clave, pid) {
  return clave.startsWith(`plantilla-vigente|${pid}|`) || new RegExp(`^${pid.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\|m\\d+\\.(pdf|json)\\|`).test(clave)
}

async function _pasada(rutaApi) {
  avisar({ fase: 'revisando', fallidos: [], sinEspacio: false, actual: null })
  let lista
  try {
    const r = await fetch(rutaApi('/api/moldes/para_bajar'))
    const d = await r.json().catch(() => ({}))
    if (!r.ok) throw new Error(d.error || `el servidor contestó ${r.status}`)
    lista = d.moldes || []
  } catch (e) {
    avisar({ fase: 'error', fallidos: [{ nombre: 'la lista de moldes', error: e.message }] })
    return
  }

  // qué falta de cada molde (sin leer lo guardado: sólo si está)
  const moldes = []
  let mbEnPc = 0
  for (const m of lista) {
    const arch = archivosDe(m)
    const faltan = []
    for (const a of arch) {
      if (await tieneCache(a.clave)) mbEnPc += a.bytes / 1048576
      else faltan.push(a)
    }
    moldes.push({ m, arch, faltan, bytes: faltan.reduce((s, a) => s + a.bytes, 0) })
  }
  // los chicos primero: en segundos quedan listos casi todos, y el pesado sigue de fondo
  moldes.sort((a, b) => a.bytes - b.bytes)
  const bytesTotal = moldes.reduce((s, x) => s + x.bytes, 0)

  // ¿entra? El navegador da un cupo por sitio; si no alcanza para todo, se baja lo que entre
  // (en orden, los chicos primero) y se avisa. Lo que no entra se baja igual cuando se use.
  let libre = Infinity
  try {
    if (navigator.storage && navigator.storage.estimate) {
      const e = await navigator.storage.estimate()
      if (e && e.quota) libre = e.quota * 0.9 - (e.usage || 0)
    }
  } catch { /* sin dato: se intenta */ }

  let listos = moldes.filter((x) => !x.faltan.length).length
  avisar({ fase: bytesTotal ? 'bajando' : 'listo', moldes: moldes.length, moldesListos: listos,
           bytesTotal, bytesHechos: 0, mbEnPc: Math.round(mbEnPc) })

  const fallidos = []
  let hechos = 0
  let sinEspacio = false
  for (const x of moldes) {
    if (!x.faltan.length) continue
    if (x.bytes > libre) { sinEspacio = true; continue }
    avisar({ actual: x.m.nombre || x.m.id })
    let ok = true
    for (const a of x.faltan) {
      try {
        await bajarAlCache(a.clave, rutaApi(a.url))
        libre -= a.bytes
        mbEnPc += a.bytes / 1048576
      } catch (e) {
        ok = false
        fallidos.push({ nombre: x.m.nombre || x.m.id, error: e.message })
        break                    // un molde a medias no sirve: se sigue con el próximo
      }
      hechos += a.bytes
      avisar({ bytesHechos: hechos, mbEnPc: Math.round(mbEnPc) })
    }
    if (ok) { listos++; avisar({ moldesListos: listos }) }
  }

  // las versiones VIEJAS de estos moldes ya no las pide nadie: fuera de la PC. Sólo de los moldes
  // de la lista (los de otro usuario que haya usado esta misma PC no se tocan).
  try {
    const quiero = new Set(moldes.flatMap((x) => x.arch.map((a) => a.clave)))
    const viejas = (await clavesCache()).filter((k) => !quiero.has(k) && moldes.some((x) => esDelMolde(k, x.m.id)))
    await borrarCache(viejas)
  } catch { /* nada: es limpieza */ }

  avisar({ fase: fallidos.length ? 'error' : 'listo', actual: null, fallidos, sinEspacio, mbEnPc: Math.round(mbEnPc) })
}
