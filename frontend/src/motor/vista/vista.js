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

/**
 * Una vista abierta: los hilos que dibujan + el PDF ya cargado en cada uno.
 *
 * VARIOS HILOS y LO MÁS NUEVO PRIMERO (2026-09-18, reporte del usuario: «el visor le re cuesta»).
 * Medido sobre un pedido real: la lista de dibujo de una hoja de 10 MB tarda 18 s en armarse y
 * cada recorte del zoom 8-20 s. Con un solo hilo, los recortes se atendían de a uno y en el orden
 * en que llegaban: al mover la pantalla se seguían dibujando recortes que ya no se veían. Ahora:
 *   · hasta 3 hilos (según núcleos y tamaño del archivo), cada uno con su copia del PDF y su lista;
 *   · los pedidos se atienden del ÚLTIMO al primero (lo que la pantalla está mirando ahora), y el
 *     precalentado (`precalentar`) va al final de la fila;
 *   · lo dibujado queda en IndexedDB: la próxima vez que se abra el pedido no se dibuja nada.
 */
class Vista {
  constructor(huella) {
    this.huella = huella
    this.obreros = []               // [{w, libre}]
    this.pendientes = new Map()     // id → {ok, no, obrero}
    this.cola = []                  // pedidos sin atender: {id, tipo, datos, transfer, ok, no, fondo}
    this.n = 0
    this.urls = new Map()           // clave de dibujo → object URL ya armada
    this.enCurso = new Map()        // clave → Promise (para no pedir dos veces lo mismo)
  }

  _nuevoObrero() {
    const w = new Worker(new URL('../vista.worker.js', import.meta.url), { type: 'module' })
    registrarHilo(w, 'vista')
    const o = { w, libre: true }
    w.onmessage = (e) => {
      const { id, ok, valor, error } = e.data || {}
      const p = this.pendientes.get(id)
      if (!p) return
      this.pendientes.delete(id)
      o.libre = true
      ok ? p.ok(valor) : p.no(new Error(error))
      this._bombear()
    }
    // Si el hilo no arranca (navegador viejo, WebAssembly bloqueado) nadie contestaría nunca y la
    // pantalla se quedaría esperando en silencio: se corta acá y dibuja el servidor.
    w.onerror = (e) => {
      const err = new Error('el hilo que dibuja no arrancó: ' + (e.message || ''))
      for (const [id, p] of this.pendientes) if (p.obrero === o) { this.pendientes.delete(id); p.no(err) }
      for (const c of this.cola.splice(0)) c.no(err)
    }
    this.obreros.push(o)
    return o
  }

  _mandar(o, c) {
    o.libre = false
    this.pendientes.set(c.id, { ok: c.ok, no: c.no, obrero: o })
    o.w.postMessage({ id: c.id, tipo: c.tipo, datos: c.datos }, c.transfer || [])
  }

  /** Reparte la cola: lo más nuevo primero; lo de fondo (precalentado) al final. */
  _bombear() {
    for (const o of this.obreros) {
      if (!o.libre || !this.cola.length) continue
      let k = this.cola.length - 1
      while (k > 0 && this.cola[k].fondo) k--
      if (this.cola[k].fondo) k = 0                       // sólo queda fondo: el más viejo primero
      const c = this.cola.splice(k, 1)[0]
      this._mandar(o, c)
    }
  }

  enviar(tipo, datos, transfer, fondo = false) {
    const id = ++this.n
    return new Promise((ok, no) => {
      this.cola.push({ id, tipo, datos, transfer, ok, no, fondo })
      this._bombear()
    })
  }

  /** Abre el archivo en `hilos` hilos (cada uno recibe su copia de los bytes). */
  async abrir(bytes, hilos = 1) {
    for (let i = 0; i < hilos; i++) this._nuevoObrero()
    const r = await Promise.all(this.obreros.map((o, i) => new Promise((ok, no) => {
      const id = ++this.n
      const copia = i === hilos - 1 ? bytes : bytes.slice()
      this._mandar(o, { id, tipo: 'abrir', datos: { bytes: copia }, transfer: [copia.buffer], ok, no })
    })))
    this.medidas = r[0].medidas
    return r[0]
  }

  /** El ancho en píxeles de la FOTO de la página `pagina` a `pxcm` px por cm. */
  anchoFoto(pagina, pxcm) {
    const m = (this.medidas || [])[pagina]
    return m ? Math.max(1, Math.round((m.ancho / CM_PT) * pxcm)) : Math.round(180 * pxcm)
  }

  claveDe(pagina, ancho, recorte = null) {
    return `${this.huella}|${pagina}|${ancho}|${recorte ? recorte.map((x) => x.toFixed(4)).join(',') : 'todo'}`
  }

