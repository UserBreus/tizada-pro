// LA VISTA DE LAS MESAS, DIBUJADA EN ESTA COMPUTADORA — PLAN_NAVEGADOR.md, etapa 2.
//
// La pantalla pide «la mesa 3 a 1200 px» o «este pedazo a 1600 px» y acá se contesta con una URL
// de imagen, igual que antes contestaba el servidor (`/api/trabajos/<id>/mesa_img`). El archivo se
// baja UNA vez, se guarda en el navegador (IndexedDB) y de ahí en más no se vuelve a pedir nada:
// el zoom, los recortes y la ficha salen de acá.
//
// 🔴 SI NO SE PUEDE (el navegador no da, el archivo es enorme o el servidor tiene la vista
// apagada), se devuelve `null` y la pantalla sigue usando las imágenes del servidor. Nada se
// degrada: el dibujo es el mismo (contrato `verificar_navegador_vista.py`).

import { registrarHilo } from '../monitor.js'

const DB = 'tizada-vista'
const ARCHIVOS = 'archivos'      // huella → bytes del PDF
const DIBUJOS = 'dibujos'        // huella|página|ancho|recorte → PNG

let _config = null

/** ¿El servidor quiere que el navegador dibuje las vistas? (`/api/navegador/config`) */
export async function navegadorDibujaVista(rutaApi = (x) => x) {
  if (_config === null) {
    try {
      const r = await fetch(rutaApi('/api/navegador/config'))
      _config = r.ok ? await r.json() : {}
    } catch {
      _config = {}
    }
  }
  return !!_config.vista
}

/** ¿El servidor quiere que el navegador haga `que` (`vista`, `arte`, `molde`, `tizada`)? */
export async function navegadorHace(que, rutaApi = (x) => x) {
  if (_config === null) await navegadorDibujaVista(rutaApi)
  return !!_config[que]
}

function abrirDb() {
  return new Promise((ok, no) => {
    const p = indexedDB.open(DB, 1)
    p.onupgradeneeded = () => {
      const db = p.result
      if (!db.objectStoreNames.contains(ARCHIVOS)) db.createObjectStore(ARCHIVOS)
      if (!db.objectStoreNames.contains(DIBUJOS)) db.createObjectStore(DIBUJOS)
    }
    p.onsuccess = () => ok(p.result)
    p.onerror = () => no(p.error || new Error('no se pudo abrir el guardado del navegador'))
  })
}

async function leer(store, clave) {
  try {
    const db = await abrirDb()
    return await new Promise((ok) => {
      const p = db.transaction(store).objectStore(store).get(clave)
      p.onsuccess = () => ok(p.result || null)
      p.onerror = () => ok(null)
    })
  } catch {
    return null                     // ventana privada, espacio lleno: se sigue sin caché
  }
}

async function guardar(store, clave, valor) {
  try {
    const db = await abrirDb()
    await new Promise((ok) => {
      const t = db.transaction(store, 'readwrite')
      t.objectStore(store).put(valor, clave)
      t.oncomplete = t.onerror = t.onabort = () => ok()
    })
  } catch { /* sin caché, se dibuja igual */ }
}

/** Una vista abierta: el hilo que dibuja + el PDF ya cargado. */
class Vista {
  constructor(huella) {
    this.huella = huella
    this.obrero = null
    this.pendientes = new Map()
    this.n = 0
    this.urls = new Map()           // clave de dibujo → object URL ya armada
  }

  _obrero() {
    if (this.obrero) return this.obrero
    this.obrero = new Worker(new URL('../vista.worker.js', import.meta.url), { type: 'module' })
    registrarHilo(this.obrero, 'vista')
    this.obrero.onmessage = (e) => {
      const { id, ok, valor, error } = e.data || {}
      const p = this.pendientes.get(id)
      if (!p) return
      this.pendientes.delete(id)
      ok ? p.ok(valor) : p.no(new Error(error))
    }
    // Si el hilo no arranca (navegador viejo, WebAssembly bloqueado) nadie contestaría nunca y la
    // pantalla se quedaría esperando en silencio: se corta acá y dibuja el servidor.
    this.obrero.onerror = (e) => {
      const err = new Error('el hilo que dibuja no arrancó: ' + (e.message || ''))
      for (const p of this.pendientes.values()) p.no(err)
      this.pendientes.clear()
    }
    return this.obrero
  }

