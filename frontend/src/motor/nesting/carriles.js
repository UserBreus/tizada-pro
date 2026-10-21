// LOS CARRILES DEL OPTIMIZADOR EN VARIOS HILOS (MAPA 728).
//
// `anidarContorno(piezas, cfg, ejecutor)` (contorno.js) reparte su trabajo en TAREAS independientes —los
// puntos de partida de la búsqueda y los carriles— y este ejecutor las corre a la vez, una por hilo libre
// (`carril.worker.js`). Cada hilo recibe las piezas UNA vez (con sus máscaras ya hechas) y después las tareas
// que le tocan. El resultado de cada tarea vuelve en su lugar de la lista: quién la corrió y en qué orden
// terminó no cambia nada, así que la tizada sale IGUAL con 1 hilo o con 12 (y igual que en Python, que las
// corre en orden).
//
// 🔴 LOS HILOS LOS ABRE LA PÁGINA, NO EL HILO DE LA HOJA: el acomodo corre adentro de un hilo (`obrero.worker.js`,
// tarea `hoja`) y el navegador NO deja que un hilo abra otro desde un archivo (medido 2026-10-16: `new Worker`
// adentro de un hilo da «error» sin más, con el mismo archivo que desde la página abre bien). Por eso la página
// abre los hilos de carriles (`abrirCarriles`) y le pasa a la hoja un CANAL a cada uno (MessagePort): la hoja
// les habla por ahí. En Node (robot, contratos) es igual, con worker_threads.

const esNode = typeof process !== 'undefined' && !!(process.versions && process.versions.node)

/** Cuántos hilos usar: los de la PC menos uno (el que arma la hoja), hasta 8. */
export async function hilosParaCarriles() {
  let n = 4
  if (esNode) {
    try { const os = await import('node:os'); n = os.availableParallelism ? os.availableParallelism() : os.cpus().length } catch { n = 4 }
  } else if (typeof navigator !== 'undefined' && navigator.hardwareConcurrency) n = navigator.hardwareConcurrency
  return Math.max(1, Math.min(8, n - 1))
}

// el archivo del hilo en una variable: en Node sin `Worker` del navegador se abre con worker_threads; si la
// ruta fuera un literal, el empaquetador lo copiaría como un recurso suelto
const ARCHIVO_NODE = './carril.worker.js'

async function nuevoHilo() {
  if (typeof Worker !== 'undefined') return new Worker(new URL('./carril.worker.js', import.meta.url), { type: 'module' })
  const { Worker: W } = await import('node:worker_threads')
  return new W(new URL(ARCHIVO_NODE, import.meta.url))
}

/**
 * Lo llama la PÁGINA (o el proceso de Node) antes de mandar la hoja: abre `n` hilos de carriles y devuelve
 * `{puertos, cerrar}`: un canal por hilo, para pasarle a la tarea `hoja` (van en la lista de transferencia).
 */
export async function abrirCarriles(n) {
  const hilos = [], puertos = []
  for (let i = 0; i < n; i++) {
    const w = await nuevoHilo()
    const ch = new MessageChannel()
    w.postMessage({ tipo: 'puerto', puerto: ch.port2 }, [ch.port2])
    hilos.push(w)
    puertos.push(ch.port1)
  }
  return { puertos, cerrar: () => { for (const w of hilos) { try { w.terminate() } catch { /* ya estaba cerrado */ } } } }
}

/** Lo que el hilo necesita de cada pieza: su caja y las máscaras YA preparadas acá (`preparar`: viajan una
 * vez por geometría, el mensaje conserva lo compartido), así el hilo no las vuelve a armar (3,8 s con 100
 * piezas). Nada del dibujo. */
function pieza(p) {
  // del `base`, sólo la geometría del contorno (la compactación con el contorno real corre en un hilo, MAPA 736)
  const b = p.base && p.base.cont ? (p.base._geo || (p.base._geo = { cont: p.base.cont, S: p.base.S, x0: p.base.x0, y0: p.base.y0, B: p.base.B, W: p.base.W, Hp: p.base.Hp })) : null
  return { w: p.w, h: p.h, pieza: p.pieza, talle: p.talle, variante: p.variante, _molde: p._molde, rotacion: p.rotacion,
           borde_cm: p.borde_cm, etiqueta: p.etiqueta, _mask: p._mask, _borde_c: p._borde_c, _cell_pt: p._cell_pt,
           _candidatos_angulo: p._candidatos_angulo, _cache_key: p._cache_key, _geo_key: p._geo_key, base: b }
}

/** Un canal (MessagePort del navegador o de Node) como `{enviar, recibir, cerrar}`. */
function canalDe(port) {
  let fn = () => {}
  if (typeof port.on === 'function') port.on('message', (m) => fn(m))
  else { port.onmessage = (ev) => fn(ev.data); if (port.start) port.start() }
  return { enviar: (m) => port.postMessage(m), recibir: (f) => { fn = f }, cerrar: () => { try { port.close() } catch { /* ya estaba */ } } }
}

/**
 * → `ejecutor(piezas, cfg, tareas)`: una promesa con el resultado de cada tarea, EN EL ORDEN de `tareas`.
 * `puertos`: los canales de `abrirCarriles` (lo que recibe la hoja). `alAvance(hechas, total)` cuenta tareas
 * terminadas (la barra). `ejecutor.cerrar()` suelta los canales (los hilos los cierra quien los abrió).
 */
export function crearEjecutor({ puertos, alAvance = null }) {
  const pool = puertos.map(canalDe)
  let cargas = 0, ultima = null
  const ejecutor = async (piezas, cfg, tareas) => {
    if (!tareas.length) return []
    const n = Math.max(1, Math.min(pool.length, tareas.length))
    // las mismas piezas que la vez anterior (la búsqueda y después los carriles): no se vuelven a mandar
    if (!(ultima && ultima.piezas === piezas && ultima.cfg === cfg)) ultima = { piezas, cfg, carga: ++cargas, slim: piezas.map(pieza) }
    const { carga, slim } = ultima
    const res = new Array(tareas.length)
    return new Promise((resolve, reject) => {
      let siguiente = 0, hechas = 0, roto = false
      const dar = (h) => {
        if (siguiente >= tareas.length) return
        const i = siguiente++
        h.enviar({ tipo: 'tarea', carga, i, tarea: tareas[i] })
      }
      for (let k = 0; k < n; k++) {
        const h = pool[k]
        h.recibir((m) => {
          if (!m || m.carga !== carga || roto) return
          if (m.error) { roto = true; reject(new Error(m.error)); return }
          res[m.i] = m.valor
          hechas++
          if (alAvance) { try { alAvance(hechas, tareas.length) } catch { /* la pantalla no corta el acomodo */ } }
          if (hechas === tareas.length) resolve(res)
          else dar(h)
        })
        if (h.carga !== carga) { h.enviar({ tipo: 'cargar', carga, piezas: slim, cfg }); h.carga = carga }
        dar(h)
      }
    })
  }
  ejecutor.cerrar = () => { for (const h of pool) h.cerrar(); ultima = null }
  return ejecutor
}
