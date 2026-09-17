// node frontend/src/motor/pruebas/hoja.mjs <entrada.json> <salida.pdf>
// Compone la hoja de una tela (el sello) con el motor del navegador a partir de lo que Python le
// pasó a `hoja_pike.componer_hoja_sello`, volcado a JSON por `verificar_navegador_hoja.py`:
//   { cfg, hojas: [[{cx, cy, bw, bh, ang, estampado, base: <id>}]], bases: {id: {...}},
//     origenes: {id: "ruta del PDF de la mesa desplegada"}, signo_rotacion, perfil? }
// Escribe el PDF y deja en la última línea de la salida un JSON con consumo, alturas y tiempo.
import fs from 'node:fs'
import path from 'node:path'
import * as mupdf from 'mupdf'
import { componerHoja } from '../hoja/componer.js'

const [, , entrada, salida] = process.argv
const d = JSON.parse(fs.readFileSync(entrada, 'utf-8'))
const carpeta = path.dirname(path.resolve(entrada))
const origenes = {}
for (const [id, ruta] of Object.entries(d.origenes || {})) {
  origenes[id] = new Uint8Array(fs.readFileSync(path.isAbsolute(ruta) ? ruta : path.join(carpeta, ruta)))
}
// las bases se comparten por IDENTIDAD entre prendas (como `id(b)` en Python): un objeto por id
const bases = {}
for (const [id, b] of Object.entries(d.bases)) bases[id] = b
const hojas = d.hojas.map((h) => h.map((c) => ({ cx: c.cx, cy: c.cy, bw: c.bw, bh: c.bh, ang: c.ang,
  pieza: { base: bases[c.base], estampado: c.estampado || '' } })))
let perfil = null
if (d.perfil) {
  perfil = { icc: new Uint8Array(fs.readFileSync(path.isAbsolute(d.perfil.icc) ? d.perfil.icc : path.join(carpeta, d.perfil.icc))),
    nombre: d.perfil.nombre, n: d.perfil.n }
}
const t = performance.now()
const r = componerHoja(mupdf, { hojas, cfg: d.cfg, origenes, signoRotacion: d.signo_rotacion ?? 1, perfil })
const seg = (performance.now() - t) / 1000
fs.writeFileSync(salida, r.pdf)
console.log(JSON.stringify({ consumo_cm: r.consumoCm, alturas_cm: r.alturasCm, segundos: seg, bytes: r.pdf.length }))
