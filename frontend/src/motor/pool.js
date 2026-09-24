// EL EQUIPO DE HILOS DEL MOTOR (PLAN_NAVEGADOR.md, etapa 1 — velocidad).
//
// `crearPool(n, crearObrero)` levanta `n` hilos (`obrero.worker.js`) y reparte tareas: cada tarea
// va al hilo con menos trabajo pendiente. `crearObrero()` devuelve algo con la forma de un Worker
// del navegador (`postMessage`, `onmessage`, `terminate`); en Node se adapta `worker_threads`.

import { registrarHilo, tareaEmpieza, tareaTermina } from './monitor.js'

// `nombre`: para qué es este equipo de hilos (lo muestra el Monitor, ver `monitor.js`)
export function crearPool(n, crearObrero, nombre = 'obrero') {
  const obreros = []
  let siguienteId = 1
  const pendientes = new Map()      // id → {resolve, reject, obrero}
  for (let i = 0; i < n; i++) {
    const w = crearObrero()
    registrarHilo(w, nombre)
    const o = { w, carga: 0, i }
    w.onmessage = (ev) => {
      const m = ev.data !== undefined ? ev.data : ev
      const p = pendientes.get(m.id)
      if (!p) return
      // un AVANCE no termina la tarea: se le pasa a quien la pidió y se sigue esperando
      if (m.avance !== undefined && !('valor' in m) && !m.error) {
        if (p.alAvance) { try { p.alAvance(m.avance, m.texto) } catch { /* la pantalla no puede cortar el trabajo */ } }
        return
      }
      pendientes.delete(m.id)
      o.carga--
      tareaTermina(p.mon, !m.error)
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
  const mandar = (o, tipo, datos, transfer, alAvance = null) => new Promise((resolve, reject) => {
    const id = siguienteId++
    pendientes.set(id, { resolve, reject, obrero: o, mon: tareaEmpieza(tipo), alAvance })
    o.carga++
    o.w.postMessage({ id, tipo, datos }, transfer || [])
  })
  return {
    n,
    /** Una tarea al hilo menos cargado. `alAvance(fraccion, texto)`: los avisos de avance que mande. */
    enviar(tipo, datos, transfer, alAvance = null) {
      let o = obreros[0]
      for (const x of obreros) if (x.carga < o.carga) o = x
      return mandar(o, tipo, datos, transfer, alAvance)
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
