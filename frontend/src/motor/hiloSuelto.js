// UNA TAREA DEL MOTOR EN UN HILO DE USAR Y TIRAR — para lo que se hace una vez y no tiene un motor de
// molde abierto (analizar una tipografía antes de subirla, revalidar un arte): abre un
// `obrero.worker.js`, le pide la tarea y lo cierra. Es el mismo patrón de `prepararArte.js`.
import { registrarHilo } from './monitor.js'

export async function enHiloSuelto(tipo, datos, transfer = [], etiqueta = 'tarea') {
  const w = new Worker(new URL('./obrero.worker.js', import.meta.url), { type: 'module' })
  registrarHilo(w, etiqueta)
  try {
    return await new Promise((ok, no) => {
      w.onmessage = (e) => {
        const m = e.data || {}
        if (m.avance !== undefined) return            // avisos de avance: no son la respuesta
        if (m.error) no(new Error(m.error)); else ok(m.valor)
      }
      w.onerror = (e) => no(new Error('el hilo de trabajo no arrancó: ' + (e.message || '')))
      w.postMessage({ id: 1, tipo, datos }, transfer)
    })
  } finally {
    try { w.terminate() } catch { /* nada */ }
  }
}
