// node frontend/src/motor/pruebas/desplegar_paralelo.mjs <molde.ai> <carpeta_salida> [hilos]
// El desplegado con VARIOS HILOS (worker_threads, el mismo `obrero.worker.js` que el navegador),
// escrito como `desplegar.mjs` para que `verificar_navegador_desplegado.py` lo compare con el servidor.
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { Worker } from 'node:worker_threads'
import { crearPool } from '../pool.js'
import { abrirEnPool, faseA, faseB } from '../molde/desplegar_paralelo.js'
import { aJSON } from '../molde/contornos.js'

const [, , entrada, carpeta, hilosArg] = process.argv
const hilos = Number(hilosArg) || Math.max(2, Math.min(8, os.cpus().length - 1))
fs.mkdirSync(carpeta, { recursive: true })
const urlObrero = new URL('../obrero.worker.js', import.meta.url)
const crearObrero = () => {
  const w = new Worker(urlObrero, { resourceLimits: { maxOldGenerationSizeMb: 4096 } })
  const o = { postMessage: (m, t) => w.postMessage(m, t), terminate: () => w.terminate(), onmessage: null, onerror: null }
  w.on('message', (m) => o.onmessage && o.onmessage({ data: m }))
  w.on('error', (e) => o.onerror && o.onerror(e))
  return o
}
const t0 = performance.now()
const pool = crearPool(hilos, crearObrero)
const tiempos = {}
let marca = performance.now()
const lap = (k) => { const t = performance.now(); tiempos[k] = (t - marca) / 1000; marca = t }
try {
  const bytes = new Uint8Array(fs.readFileSync(entrada))
  const info = await abrirEnPool(pool, bytes)
  lap('abrir')
  const A = await faseA(pool, info)
  lap('faseA')
  const r = await faseB(pool, A)
  lap('faseB')
  for (const [m, { json, pdf }] of r.mesas) {
    fs.writeFileSync(path.join(carpeta, `m${m}.json`), JSON.stringify(aJSON(json)))
    if (pdf) fs.writeFileSync(path.join(carpeta, `m${m}.pdf`), pdf)
  }
  if (r.etiqueta) fs.writeFileSync(path.join(carpeta, 'etiqueta_archivo.json'), JSON.stringify(aJSON(r.etiqueta)))
  fs.writeFileSync(path.join(carpeta, 'alta.json'), JSON.stringify(aJSON(r.alta)))
  fs.writeFileSync(path.join(carpeta, 'tiempos.json'), JSON.stringify({ total: (performance.now() - t0) / 1000, hilos,
    contornos: tiempos.abrir + tiempos.faseA, etiquetas: 0, paginas: tiempos.faseB, memoria_mb: process.memoryUsage().rss / 1048576, ...tiempos }))
} finally {
  pool.cerrar()
}
