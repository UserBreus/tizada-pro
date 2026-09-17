// EL EQUIPO DE HILOS DEL MOTOR (PLAN_NAVEGADOR.md, etapa 1 — velocidad).
//
// `crearPool(n, crearObrero)` levanta `n` hilos (`obrero.worker.js`) y reparte tareas: cada tarea
// va al hilo con menos trabajo pendiente. `crearObrero()` devuelve algo con la forma de un Worker
// del navegador (`postMessage`, `onmessage`, `terminate`); en Node se adapta `worker_threads`.

export function crearPool(n, crearObrero) {
  const obreros = []
  let siguienteId = 1
  const pendientes = new Map()      // id → {resolve, reject, obrero}
  for (let i = 0; i < n; i++) {
    const w = crearObrero()
    const o = { w, carga: 0, i }
    w.onmessage = (ev) => {
      const m = ev.data !== undefined ? ev.data : ev
      const p = pendientes.get(m.id)
      if (!p) return
      pendientes.delete(m.id)
      o.carga--
      if (m.error) {
        const err = new Error(m.error)
        err.pila = m.pila
        p.reject(err)
      } else p.resolve(m.valor)
    }
    w.onerror = (e) => {
      for (const [id, p] of pendientes) if (p.obrero === o) { pendientes.delete(id); p.reject(new Error(e.message || 'el hilo se cortó')) }
    }
    obreros.push(o)
  }
  const mandar = (o, tipo, datos, transfer) => new Promise((resolve, reject) => {
    const id = siguienteId++
    pendientes.set(id, { resolve, reject, obrero: o })
    o.carga++
    o.w.postMessage({ id, tipo, datos }, transfer || [])
  })
  return {
    n,
    /** Una tarea al hilo menos cargado. */
    enviar(tipo, datos, transfer) {
      let o = obreros[0]
      for (const x of obreros) if (x.carga < o.carga) o = x
      return mandar(o, tipo, datos, transfer)
    },
    /** La misma tarea a TODOS los hilos (abrir el molde en cada uno). */
    todos(tipo, datosDe) {
      return Promise.all(obreros.map((o) => mandar(o, tipo, datosDe(o.i))))
    },
    cerrar() {
      for (const o of obreros) { try { o.w.terminate() } catch { /* nada */ } }
      for (const [, p] of pendientes) p.reject(new Error('cancelado'))
      pendientes.clear()
    },
  }
}