  /** ¿Este dibujo ya está (o ya se está haciendo)? */
  yaPedido(pagina, ancho, recorte = null) {
    const k = this.claveDe(pagina, ancho, recorte)
    return this.urls.has(k) || this.enCurso.has(k)
  }

  /** `recorte` = [cx0, cy0, cx1, cy1] en fracciones, o null. Devuelve una URL para un `<img>`. */
  async dibujo(pagina, ancho, recorte = null, fondo = false) {
    const clave = this.claveDe(pagina, ancho, recorte)
    if (this.urls.has(clave)) return this.urls.get(clave)
    if (this.enCurso.has(clave)) return this.enCurso.get(clave)
    const p = (async () => {
      let png = await leer(DIBUJOS, clave)
      if (!png) {
        const r = await this.enviar('dibujar', { pagina, ancho, recorte }, null, fondo)
        png = new Blob([r.png], { type: 'image/png' })
        guardar(DIBUJOS, clave, png)
      }
      const url = URL.createObjectURL(png)
      this.urls.set(clave, url)
      return url
    })()
    this.enCurso.set(clave, p)
    p.finally(() => this.enCurso.delete(clave)).catch(() => {})
    return p
  }

  cerrar() {
    for (const u of this.urls.values()) { try { URL.revokeObjectURL(u) } catch { /* nada */ } }
    this.urls.clear()
    for (const o of this.obreros) { try { o.w.terminate() } catch { /* nada */ } }
    this.obreros = []
    const err = new Error('cerrado')
    for (const c of this.cola.splice(0)) c.no(err)
    for (const [, p] of this.pendientes) p.no(err)
    this.pendientes.clear()
  }
}

/**
 * Cuántos hilos abrir para un archivo de `bytes`: cada hilo tiene su copia del PDF y sus listas
 * de dibujo (medido: ~150 MB por hilo con una hoja de 11 MB), así que manda la memoria que declara
 * el navegador (hasta 6, dos por GB) y el tamaño del archivo.
 */
function hilosParaVista(bytes) {
  const n = typeof navigator !== 'undefined' ? navigator : {}
  const nucleos = n.hardwareConcurrency || 4
  const memGb = n.deviceMemory || 4
  const mb = bytes / 1048576
  // el cupo es de TODAS las vistas abiertas (un pedido son varias hojas): con 4 hojas y 6 hilos
  // cada una serían 24 hilos y 24 copias del PDF
  const abiertosYa = [...abiertas.values()].reduce((k, v) => k + v.obreros.length, 0)
  // medido (2026-09-18, 12 núcleos / 32 GB): 24 hilos dejaron listos 258 dibujos de un pedido de
  // 28 m de tela en ~8 min; cada hilo pesa ~150-300 MB con una hoja de 11 MB → un hilo por núcleo
  // (menos uno para la pantalla) mientras la memoria declarada dé (≈ 1 hilo por cada 0,8 GB)
  const cupo = Math.max(1, Math.min(12, nucleos - 1, Math.floor(memGb * 1.25)))
  return Math.max(1, Math.min(cupo - abiertosYa, mb > 60 ? 1 : mb > 25 ? 2 : 6))
}

const abiertas = new Map()          // huella → Vista
// LA VISTA ES UNA FOTO DE CADA MESA, DE UNA SOLA CALIDAD (decisión del usuario 2026-09-18):
// «muchas imágenes pequeñas formando una es lo que lo hace lento… debe ser UNA sola calidad, como
// una foto: si es buena se ve bien completa y se ve bien si me acerco». Así que cada mesa se dibuja
// UNA vez, entera, a `pxcm` píxeles por centímetro, y el zoom sólo agranda esa imagen (no hay
// pedazos ni cambios de calidad). La calidad es la MISMA para todas las mesas del pedido.
//
// 🔴 EL TECHO DE UNA FOTO (medido con una mesa real de 1,80 × 8 m): a 16 px/cm son 2880 × 12 779 px,
// 7 s de dibujo, 3 MB de PNG y ~147 MB de memoria cuando el navegador la muestra; a 32 px/cm (lo que
// daban los pedazos) serían ~590 MB por mesa: no entra. A 16 px/cm el nombre, el número y el talle
// se ven nítidos con zoom fuerte; la letra de 3 mm de la etiqueta del cuello apenas se lee. Es el
// límite que motivó los pedazos el 2026-09-14 (a 1200 px esa etiqueta medía 2 px); el usuario
// eligió la foto única sabiéndolo. Si hay que afinarlo, es este número.
export const FOTO_PXCM = 16                // la calidad pedida
const TOPE_MPX_PEDIDO = 120                // todas las mesas del pedido juntas en pantalla: ~480 MB como mucho
const TOPE_LADO_PX = 15000                 // un lado más largo que esto el navegador no lo decodifica bien
const CM_PT = 28.3465
const _progreso = new Map()          // `${huella}|${página}` → {total, hechos}: el precalentado POR MESA

