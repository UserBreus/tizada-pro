// QUÉ ESTÁ HACIENDO ESTA COMPUTADORA — la parte del navegador del monitor (Configuración → Monitor).
//
// Pedido del usuario (2026-09-18): ver qué corre en el servidor, qué en el navegador y cuánto
// cuesta. Acá se anotan los hilos vivos (`registrarHilo`), las tareas que pasan por los hilos
// (`tareaEmpieza`/`tareaTermina`, las llama `pool.js`), los bytes que se bajaron del servidor
// (`bytesBajados`, lo llama `cache.js`) y la memoria de JavaScript si el navegador la cuenta
// (`performance.memory`, sólo Chrome/Edge). `estado()` devuelve la foto para la pantalla.
const _hilos = new Set()
const _tareas = []                   // las últimas 200: {tipo, ms, ok, t}
const _enCurso = new Map()           // id → {tipo, t0}
let _bytes = 0
let _tareasTotal = 0
let _nId = 0

const _porWorker = new WeakMap()     // Worker → su registro (un hilo se anota UNA vez)

/** Un hilo (Worker) nuevo: devuelve una función para anotar que se cerró. */
export function registrarHilo(w, nombre = 'obrero') {
  // 🔴 UNA VEZ POR HILO (2026-09-24): el hilo de los cálculos del molde se anotaba dos veces —como
  // «molde» al crearlo y como «obrero» en el pool— y el monitor contaba de más. Si ya está, sólo se
  // queda con el nombre más específico (el que no es el genérico «obrero»).
  const ya = _porWorker.get(w)
  if (ya) {
    if (nombre !== 'obrero') ya.h.nombre = nombre
    return ya.cerrar
  }
  const h = { w, nombre, desde: Date.now(), bytes: null, ocupado: false, trabajadoMs: null, cpuPct: null }
  _hilos.add(h)
  const cerrar = () => _hilos.delete(h)
  _porWorker.set(w, { h, cerrar })
  // el `terminate` del Worker se envuelve para no depender de que quien lo creó avise
  try {
    const t = w.terminate.bind(w)
    w.terminate = () => { cerrar(); return t() }
  } catch { /* nada */ }
  return cerrar
}

export function tareaEmpieza(tipo) {
  const id = ++_nId
  _enCurso.set(id, { tipo, t0: performance.now() })
  return id
}

export function tareaTermina(id, ok = true) {
  const t = _enCurso.get(id)
  if (!t) return
  _enCurso.delete(id)
  _tareasTotal++
  _tareas.unshift({ tipo: t.tipo, ms: Math.round(performance.now() - t.t0), ok, t: Date.now() })
  if (_tareas.length > 200) _tareas.length = 200
}

export function bytesBajados(n) { _bytes += n || 0 }

/**
 * LO QUE GASTA TIZADA EN ESTA PC (pedido del usuario 2026-09-24: «lo que consume el sistema real en
 * la PC que lo levanto», no el navegador entero): se le pregunta a cada hilo vivo cuánta memoria
 * usa su motor de PDF (`contestarMemoria` en los workers). Un hilo en medio de un trabajo largo no
 * contesta hasta terminar: queda con su último valor y marcado «ocupado». Lo que Chrome gasta para
 * dibujar la pantalla no se puede leer desde una página: por eso el total es aproximado.
 */
let _almacenMb = null                // lo que TIZADA tiene guardado en esta PC (moldes, artes…)
let _cuotaMb = null                  // lo que el navegador le deja guardar a TIZADA en esta PC
export async function medirHilos(esperaMs = 700) {
  // el disco: lo que ocupa este sitio en el navegador (`navigator.storage`: sólo lo de TIZADA)
  try {
    const e = navigator.storage && navigator.storage.estimate ? await navigator.storage.estimate() : null
    if (e && e.usage != null) _almacenMb = Math.round(e.usage / 1048576)
    if (e && e.quota) _cuotaMb = Math.round(e.quota / 1048576)
  } catch { /* nada */ }
  const ahora = performance.now()
  return Promise.all([..._hilos].map((h) => new Promise((ok) => {
    let listo = false
    const fin = (d) => {
      if (listo) return
      listo = true
      if (d) {
        h.bytes = d.bytes || 0
        h.ocupado = false
        // % de UN núcleo: cuánto de este rato estuvo trabajando el hilo
        if (d.trabajadoMs != null && h.trabajadoMs != null && h.medido && ahora > h.medido) {
          h.cpuPct = Math.max(0, Math.min(100, 100 * (d.trabajadoMs - h.trabajadoMs) / (ahora - h.medido)))
        }
        if (d.trabajadoMs != null) { h.trabajadoMs = d.trabajadoMs; h.medido = ahora }
      } else {
        // no contesta: está en medio de un trabajo largo → trabajando todo el rato
        h.ocupado = true
        h.cpuPct = 100
      }
      ok()
    }
    try {
      const canal = new MessageChannel()
      canal.port1.onmessage = (ev) => { fin(ev.data || {}); canal.port1.close() }
      h.w.postMessage({ __memoria: canal.port2 }, [canal.port2])
      setTimeout(() => fin(null), esperaMs)
    } catch { fin(null) }
  })))
}

/** La foto de ahora. */
export function estado() {
  const n = typeof navigator !== 'undefined' ? navigator : {}
  const mem = (typeof performance !== 'undefined' && performance.memory) ? performance.memory : null
  return {
    hilos: [..._hilos].map((h) => ({ nombre: h.nombre, seg: Math.round((Date.now() - h.desde) / 1000),
      mb: h.bytes != null ? Math.round(h.bytes / 1048576) : null, ocupado: h.ocupado,
      cpu: h.cpuPct != null ? Math.round(h.cpuPct) : null })),
    en_curso: [..._enCurso.values()].map((t) => ({ tipo: t.tipo, ms: Math.round(performance.now() - t.t0) })),
    tareas: _tareas.slice(0, 40),
    tareas_total: _tareasTotal,
    bytes_bajados: _bytes,
    nucleos: n.hardwareConcurrency || null,
    memoria_gb: n.deviceMemory || null,
    js_usado_mb: mem ? Math.round(mem.usedJSHeapSize / 1048576) : null,
    js_tope_mb: mem ? Math.round(mem.jsHeapSizeLimit / 1048576) : null,
    // TIZADA en esta PC ≈ la página (JavaScript) + el motor de cada hilo
    tizada_mb: Math.round((mem ? mem.usedJSHeapSize : 0) / 1048576 +
      [..._hilos].reduce((a, h) => a + (h.bytes || 0), 0) / 1048576),
    // % del procesador de la PC que usan los hilos de TIZADA (la suma de sus núcleos / todos)
    tizada_cpu_pct: Math.round(10 * [..._hilos].reduce((a, h) => a + (h.cpuPct || 0), 0) / (n.hardwareConcurrency || 1)) / 10,
    tizada_disco_mb: _almacenMb,
    tizada_disco_cuota_mb: _cuotaMb,
  }
}
