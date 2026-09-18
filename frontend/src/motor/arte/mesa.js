// LA MESA DEL ARTE, DIBUJADA EN ESTA COMPUTADORA — PLAN_NAVEGADOR.md, etapa 2/3 (camino A).
//
// El paso Arte muestra cada mesa del arte como SVG (`/api/arte/mesa_img`: `get_svg_image` con las
// capas «guías» y «Editable …» apagadas). Acá se hace lo mismo en un hilo de trabajo: el arte se
// baja UNA vez (`/api/productos/<pid>/arte_archivo?diseno=`), queda en IndexedDB y cada mesa sale
// del mismo escritor SVG de MuPDF (`pieza/svg.js`). Sigue siendo el VECTOR: nada se rasteriza.
//
// 🔴 Si no se puede (el servidor tiene el interruptor `arte` apagado, el navegador no da, el arte
// es enorme), `localizarMesas` deja las URLs del servidor como estaban: nada se degrada.
import { traerConCache } from '../cache.js'
import { navegadorHace } from '../vista/vista.js'

const artes = new Map()             // `${pid}|${diseno}|${firma}` → {obrero, pendientes, n, urls}
const TOPE_MB = 300

function abridor(clave) {
  let a = artes.get(clave)
  if (a) return a
  a = { clave, obrero: null, pendientes: new Map(), n: 0, urls: new Map(), listo: null }
  a.enviar = (tipo, datos, transfer) => new Promise((ok, no) => {
    if (!a.obrero) {
      a.obrero = new Worker(new URL('../obrero.worker.js', import.meta.url), { type: 'module' })
      a.obrero.onmessage = (e) => {
        const m = e.data || {}
        const p = a.pendientes.get(m.id)
        if (!p) return
        a.pendientes.delete(m.id)
        m.error ? p.no(new Error(m.error)) : p.ok(m.valor)
      }
      a.obrero.onerror = (e) => {
        const err = new Error('el hilo que dibuja el arte no arrancó: ' + (e.message || ''))
        for (const p of a.pendientes.values()) p.no(err)
        a.pendientes.clear()
      }
    }
    const id = ++a.n
    a.pendientes.set(id, { ok, no })
    a.obrero.postMessage({ id, tipo, datos }, transfer || [])
  })
  artes.set(clave, a)
  return a
}

/** La firma del archivo tal como la pone el servidor en `m.img` (`v=<mtime>-<tamaño>`). */
function firmaDe(det) {
  const m = (det.mesas || []).find((x) => x && x.img && !x.img_local)
  const v = m && /[?&]v=([^&]+)/.exec(m.img)
  return v ? v[1] : null
}

/**
 * Cambia `m.img` de cada mesa de `det` (lo que devuelve `/api/arte/deteccion`) por una URL de un
 * SVG dibujado acá. Devuelve el mismo `det`. Si algo no se puede, las URLs del servidor quedan.
 */
export async function localizarMesas(det, { pid, diseno = null, rutaApi = (x) => x } = {}) {
  if (!det || !Array.isArray(det.mesas) || !det.mesas.length || typeof Worker === 'undefined') return det
  if (!(await navegadorHace('arte', rutaApi))) return det
  const firma = firmaDe(det)
  if (!firma) return det
  const clave = `${pid}|${diseno || 'principal'}|${firma}`
  const a = abridor(clave)
  try {
    if (!a.listo) {
      a.listo = (async () => {
        const url = rutaApi(`/api/productos/${encodeURIComponent(pid)}/arte_archivo` + (diseno ? `?diseno=${encodeURIComponent(diseno)}` : ''))
        const bytes = await traerConCache(`arte|${clave}`, url)
        if (bytes.byteLength > TOPE_MB * 1024 * 1024) throw new Error('el arte es demasiado grande para dibujarlo acá')
        return a.enviar('arte_abrir', { bytes }, [bytes.buffer])
      })()
    }
    const n = await a.listo
    await Promise.all(det.mesas.map(async (m) => {
      const pagina = (m.mesa || 1) - 1
      if (pagina < 0 || pagina >= n) return
      if (!a.urls.has(pagina)) {
        const svg = await a.enviar('arte_svg', { pagina })
        a.urls.set(pagina, URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml' })))
      }
      m.img = a.urls.get(pagina)
      m.img_local = true
    }))
  } catch (e) {
    console.warn('[arte] la mesa la dibuja el servidor:', e && e.message)
    a.listo = null
  }
  return det
}

/** Cierra los artes abiertos (al cambiar de pedido). Las URLs siguen valiendo hasta recargar. */
export function cerrarArtes() {
  for (const a of artes.values()) { if (a.obrero) { try { a.obrero.terminate() } catch { /* nada */ } } }
  artes.clear()
}
