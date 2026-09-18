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

/** Un hilo (Worker) nuevo: devuelve una función para anotar que se cerró. */
export function registrarHilo(w, nombre = 'obrero') {
  const h = { w, nombre, desde: Date.now() }
  _hilos.add(h)
  const cerrar = () => _hilos.delete(h)
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

/** La foto de ahora. */
export function estado() {
  const n = typeof navigator !== 'undefined' ? navigator : {}
  const mem = (typeof performance !== 'undefined' && performance.memory) ? performance.memory : null
  return {
    hilos: [..._hilos].map((h) => ({ nombre: h.nombre, seg: Math.round((Date.now() - h.desde) / 1000) })),
    en_curso: [..._enCurso.values()].map((t) => ({ tipo: t.tipo, ms: Math.round(performance.now() - t.t0) })),
    tareas: _tareas.slice(0, 40),
    tareas_total: _tareasTotal,
    bytes_bajados: _bytes,
    nucleos: n.hardwareConcurrency || null,
    memoria_gb: n.deviceMemory || null,
    js_usado_mb: mem ? Math.round(mem.usedJSHeapSize / 1048576) : null,
    js_tope_mb: mem ? Math.round(mem.jsHeapSizeLimit / 1048576) : null,
  }
}
