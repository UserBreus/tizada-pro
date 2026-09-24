// LO GUARDADO EN EL NAVEGADOR (IndexedDB): archivos que se bajan una vez y se reusan — las mesas
// desplegadas de un molde, las tipografías, los dibujos ya hechos. Es el «espacio local» de
// PLAN_NAVEGADOR.md. Todo es best-effort: en una ventana privada o con el espacio lleno se sigue
// sin caché, nunca se corta nada.

import { bytesBajados } from './monitor.js'

const DB = 'tizada-motor'
const STORE = 'archivos'

// 🔴 LAS CLAVES, EN UN SOLO LUGAR (2026-09-23). La descarga de fondo de todos los moldes
// (`bajarMoldes.js`) guarda cada archivo bajo la MISMA clave con la que después lo pide el motor;
// si cada módulo la armara a mano, alcanza con una coma distinta para que el motor no lo encuentre
// y lo vuelva a bajar. El sello viene del servidor (`_sello_archivo`: tamaño + fecha en µs).
const _s = (sello) => (sello || []).join(',')
export const claveDe = {
  /** el archivo del molde (camino A); `cual` = 'vigente' (lo que usa el motor) u 'original' */
  plantilla: (pid, sello, cual = 'vigente') => `plantilla-${cual}|${pid}|${_s(sello)}`,
  /** una mesa desplegada de un molde con el diseño adentro (camino B): su PDF o su índice */
  mesaPdf: (pid, mesa, sello) => `${pid}|m${mesa}.pdf|${_s(sello)}`,
  mesaJson: (pid, mesa, sello) => `${pid}|m${mesa}.json|${_s(sello)}`,
  /** el arte (vigente) de un diseño; `diseno` = 'principal' o el id del diseño */
  arte: (pid, diseno, sello) => `arte|${pid}|${diseno || 'principal'}|${_s(sello)}`,
}
/** De dónde se baja cada uno (sin el prefijo de la app: pasarlo por `rutaApi`). */
export const urlDe = {
  plantilla: (pid, cual = 'vigente') => `/api/productos/${encodeURIComponent(pid)}/descargar_plantilla${cual === 'vigente' ? '?cual=vigente' : ''}`,
  mesa: (pid, mesa, ext) => `/api/productos/${encodeURIComponent(pid)}/desplegado/m${mesa}.${ext}`,
  arte: (pid, diseno) => `/api/productos/${encodeURIComponent(pid)}/arte_archivo` +
    (diseno && diseno !== 'principal' ? `?diseno=${encodeURIComponent(diseno)}` : ''),
}

// Una sola conexión: antes cada lectura abría una nueva y ninguna se cerraba.
let _db = null
function abrirDb() {
  if (!_db) {
    _db = new Promise((ok, no) => {
      const p = indexedDB.open(DB, 1)
      p.onupgradeneeded = () => { const db = p.result; if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE) }
      p.onsuccess = () => {
        const db = p.result
        // otra pestaña con una versión nueva de la base: se suelta para no trabarla
        db.onversionchange = () => { try { db.close() } catch { /* nada */ } _db = null }
        db.onclose = () => { _db = null }
        ok(db)
      }
      p.onerror = () => no(p.error || new Error('sin guardado'))
    })
    _db.catch(() => { _db = null })
  }
  return _db
}

/** Los bytes guardados bajo `clave`, o null. */
export async function leerCache(clave) {
  try {
    const db = await abrirDb()
    const v = await new Promise((ok) => {
      const p = db.transaction(STORE).objectStore(STORE).get(clave)
      p.onsuccess = () => ok(p.result || null)
      p.onerror = () => ok(null)
    })
    if (!v) return null
    const u8 = new Uint8Array(v instanceof Blob ? await v.arrayBuffer() : v)
    return u8.length ? u8 : null            // un guardado vacío (ver `guardarCache`) no es un acierto
  } catch {
    return null
  }
}

