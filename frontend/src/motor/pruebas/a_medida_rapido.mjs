// node frontend/src/motor/pruebas/a_medida_rapido.mjs
// MAPA 661: el molde a medida se prepara en UN hilo (antes: un hilo para el PDF y hasta 12 para leerlo) y
// la misma medida se prepara UNA vez (memoria). Comprueba que el paquete sea EL MISMO que el de antes
// (dos tiempos con un pool aparte) y mide cuánto tarda cada camino. Imprime un JSON en la última línea.
import { Worker as WorkerNode } from 'node:worker_threads'

globalThis.Worker = class {
  constructor(url) {
    this.w = new WorkerNode(url)
    this.w.on('message', (m) => this.onmessage && this.onmessage({ data: m }))
    this.w.on('error', (e) => this.onerror && this.onerror(e))
  }
  postMessage(m, t) { this.w.postMessage(m, t) }
  terminate() { this.w.terminate() }
}

const { prepararMoldeAMedida, prepararEnDosTiempos } = await import('../prepararMolde.js')
const { crearPool } = await import('../pool.js')

const P = { anchoM: 3, altoM: 1.5, pieza: 'Bandera', reservaMm: 2, margen: { todos: 2 }, forma: 'rectangulo', orientacion: 'abajo', terminacion: 'dobladillo' }

// EL CAMINO DE ANTES (dos pools: uno para el PDF, otro de varios hilos para leerlo)
let t = performance.now()
const uno = crearPool(1, () => new Worker(new URL('../obrero.worker.js', import.meta.url), { type: 'module' }), 'antes')
const r = await uno.enviar('a_medida_pdf', P)
uno.cerrar()
const archivo = new File([new Uint8Array(r.pdf)], 'molde_a_medida.pdf', { type: 'application/pdf' })
const viejo = await prepararEnDosTiempos(archivo, { dxfResumen: r.resumen })
const tViejo = performance.now() - t

t = performance.now()
const nuevo = await prepararMoldeAMedida(P)
const tNuevo = performance.now() - t
t = performance.now()
const otra = await prepararMoldeAMedida({ ...P, margen: { arriba: 2, abajo: 2, izq: 2, der: 2 } })   // misma medida, escrita distinto
const tMemoria = performance.now() - t
const distinta = await prepararMoldeAMedida({ ...P, altoM: 1.45 })

const hex = (b) => Buffer.from(new Uint8Array(b)).toString('hex')
console.log(JSON.stringify({
  mismoArchivo: viejo.sha1 === nuevo.sha1,
  mismoPaquete: hex(viejo.zipA) === hex(nuevo.zipA),
  mismoResumen: JSON.stringify(viejo.resumen) === JSON.stringify(nuevo.resumen),
  memoria: otra === nuevo,
  otraMedidaEsOtra: distinta.sha1 !== nuevo.sha1,
  ms: { antes: Math.round(tViejo), ahora: Math.round(tNuevo), memoria: Math.round(tMemoria) },
}))
import('node:fs').then(fs => { fs.writeFileSync(process.env.ZV, Buffer.from(new Uint8Array(viejo.zipA))); fs.writeFileSync(process.env.ZN, Buffer.from(new Uint8Array(nuevo.zipA))); process.exit(0) })
