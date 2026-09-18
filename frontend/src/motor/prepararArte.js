// EL ARTE SEPARADO, ANALIZADO EN LA COMPUTADORA DE LA PERSONA — PLAN_NAVEGADOR.md, etapa 3 (camino A).
//
// La pantalla llama a esto antes de subir un arte: un hilo (`obrero.worker.js` → `arte_preparar`,
// `arte/preparar.js`) detecta las mesas, la personalización, el mapeo por nombre y la validación,
// y arma el paquete que viaja con el archivo (`POST /api/arte` con `paquete`). El servidor sólo
// comprueba y guarda (`servidor._subir_arte_paquete`). Si el servidor tiene esto apagado devuelve
// `null` y el arte se manda pelado, como siempre.
import { navegadorHace } from './vista/vista.js'
import { puedeHacer } from './capacidad.js'
import { traerConCache } from './cache.js'
import { registrarHilo } from './monitor.js'

async function json(url, opts) {
  const r = await fetch(url, opts)
  const d = await r.json().catch(() => ({}))
  if (!r.ok) { const e = new Error(d.error || `${url}: ${r.status}`); e.datos = d; throw e }
  return d
}

/**
 * `archivo` = el File del arte; `pid` el molde; `diseno` el diseño (o null = principal).
 * Devuelve `{zip, modo, validacion}` o `null`. Tira un Error con mensaje para la pantalla si esta
 * computadora no puede (`e.capacidad`).
 */
export async function prepararArteEnNavegador(archivo, { pid, diseno = null, rutaApi = (x) => x, avisar = null } = {}) {
  if (!pid || !(await navegadorHace('arte', rutaApi))) return null
  const puerta = puedeHacer({ tipo: 'molde', mb: archivo.size / 1048576, hilos: 1 })
  if (!puerta.puede) { const e = new Error(puerta.motivo); e.capacidad = true; throw e }
  avisar && avisar('Leyendo el diseño en tu computadora…')
  const contexto = await json(rutaApi(`/api/productos/${encodeURIComponent(pid)}/arte_contexto`))
  // la plantilla decide el modo (`arte_es_separado`) igual que en el servidor
  const plantilla = contexto.plantilla_sello
    ? await traerConCache(`plantilla|${pid}|${contexto.plantilla_sello.join(',')}`, rutaApi(`/api/productos/${encodeURIComponent(pid)}/descargar_plantilla`))
    : null
  const bytes = new Uint8Array(await archivo.arrayBuffer())
  const w = new Worker(new URL('./obrero.worker.js', import.meta.url), { type: 'module' })
  registrarHilo(w, 'arte')
  try {
    const r = await new Promise((ok, no) => {
      w.onmessage = (e) => { const m = e.data || {}; m.error ? no(new Error(m.error)) : ok(m.valor) }
      w.onerror = (e) => no(new Error('el hilo que analiza el diseño no arrancó: ' + (e.message || '')))
      w.postMessage({ id: 1, tipo: 'arte_preparar', datos: { bytes, contexto: { ...contexto, diseno, plantilla: plantilla ? plantilla.slice() : null } } }, [bytes.buffer])
    })
    return { zip: r.zip, modo: r.modo, validacion: r.validacion, mapeo: r.mapeo, sha1: r.sha1 }
  } finally {
    try { w.terminate() } catch { /* nada */ }
  }
}