  enviar(tipo, datos, transfer) {
    const id = ++this.n
    return new Promise((ok, no) => {
      this.pendientes.set(id, { ok, no })
      this._obrero().postMessage({ id, tipo, datos }, transfer || [])
    })
  }

  async abrir(bytes) {
    const r = await this.enviar('abrir', { bytes }, [bytes.buffer])
    this.medidas = r.medidas
    return r
  }

  /** `recorte` = [cx0, cy0, cx1, cy1] en fracciones, o null. Devuelve una URL para un `<img>`. */
  async dibujo(pagina, ancho, recorte = null) {
    const clave = `${this.huella}|${pagina}|${ancho}|${recorte ? recorte.map((x) => x.toFixed(4)).join(',') : 'todo'}`
    if (this.urls.has(clave)) return this.urls.get(clave)
    let png = await leer(DIBUJOS, clave)
    if (!png) {
      const r = await this.enviar('dibujar', { pagina, ancho, recorte })
      png = new Blob([r.png], { type: 'image/png' })
      guardar(DIBUJOS, clave, png)
    }
    const url = URL.createObjectURL(png)
    this.urls.set(clave, url)
    return url
  }

  cerrar() {
    for (const u of this.urls.values()) { try { URL.revokeObjectURL(u) } catch { /* nada */ } }
    this.urls.clear()
    if (this.obrero) { try { this.obrero.terminate() } catch { /* nada */ } this.obrero = null }
  }
}

const abiertas = new Map()          // huella → Vista

/**
 * Abre un archivo para dibujarlo acá. `huella` identifica al archivo (trabajo + nombre); `traer()`
 * devuelve sus bytes (se llama sólo la primera vez). Devuelve la `Vista` o `null` si no se puede.
 * `topeMb`: por arriba de eso no vale la pena bajarlo para verlo (lo sigue dibujando el servidor).
 */
export async function abrirVista(huella, traer, { topeMb = 400 } = {}) {
  if (abiertas.has(huella)) return abiertas.get(huella)
  if (typeof Worker === 'undefined') return null
  try {
    let bytes = await leer(ARCHIVOS, huella)
    if (bytes) bytes = new Uint8Array(bytes instanceof Blob ? await bytes.arrayBuffer() : bytes)
    if (!bytes) {
      const b = await traer()
      if (!b) return null
      if (b.byteLength > topeMb * 1024 * 1024) return null
      bytes = new Uint8Array(b)
      guardar(ARCHIVOS, huella, new Blob([bytes], { type: 'application/pdf' }))
    }
    const v = new Vista(huella)
    await v.abrir(bytes)
    abiertas.set(huella, v)
    return v
  } catch {
    return null                      // sin memoria, sin permiso, archivo raro: lo dibuja el servidor
  }
}

/** Cierra las vistas abiertas (al salir del pedido, o al empezar uno nuevo). */
export function cerrarVistas() {
  for (const v of abiertas.values()) v.cerrar()
  abiertas.clear()
}

/** Borra del navegador lo guardado de un trabajo (sus dibujos y su archivo). */
export async function olvidarVistas(prefijo) {
  try {
    const db = await abrirDb()
    for (const store of [ARCHIVOS, DIBUJOS]) {
      await new Promise((ok) => {
        const t = db.transaction(store, 'readwrite')
        const s = t.objectStore(store)
        const p = s.openKeyCursor()
        p.onsuccess = () => {
          const c = p.result
          if (!c) return
          if (String(c.key).startsWith(prefijo)) s.delete(c.key)
          c.continue()
        }
        t.oncomplete = t.onerror = t.onabort = () => ok()
      })
    }
  } catch { /* nada que borrar */ }
}