/** ¿Hay algo guardado bajo `clave`? Sin leerlo (un molde pesa cientos de MB). */
export async function tieneCache(clave) {
  try {
    const db = await abrirDb()
    return await new Promise((ok) => {
      const p = db.transaction(STORE).objectStore(STORE).count(clave)
      p.onsuccess = () => ok(p.result > 0)
      p.onerror = () => ok(false)
    })
  } catch {
    return false
  }
}

/** Todas las claves guardadas (para soltar las versiones viejas). */
export async function clavesCache() {
  try {
    const db = await abrirDb()
    return await new Promise((ok) => {
      const p = db.transaction(STORE).objectStore(STORE).getAllKeys()
      p.onsuccess = () => ok((p.result || []).map(String))
      p.onerror = () => ok([])
    })
  } catch {
    return []
  }
}

/** Borra esas claves del guardado del navegador (sólo lo guardado acá; nada del servidor). */
export async function borrarCache(claves) {
  if (!claves || !claves.length) return
  try {
    const db = await abrirDb()
    await new Promise((ok) => {
      const t = db.transaction(STORE, 'readwrite')
      const st = t.objectStore(STORE)
      for (const k of claves) st.delete(k)
      t.oncomplete = t.onerror = t.onabort = () => ok()
    })
  } catch { /* nada */ }
}

async function guardarBlob(clave, blob) {
  if (!blob || !blob.size) return
  try {
    const db = await abrirDb()
    await new Promise((ok) => {
      const t = db.transaction(STORE, 'readwrite')
      t.objectStore(STORE).put(blob, clave)
      t.oncomplete = t.onerror = t.onabort = () => ok()
    })
  } catch { /* sin caché */ }
}

/** Guarda `bytes` (Uint8Array) bajo `clave`. */
export async function guardarCache(clave, bytes) {
  // 🔴 el Blob se arma AHORA, antes de cualquier `await`: quien llama suele TRANSFERIR `bytes.buffer`
  // a un hilo apenas recibe los bytes, y un Blob armado después quedaba VACÍO (se guardaban 0
  // bytes y la próxima carga fallaba con «no objects found»)
  return guardarBlob(clave, new Blob([bytes]))
}

// UNA descarga por clave aunque la pidan dos a la vez (la descarga de fondo de los moldes y el
// motor que justo necesita ese molde): el segundo espera al primero en vez de bajarlo de nuevo.
// Se suelta recién cuando quedó GUARDADO: si no, entre que termina la descarga y termina de
// escribirse en el disco, otro pedido no lo encontraba en ningún lado y lo volvía a bajar.
const _enVuelo = new Map()          // clave → Promise<Blob>

function _bajar(clave, url) {
  const ya = _enVuelo.get(clave)
  if (ya) return ya
  const soltar = () => { if (_enVuelo.get(clave) === p) _enVuelo.delete(clave) }
  const p = (async () => {
    const r = await fetch(url)
    if (!r.ok) throw new Error(`no se pudo bajar ${url} (${r.status})`)
    const blob = await r.blob()
    bytesBajados(blob.size)
    guardarBlob(clave, blob).then(soltar, soltar)
    return blob
  })()
  _enVuelo.set(clave, p)
  p.catch(soltar)
  return p
}

/** Baja `url` (o lo toma del guardado) y lo deja guardado bajo `clave`. Devuelve Uint8Array. */
export async function traerConCache(clave, url) {
  const hit = await leerCache(clave)
  if (hit) return hit
  // una copia PROPIA por pedido: quien llama suele transferir el buffer a un hilo
  const blob = await _bajar(clave, url)
  return new Uint8Array(await blob.arrayBuffer())
}

/** Deja `url` guardado bajo `clave` sin devolverlo. `true` si hubo que bajarlo. */
export async function bajarAlCache(clave, url) {
  if (await tieneCache(clave)) return false
  await _bajar(clave, url)
  return true
}

/** Texto → base64 (para `data:image/svg+xml;base64,`), sin reventar con textos largos. */
export function base64DeTexto(texto) {
  const bytes = new TextEncoder().encode(texto)
  let bin = ''
  const paso = 0x8000
  for (let i = 0; i < bytes.length; i += paso) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + paso))
  return btoa(bin)
}
