// LO GUARDADO EN EL NAVEGADOR (IndexedDB): archivos que se bajan una vez y se reusan — las mesas
// desplegadas de un molde, las tipografías, los dibujos ya hechos. Es el «espacio local» de
// PLAN_NAVEGADOR.md. Todo es best-effort: en una ventana privada o con el espacio lleno se sigue
// sin caché, nunca se corta nada.

const DB = 'tizada-motor'
const STORE = 'archivos'

function abrirDb() {
  return new Promise((ok, no) => {
    const p = indexedDB.open(DB, 1)
    p.onupgradeneeded = () => { const db = p.result; if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE) }
    p.onsuccess = () => ok(p.result)
    p.onerror = () => no(p.error || new Error('sin guardado'))
  })
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

/** Guarda `bytes` (Uint8Array) bajo `clave`. */
export async function guardarCache(clave, bytes) {
  // 🔴 el Blob se arma AHORA, antes de cualquier `await`: quien llama suele TRANSFERIR `bytes.buffer`
  // a un hilo apenas recibe los bytes, y un Blob armado después quedaba VACÍO (se guardaban 0
  // bytes y la próxima carga fallaba con «no objects found»)
  const blob = new Blob([bytes])
  if (!blob.size) return
  try {
    const db = await abrirDb()
    await new Promise((ok) => {
      const t = db.transaction(STORE, 'readwrite')
      t.objectStore(STORE).put(blob, clave)
      t.oncomplete = t.onerror = t.onabort = () => ok()
    })
  } catch { /* sin caché */ }
}

/** Baja `url` (o lo toma del guardado) y lo deja guardado bajo `clave`. Devuelve Uint8Array. */
export async function traerConCache(clave, url) {
  const hit = await leerCache(clave)
  if (hit) return hit
  const r = await fetch(url)
  if (!r.ok) throw new Error(`no se pudo bajar ${url} (${r.status})`)
  const bytes = new Uint8Array(await r.arrayBuffer())
  guardarCache(clave, bytes)
  return bytes
}

/** Texto → base64 (para `data:image/svg+xml;base64,`), sin reventar con textos largos. */
export function base64DeTexto(texto) {
  const bytes = new TextEncoder().encode(texto)
  let bin = ''
  const paso = 0x8000
  for (let i = 0; i < bytes.length; i += paso) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + paso))
  return btoa(bin)
}
