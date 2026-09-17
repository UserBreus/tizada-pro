// node frontend/src/motor/pruebas/paquete.mjs <molde.ai> <salida.zip>
// Prepara el molde con el motor del navegador y arma el paquete que se manda con «Guardar».
// Lo usa `verificar_paquete_molde.py`.
import fs from 'node:fs'
import * as mupdf from 'mupdf'
import { desplegarMolde } from '../molde/desplegar.js'
import { armarPaqueteMolde } from '../paquete/armar.js'

const [, , entrada, salida] = process.argv
const bytes = new Uint8Array(fs.readFileSync(entrada))
const doc = mupdf.Document.openDocument(bytes, 'application/pdf')
const r = desplegarMolde(mupdf, doc)
const { zip, sha1 } = armarPaqueteMolde(bytes, r, { motor: 'mupdf.js (Node, contrato)' })
fs.writeFileSync(salida, zip)
console.log(JSON.stringify({ sha1, bytes: zip.length, mesas: r.mesas.size }))