/**
 * La calidad de la foto para ESTE pedido, en px por cm (la misma para todas sus mesas).
 * `hojas` = `resultado.hojas` (`ancho_cm`, `alturas_cm`). Baja de `FOTO_PXCM` sólo si el pedido es
 * tan grande que todas las fotos juntas no entrarían en memoria, o si una mesa es tan larga que
 * su foto pasaría el lado máximo que el navegador maneja (una mesa de 50 m, por ejemplo).
 */
export function calidadFoto(hojas) {
  let area = 0, ladoMax = 0
  for (const h of (hojas || [])) {
    const ancho = Number(h.ancho_cm) || 180
    const altos = (h.alturas_cm && h.alturas_cm.length) ? h.alturas_cm : [Number(h.consumo_cm) || 0]
    for (const alto of altos) { area += ancho * (Number(alto) || 0); ladoMax = Math.max(ladoMax, ancho, Number(alto) || 0) }
  }
  if (!area || !ladoMax) return FOTO_PXCM
  const q = Math.min(FOTO_PXCM, Math.sqrt(TOPE_MPX_PEDIDO * 1e6 / area), TOPE_LADO_PX / ladoMax)
  return Math.max(4, Math.floor(q * 2) / 2)          // en pasos de medio px/cm: el mismo número al generar y al mirar
}

/** Cuánto falta del precalentado, por MESA: `{mesas, listas}`. */
export function progresoVistas() {
  let mesas = 0, listas = 0
  for (const m of _progreso.values()) { mesas++; if (m.hechos >= m.total) listas++ }
  return { mesas, listas }
}

function _anotarFondo(clave, p) {
  const m = _progreso.get(clave) || { total: 0, hechos: 0 }
  m.total++
  _progreso.set(clave, m)
  const fin = () => {
    m.hechos++
    // cuando TODAS las mesas están, el cartel se va y la cuenta arranca de cero la próxima vez
    if ([..._progreso.values()].every((x) => x.hechos >= x.total)) _progreso.clear()
  }
  p.then(fin, fin)
}

/**
 * Dibuja de fondo lo que la pantalla va a pedir de esta vista: con `pxcm`, LA FOTO de cada mesa;
 * con `anchos`, esos anchos (la ficha técnica). Lo que ya está o ya se pidió no se cuenta dos veces.
 */
export function precalentarTodo(v, { pxcm = null, anchos = [] } = {}) {
  const paginas = (v.medidas || []).length
  const pedir = (p, ancho) => { if (!v.yaPedido(p, ancho, null)) _anotarFondo(`${v.huella}|${p}`, v.dibujo(p, ancho, null, true)) }
  if (pxcm) for (let p = 0; p < paginas; p++) pedir(p, v.anchoFoto(p, pxcm))
  for (const ancho of anchos) for (let p = 0; p < paginas; p++) pedir(p, ancho)
}

/**
 * Los bytes de un archivo de un trabajo: de la caché del navegador si ya están (se guardan al
 * generar el pedido acá o al verlo) y, si no, `traer()` una vez y quedan guardados.
 */
export async function bytesDeArchivo(huella, traer) {
  let bytes = null
  try { bytes = await leer(ARCHIVOS, huella) } catch { bytes = null }
  if (bytes) return new Uint8Array(bytes instanceof Blob ? await bytes.arrayBuffer() : bytes)
  const b = await traer()
  if (!b) return null
  const u = new Uint8Array(b)
  try { guardar(ARCHIVOS, huella, new Blob([u], { type: 'application/pdf' })) } catch { /* sin caché */ }
  return u
}

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
    await v.abrir(bytes, hilosParaVista(bytes.byteLength))
    abiertas.set(huella, v)
    return v
  } catch {
    return null                      // sin memoria, sin permiso, archivo raro: lo dibuja el servidor
  }
}

/**
 * PRECALENTAR: apenas esta computadora generó el pedido ya tiene los bytes de cada hoja y de la
 * ficha. Se guardan en la caché (no se vuelven a bajar del servidor) y se dibuja de fondo la foto
 * de cada mesa (`pxcm`) o las hojas de la ficha (`anchos`): al abrir el paso Tizada, ya están.
 */
export async function precalentarVista(huella, bytes, { pxcm = null, anchos = [] } = {}) {
  if (typeof Worker === 'undefined' || !bytes || !bytes.byteLength) return null
  try {
    const copia = new Uint8Array(bytes.slice ? bytes.slice() : bytes)
    guardar(ARCHIVOS, huella, new Blob([copia], { type: 'application/pdf' }))
    const v = await abrirVista(huella, async () => copia.buffer)
    if (!v) return null
    precalentarTodo(v, { pxcm, anchos })
    return v
  } catch {
    return null
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
