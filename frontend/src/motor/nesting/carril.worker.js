// UN HILO DEL OPTIMIZADOR DE LA TIZADA (MAPA 728). Lo abre la página (`abrirCarriles` de carriles.js) y le
// manda un CANAL (`{tipo: 'puerto'}`): por ese canal le habla la hoja. Recibe las piezas de una carga
// (`cargar`, con sus máscaras ya hechas) y corre las tareas con las MISMAS funciones que el acomodo en un
// solo hilo (`tareaCarril` de contorno.js). Corre en el navegador (Web Worker) y en Node (worker_threads).
import { tareaCarril } from './contorno.js'

const enNode = typeof self === 'undefined' || typeof self.postMessage !== 'function'
const canal = enNode ? (await import('node:worker_threads')).parentPort : self
const escuchar = (fn) => (enNode ? canal.on('message', fn) : (self.onmessage = (ev) => fn(ev.data)))

let carga = -1, piezas = null, cfg = null

function atender(m, responder) {
  if (!m) return
  if (m.tipo === 'cargar') { carga = m.carga; piezas = m.piezas; cfg = m.cfg; return }
  try {
    if (m.carga !== carga) throw new Error('el hilo del acomodo no tiene esas piezas')
    responder({ carga: m.carga, i: m.i, valor: tareaCarril(piezas, cfg, m.tarea) })
  } catch (e) {
    responder({ carga: m.carga, i: m.i, error: String((e && e.message) || e) })
  }
}

escuchar((m) => {
  if (m && m.tipo === 'puerto') {
    const p = m.puerto
    const responder = (r) => p.postMessage(r)
    if (typeof p.on === 'function') p.on('message', (x) => atender(x, responder))
    else { p.onmessage = (ev) => atender(ev.data, responder); if (p.start) p.start() }
    return
  }
  atender(m, (r) => canal.postMessage(r))
})
