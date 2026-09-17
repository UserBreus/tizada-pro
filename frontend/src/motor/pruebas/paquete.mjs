// node frontend/src/motor/pruebas/paquete.mjs <molde.ai> <salida.zip>                → paquete completo (un hilo)
// node frontend/src/motor/pruebas/paquete.mjs <molde.ai> <faseA.zip> <faseB.zip> [hilos] → los DOS tiempos (varios hilos)
// Prepara el molde con el motor del navegador y arma lo que se manda al servidor.
// Lo usa `verificar_paquete_molde.py`.
import fs from 'node:fs'
import os from 'node:os'
import { Worker } from 'node:worker_threads'
import * as mupdf from 'mupdf'
import { desplegarMolde } from '../molde/desplegar.js'
import { armarPaqueteMolde } from '../paquete/armar.js'
import { crearPool } from '../pool.js'
import { abrirEnPool, faseA, faseB } from '../molde/desplegar_paralelo.js'

const [, , entrada, salidaA, salidaB, hilosArg] = process.argv
const bytes = new Uint8Array(fs.readFileSync(entrada))

if (!salidaB) {
  const doc = mupdf.Document.openDocument(bytes, 'application/pdf')
  const r = desplegarMolde(mupdf, doc)
  const { zip, sha1 } = armarPaqueteMolde(bytes, r, { motor: 'mupdf.js (Node, contrato)' })
  fs.writeFileSync(salidaA, zip)
  console.log(JSON.stringify({ sha1, bytes: zip.length, mesas: r.mesas.size }))
} else {
  const hilos = Number(hilosArg) || Math.max(2, Math.min(8, os.cpus().length - 1))
  const urlObrero = new URL('../obrero.worker.js', import.meta.url)
  const pool = crearPool(hilos, () => {
    const w = new Worker(urlObrero)
    const o = { postMessage: (m, t) => w.postMessage(m, t), terminate: () => w.terminate(), onmessage: null, onerror: null }
    w.on('message', (m) => o.onmessage && o.onmessage({ data: m }))
    w.on('error', (e) => o.onerror && o.onerror(e))
    return o
  })
  try {
    const t0 = performance.now()
    const sha1 = Buffer.from(await crypto.subtle.digest('SHA-1', bytes)).toString('hex')
    const info = await abrirEnPool(pool, bytes)
    const A = await faseA(pool, info)
    const pA = await pool.enviar('paquete', { archivo: null, desplegado: A, fase: 'contornos', sha1, motor: 'mupdf.js (Node, contrato)' })
    fs.writeFileSync(salidaA, pA.zip)
    const tA = (performance.now() - t0) / 1000
    const B = await faseB(pool, A)
    const pdfs = [...B.mesas.values()].map((x) => x.pdf.buffer)
    const pB = await pool.enviar('paquete', { archivo: null, desplegado: B, fase: 'paginas', sha1, motor: 'mupdf.js (Node, contrato)' }, pdfs)
    fs.writeFileSync(salidaB, pB.zip)
    console.log(JSON.stringify({ sha1, faseA_s: tA, total_s: (performance.now() - t0) / 1000, bytesA: pA.zip.length, bytesB: pB.zip.length, hilos }))
  } finally {
    pool.cerrar()
  }
}
